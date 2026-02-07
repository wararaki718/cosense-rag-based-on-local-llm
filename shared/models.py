"""Shared data models for the Scrapbox RAG system.

This module defines the Pydantic models used for communication between
the different microservices, including data ingestion, search, and LLM generation.
"""
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class ScrapboxChunk(BaseModel):
    """Represent a chunk of text from a Scrapbox page.

    Attributes:
        id (str): Unique identifier for the chunk.
        project_name (str): The name of the Scrapbox project.
        page_title (str): The title of the original page.
        content (str): The actual text content of the chunk.
        url (str): The direct URL to the Scrapbox page.
        updated_at (datetime): When the page was last updated.
        indent_level (int): The indentation level of the first line.
    """

    id: str = Field(
        ...,
        description="Unique ID for the chunk (e.g., pageId_chunkIndex)"
    )
    project_name: str = Field(..., description="Scrapbox project name")
    page_title: str = Field(..., description="Original page title")
    content: str = Field(..., description="Chunked text content")
    url: str = Field(..., description="Direct link to the Scrapbox page")
    updated_at: datetime = Field(
        ...,
        description="Last updated timestamp of the page"
    )
    indent_level: int = Field(
        0, description="Nesting level of the first line in this chunk"
    )

class EmbeddingRequest(BaseModel):
    """Request schema for text-to-vector transformation.

    Attributes:
        text (str): The source text to vectorize.
    """

    text: str = Field(..., description="Text to be vectorized")


class EmbeddingResponse(BaseModel):
    """Response schema for vector transformation.

    Attributes:
        vector (Dict[int, float]): Sparse vector represented as a mapping 
            of indices to weights.
    """

    vector: Dict[int, float] = Field(
        ..., description="Indices and weights of the sparse vector"
    )


class SearchQuery(BaseModel):
    """Request schema for searching chunks.

    Attributes:
        query (str): The search query in natural language.
        top_k (int): Maximum number of results to return.
    """

    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(5, description="Number of results to return")


class SearchResultItem(BaseModel):
    """Single search result entry.

    Attributes:
        chunk (ScrapboxChunk): The retrieved chunk data.
        score (float): Relevance score calculated by the search engine.
    """

    chunk: ScrapboxChunk
    score: float = Field(..., description="Relevance score (hybrid search)")


class SearchResponse(BaseModel):
    """Response schema for a search operation.

    Attributes:
        results (List[SearchResultItem]): List of ranked search results.
    """

    results: List[SearchResultItem]


class LLMRequest(BaseModel):
    """Request schema for LLM response generation.

    Attributes:
        query (str): The user's question.
        context (List[ScrapboxChunk]): List of relevant chunks to use as context.
    """

    query: str = Field(..., description="User's original question")
    context: List[ScrapboxChunk] = Field(
        ..., description="Relevant chunks retrieved from search"
    )


class LLMResponse(BaseModel):
    """Response schema for LLM generation.

    Attributes:
        answer (str): The generated response text.
        sources (List[str]): List of URLs for the sources used in the answer.
    """

    answer: str = Field(..., description="Generated answer from LLM")
    sources: List[str] = Field(
        ..., description="List of source URLs used for the answer"
    )
