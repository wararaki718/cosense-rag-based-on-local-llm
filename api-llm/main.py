import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from shared.models import ScrapboxChunk, LLMRequest, LLMResponse

# FastAPI App
app = FastAPI(
    title="API LLM Service",
    description="RAG Prompt Engineering and Inference Engine for Gemma 3",
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
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma3:4b")

# Helper classes removed as they are now imported from shared.models

@app.post("/generate", response_model=LLMResponse)
async def generate(request: LLMRequest):
    """
    検索コンテキストに基づいて回答を生成します。
    """
    try:
        # 1. Build context string
        context_str = ""
        sources = []
        for i, chunk in enumerate(request.context):
            context_str += f"--- Source {i+1}: {chunk.page_title} ---\n{chunk.content}\n\n"
            if chunk.url not in sources:
                sources.append(chunk.url)

        # 2. Build Prompt
        prompt = f"""あなたはScrapboxの知識ベースに基づくアシスタントです。
以下の「提供されたコンテキスト」のみを使用して、ユーザーの質問に日本語で答えてください。
コンテキストから答えが見つからない場合は、「わかりません」と答えてください。
回答には、どのソースに基づいているかを明記する必要はありません（後でシステムが付与します）。

### 提供されたコンテキスト:
{context_str}

### 質問:
{request.query}

### 回答:"""

        # 3. Call Ollama
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                    }
                }
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to communicate with Ollama")
            
            answer = resp.json()["response"]
            
        return LLMResponse(answer=answer.strip(), sources=sources)

    except Exception as e:
        print(f"Error during LLM generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            return {"status": "ok", "ollama": "connected" if resp.status_code == 200 else "error"}
    except:
        return {"status": "ok", "ollama": "disconnected"}
