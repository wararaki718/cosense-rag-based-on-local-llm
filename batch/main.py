import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from tqdm import tqdm

from shared.models import ScrapboxChunk

# Environment Variables
PROJECT_NAME = os.getenv("SCRAPBOX_PROJECT")
SCRAPBOX_SID = os.getenv("SCRAPBOX_SID")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:8001")
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "http://localhost:8002")

async def fetch_pages(project: str) -> List[dict]:
    """Retrieves all page metadata from the Scrapbox project.

    Args:
        project (str): The Scrapbox project name.

    Returns:
        List[dict]: A list of page summary objects.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    headers = {"Cookie": f"connect.sid={SCRAPBOX_SID}"} if SCRAPBOX_SID else {}
    async with httpx.AsyncClient(headers=headers) as client:
        # Get all pages list
        url = f"https://scrapbox.io/api/pages/{project}?limit=1000"
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()["pages"]

async def fetch_page_content(project: str, title: str) -> Optional[Dict[str, Any]]:
    """Retrieves detailed content for a specific Scrapbox page.

    Args:
        project (str): The Scrapbox project name.
        title (str): The title of the page to fetch.

    Returns:
        Optional[Dict[str, Any]]: The full page data, or None if the request failed.
    """
    headers = {"Cookie": f"connect.sid={SCRAPBOX_SID}"} if SCRAPBOX_SID else {}
    async with httpx.AsyncClient(headers=headers) as client:
        url = f"https://scrapbox.io/api/pages/{project}/{title}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        return resp.json()

def chunk_page(page_data: Dict[str, Any], project: str) -> List[ScrapboxChunk]:
    """Segments a Scrapbox page into chunks based on indentation and empty lines.

    Args:
        page_data (Dict[str, Any]): The raw page data from Scrapbox API.
        project (str): The project name for URL construction.

    Returns:
        List[ScrapboxChunk]: A list of generated text chunks.
    """
    title = page_data["title"]
    lines = page_data["lines"]
    updated_at = datetime.fromtimestamp(page_data["updated"])
    page_url = f"https://scrapbox.io/{project}/{title.replace(' ', '_')}"
    
    chunks = []
    current_chunk = []
    current_indent = 0
    
    for i, line_data in enumerate(lines):
        line_text = line_data["text"]
        
        # Determine indent (count leading tabs or spaces)
        indent = 0
        for char in line_text:
            if char == '\t':
                indent += 1
            elif char == ' ':
                indent += 1
            else:
                break
        
        # Logic: If empty line or indent level decreases, start a new chunk
        is_empty = not line_text.strip()
        is_indent_decrease = (
            i > 0 and indent < current_indent and len(current_chunk) > 5
        )
        if is_empty or is_indent_decrease:
            if current_chunk:
                chunk_text = "\n".join(current_chunk)
                chunks.append(ScrapboxChunk(
                    id=f"{page_data['id']}_{len(chunks)}",
                    project_name=project,
                    page_title=title,
                    content=chunk_text,
                    url=page_url,
                    updated_at=updated_at,
                    indent_level=current_indent
                ))
                current_chunk = []
        
        if line_text.strip():
            if not current_chunk:
                current_indent = indent
            current_chunk.append(line_text)

    # Add last chunk
    if current_chunk:
        chunks.append(ScrapboxChunk(
            id=f"{page_data['id']}_{len(chunks)}",
            project_name=project,
            page_title=title,
            content="\n".join(current_chunk),
            url=page_url,
            updated_at=updated_at,
            indent_level=current_indent
        ))
        
    return chunks

async def process_and_index(chunk: ScrapboxChunk, client: httpx.AsyncClient) -> None:
    """Vectorizes a chunk and indices it into the search engine.

    Args:
        chunk (ScrapboxChunk): The chunk to be processed.
        client (httpx.AsyncClient): An active HTTP client for API calls.
    """
    try:
        # 1. Vectorize
        resp_embed = await client.post(
            f"{EMBEDDING_API_URL}/embed",
            json={"text": chunk.content}
        )
        if resp_embed.status_code != 200:
            print(f"Failed to embed chunk {chunk.id}")
            return
        vector = resp_embed.json()["vector"]
        
        # 2. Index
        resp_index = await client.post(f"{SEARCH_API_URL}/index", json={
            "chunk": chunk.dict(),
            "vector": vector
        })
        if resp_index.status_code != 200:
            print(f"Failed to index chunk {chunk.id}: {resp_index.text}")
    except Exception as e:
        print(f"Error processing chunk {chunk.id}: {e}")

async def main() -> None:
    """Main entry point for the Scrapbox data ingestion batch.

    Orchestrates the process of fetching, chunking, and indexing pages.
    """
    if not PROJECT_NAME:
        print("Error: SCRAPBOX_PROJECT is not set.")
        return

    print(f"Fetching pages from project: {PROJECT_NAME}")
    try:
        pages = await fetch_pages(PROJECT_NAME)
    except Exception as e:
        print(f"Failed to fetch pages: {e}")
        return
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page_summary in tqdm(pages, desc="Processing pages"):
            page_data = await fetch_page_content(PROJECT_NAME, page_summary["title"])
            if not page_data:
                continue
                
            chunks = chunk_page(page_data, PROJECT_NAME)
            
            # Process chunks in parallel for this page
            tasks = [process_and_index(chunk, client) for chunk in chunks]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
