import asyncio
import os
import urllib.parse
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

async def fetch_pages(project: str, client: httpx.AsyncClient) -> List[dict]:
    """Retrieves all page metadata from the Scrapbox project.

    Args:
        project (str): The Scrapbox project name.
        client (httpx.AsyncClient): The HTTP client to use.

    Returns:
        List[dict]: A list of page summary objects.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    url = f"https://scrapbox.io/api/pages/{project}?limit=1000"
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()["pages"]

async def fetch_page_content(project: str, title: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """Retrieves detailed content for a specific Scrapbox page with retry logic.

    Args:
        project (str): The Scrapbox project name.
        title (str): The title of the page to fetch.
        client (httpx.AsyncClient): The HTTP client to use.

    Returns:
        Optional[Dict[str, Any]]: The full page data, or None if the request failed.
    """
    encoded_title = urllib.parse.quote(title, safe="")
    url = f"https://scrapbox.io/api/pages/{project}/{encoded_title}"
    
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            print(f"Warning: Got status {resp.status_code} for {title}. Retrying... ({attempt+1}/3)")
        except (httpx.ReadError, httpx.ConnectError) as e:
            print(f"Network error fetching {title}: {e}. Retrying... ({attempt+1}/3)")
        
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
    return None

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
        
        # Logic: If empty line or indent level decreases or chunk is too long, start a new chunk
        is_empty = not line_text.strip()
        current_len = sum(len(l) for l in current_chunk)
        is_indent_decrease = (
            i > 0 and indent < current_indent and len(current_chunk) > 5
        )
        is_too_long = current_len > 1000
        
        if is_empty or is_indent_decrease or is_too_long:
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

async def process_and_index(chunk: ScrapboxChunk, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> None:
    """Vectorizes a chunk and indices it into the search engine.

    Args:
        chunk (ScrapboxChunk): The chunk to be processed.
        client (httpx.AsyncClient): An active HTTP client for API calls.
        semaphore (asyncio.Semaphore): To limit concurrent requests.
    """
    async with semaphore:
        try:
            # 1. Vectorize
            resp_embed = await client.post(
                f"{EMBEDDING_API_URL}/embed",
                json={"text": chunk.content}
            )
            if resp_embed.status_code != 200:
                print(f"Failed to embed chunk {chunk.id}: {resp_embed.text}")
                return
            vector = resp_embed.json()["vector"]
            
            # 2. Index
            resp_index = await client.post(f"{SEARCH_API_URL}/index", json={
                "chunk": chunk.model_dump(mode="json"),
                "vector": vector
            })
            if resp_index.status_code != 200:
                print(f"Failed to index chunk {chunk.id}: {resp_index.text}")
        except Exception as e:
            print(f"Error processing chunk {chunk.id} at {EMBEDDING_API_URL} or {SEARCH_API_URL}: {e}")

async def wait_for_services(client: httpx.AsyncClient) -> bool:
    """Waits for backend API services to become healthy."""
    for api_name, url in [("Embedding", EMBEDDING_API_URL), ("Search", SEARCH_API_URL)]:
        print(f"Checking {api_name} API at {url}...")
        for i in range(20):
            try:
                resp = await client.get(f"{url}/health")
                if resp.status_code == 200:
                    print(f"{api_name} API is ready.")
                    break
            except Exception:
                pass
            if i % 5 == 0 and i > 0:
                print(f"Still waiting for {api_name} API... ({i}/20)")
            await asyncio.sleep(5)
        else:
            print(f"Error: {api_name} API is not responding.")
            return False
    return True

async def main() -> None:
    """Main entry point for the Scrapbox data ingestion batch.

    Orchestrates the process of fetching, chunking, and indexing pages.
    """
    if not PROJECT_NAME:
        print("Error: SCRAPBOX_PROJECT is not set.")
        return

    headers = {"Cookie": f"connect.sid={SCRAPBOX_SID}"} if SCRAPBOX_SID else {}
    async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
        if not await wait_for_services(client):
            return

        print(f"Fetching pages from project: {PROJECT_NAME}")
        try:
            pages = await fetch_pages(PROJECT_NAME, client)
        except Exception as e:
            print(f"Failed to fetch pages: {e}")
            return
        
        semaphore = asyncio.Semaphore(10) # Limit concurrency
        for page_summary in tqdm(pages, desc="Processing pages"):
            page_data = await fetch_page_content(PROJECT_NAME, page_summary["title"], client)
            if not page_data:
                continue
                
            chunks = chunk_page(page_data, PROJECT_NAME)
            
            # Process chunks in parallel for this page
            tasks = [process_and_index(chunk, client, semaphore) for chunk in chunks]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
