import os
import asyncio
from typing import Dict, List
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from elasticsearch import AsyncElasticsearch
from shared.models import ScrapboxChunk, SearchQuery, SearchResultItem

# Configuration
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:8001")
INDEX_NAME = os.getenv("INDEX_NAME", "scrapbox-chunks")

es = AsyncElasticsearch(
    ES_URL,
    headers={"Accept": "application/vnd.elasticsearch+json; compatible-with=8"}
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    # Wait for ES to be truly ready (retry logic)
    for i in range(10):
        try:
            if await es.ping():
                break
        except Exception:
            pass
        print(f"Waiting for Elasticsearch... ({i+1}/10)")
        await asyncio.sleep(5)

    try:
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
    except Exception as e:
        print(f"Index creation step failed: {e}")
    
    yield
    await es.close()

# FastAPI App
app = FastAPI(
    title="API Search Service",
    description="Elasticsearch wrapper for Hybrid Search (BM25 + Sparse Vector)",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/search", response_model=List[SearchResultItem])
async def search(request: SearchQuery) -> List[SearchResultItem]:
    """Performs a hybrid search combining BM25 and SPLADE sparse vectors.

    Args:
        request (SearchQuery): Request containing search query and top_k parameter.

    Returns:
        List[SearchResultItem]: A list of ranked search results.

    Raises:
        HTTPException: If the embedding API call fails or Elasticsearch query errors.
    """
    try:
        # 1. Get vector from api-embedding
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{EMBEDDING_API_URL}/embed",
                json={"text": request.query},
                timeout=10.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get embedding")
            vector = resp.json()["vector"]

        # 2. Build multi-match + rank_feature query
        # Simplified hybrid search: linear combination via 'should'
        
        # Correct rank_features query for multiple features:
        combined_query = {
            "size": request.top_k,
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": request.query,
                                "fields": ["content", "page_title"],
                            }
                        }
                    ]
                }
            },
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
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/index")
async def index_chunk(chunk: ScrapboxChunk, vector: Dict[str, float]) -> dict:
    """Indexes a single chunk with its corresponding vector.

    Args:
        chunk (ScrapboxChunk): The chunk metadata and content.
        vector (Dict[str, float]): The sparse vector weights for the chunk.

    Returns:
        dict: A confirmation message with the indexed ID.

    Raises:
        HTTPException: If indexing into Elasticsearch fails.
    """
    try:
        body = chunk.model_dump(mode="json")
        body["vector"] = {str(k): v for k, v in vector.items()}
        await es.index(index=INDEX_NAME, id=chunk.id, body=body)
        return {"result": "indexed", "id": chunk.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/health")
async def health() -> dict:
    """Checks service health and Elasticsearch connectivity.

    Returns:
        dict: Status of the service and Elasticsearch cluster health.
    """
    es_health = await es.cluster.health()
    return {"status": "ok", "elasticsearch": es_health["status"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
