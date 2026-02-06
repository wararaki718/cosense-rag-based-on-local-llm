from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ScrapboxChunk(BaseModel):
    """
    Scrapboxの1ページを分割したチャンクのデータモデル
    """
    id: str = Field(..., description="Unique ID for the chunk (e.g., pageId_chunkIndex)")
    project_name: str = Field(..., description="Scrapbox project name")
    page_title: str = Field(..., description="Original page title")
    content: str = Field(..., description="Chunked text content")
    url: str = Field(..., description="Direct link to the Scrapbox page")
    updated_at: datetime = Field(..., description="Last updated timestamp of the page")
    indent_level: int = Field(0, description="Nesting level of the first line in this chunk")

class EmbeddingRequest(BaseModel):
    """
    ベクトル変換リクエスト
    """
    text: str = Field(..., description="Text to be vectorized")

class EmbeddingResponse(BaseModel):
    """
    ベクトル変換レスポンス (SPLADE などの Sparse Vector を想定)
    """
    vector: Dict[int, float] = Field(..., description="Indices and weights of the sparse vector")

class SearchQuery(BaseModel):
    """
    検索リクエスト
    """
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(5, description="Number of results to return")

class SearchResultItem(BaseModel):
    """
    検索結果の1項目
    """
    chunk: ScrapboxChunk
    score: float = Field(..., description="Relevance score (hybrid search)")

class SearchResponse(BaseModel):
    """
    検索レスポンス
    """
    results: List[SearchResultItem]

class LLMRequest(BaseModel):
    """
    LLM回答生成リクエスト
    """
    query: str = Field(..., description="User's original question")
    context: List[ScrapboxChunk] = Field(..., description="Relevant chunks retrieved from search")

class LLMResponse(BaseModel):
    """
    LLM回答生成レスポンス
    """
    answer: str = Field(..., description="Generated answer from LLM")
    sources: List[str] = Field(..., description="List of source URLs used for the answer")
