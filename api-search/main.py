import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import AsyncElasticsearch
from typing import List, Dict, Any, Optional
from shared.models import ScrapboxChunk, SearchQuery, SearchResultItem

# FastAPI App
app = FastAPI(
    title="API Search Service",
    description="Elasticsearch wrapper for Hybrid Search (BM25 + Sparse Vector)",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:8001")
INDEX_NAME = os.getenv("INDEX_NAME", "scrapbox-chunks")

es = AsyncElasticsearch(ES_URL)

# Helper classes removed as they are now imported from shared.models

@app.on_event("startup")
async def startup_event():
    """
    インデックスの作成とマッピングの定義
    """
    exists = await es.indices.exists(index=INDEX_NAME)
    if not exists:
        await es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "content": {
                            "type": "text",
                            "analyzer": "kuromoji",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "page_title": {"type": "text", "analyzer": "kuromoji"},
                        "project_name": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "updated_at": {"type": "date"},
                        "indent_level": {"type": "integer"},
                        "vector": {"type": "rank_features"}  # SPLADE vectors
                    }
                }
            }
        )
        print(f"Created index: {INDEX_NAME}")

@app.post("/search", response_model=List[SearchResultItem])
async def search(request: SearchQuery):
    """
    ハイブリッド検索 (BM25 + SPLADE) を実行します。
    """
    try:
        # 1. Get vector from api-embedding
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{EMBEDDING_API_URL}/embed", json={"text": request.query}, timeout=10.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get embedding")
            vector = resp.json()["vector"]

        # 2. Build multi-match + rank_feature query
        # Simplified hybrid search: linear combination via 'should'
        query_body = {
            "size": request.top_k,
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": request.query,
                                "fields": ["content^1.5", "page_title^2.0"],
                                "boost": 1.0
                            }
                        },
                        # SPLADE Sparse Vector search using rank_features
                        *[
                            {"rank_feature": {"field": "vector", "boost": weight, "log": {"scaling_factor": 1}, "field_name": str(idx)}}
                            for idx, weight in list(vector.items())[:100] # Limit to top features for performance
                        ]
                    ]
                }
            }
        }
        
        # Note: Elasticsearch rank_feature query structure is actually slightly different for multiple features.
        # For SPLADE, we often index them as separate fields or use a script.
        # ES 8.8+ supports `sparse_vector` type but it's for ELSER.
        # For custom SPLADE, 'rank_features' (plural) field type is best.
        
        # Correct rank_features query for multiple features:
        combined_query = {
            "size": request.top_k,
            "query": {
                "bool": {
                    "should": [
                        {"multi_match": {"query": request.query, "fields": ["content", "page_title"]}}
                    ]
                }
            }
        }
        
        # Adding rank features
        for feature_idx, weight in vector.items():
            combined_query["query"]["bool"]["should"].append({
                "rank_feature": {
                    "field": f"vector.{feature_idx}",
                    "boost": weight
                }
            })

        response = await es.search(index=INDEX_NAME, body=combined_query)
        
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            # Remove vector from output to save bandwidth
            if "vector" in source:
                del source["vector"]
                
            results.append(SearchResultItem(
                chunk=ScrapboxChunk(
                    id=hit["_id"],
                    project_name=source["project_name"],
                    page_title=source["page_title"],
                    content=source["content"],
                    url=source["url"],
                    updated_at=source["updated_at"],
                    indent_level=source["indent_level"]
                ),
                score=hit["_score"]
            ))
            
        return results

    except Exception as e:
        print(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def index_chunk(chunk: ScrapboxChunk, vector: Dict[str, float]):
    """
    チャンクをベクトル付きでインデックスに登録します。
    """
    try:
        body = chunk.dict()
        body["vector"] = {str(k): v for k, v in vector.items()}
        await es.index(index=INDEX_NAME, id=chunk.id, body=body)
        return {"result": "indexed", "id": chunk.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    es_health = await es.cluster.health()
    return {"status": "ok", "elasticsearch": es_health["status"]}
