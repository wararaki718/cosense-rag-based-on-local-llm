import os

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForMaskedLM, AutoTokenizer

from shared.models import EmbeddingRequest, EmbeddingResponse

# FastAPI App
app = FastAPI(
    title="API Embedding Service",
    description="SPLADE-based sparse vector generation for Apple Silicon",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "naver/splade_v2_distil")
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

print(f"Loading model {MODEL_NAME} to {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()

# Helper classes removed as they are now imported from shared.models

@app.post("/embed", response_model=EmbeddingResponse, summary="Vectorize text")
async def embed(request: EmbeddingRequest) -> EmbeddingResponse:
    """Transforms input text into a SPLADE sparse vector.

    Args:
        request (EmbeddingRequest): Request containing the text to be vectorized.

    Returns:
        EmbeddingResponse: Response containing the calculated sparse vector weights.

    Raises:
        HTTPException: If the vectorization process fails or the model errors.
    """
    try:
        inputs = tokenizer(
            request.text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(DEVICE)
        
        with torch.no_grad():
            outputs = model(**inputs)
            # SPLADE logic: max over time of log(1 + relu(logits))
            logits = outputs.logits
            sparse_vector = torch.max(
                torch.log(1 + torch.relu(logits)) * inputs.attention_mask.unsqueeze(-1),
                dim=1
            ).values.squeeze()

        # Convert to dictionary of non-zero indices for efficiency
        indices = torch.nonzero(sparse_vector).squeeze()
        if indices.dim() == 0:
            # Handle case where only 1 index is non-zero
            values = {int(indices.item()): float(sparse_vector[indices].item())}
        else:
            values = {int(i): float(sparse_vector[i].item()) for i in indices}

        return EmbeddingResponse(vector=values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/health")
async def health() -> dict:
    """Checks the health status of the embedding service.

    Returns:
        dict: A dictionary containing the status, target device, and model name.
    """
    return {"status": "ok", "device": DEVICE, "model": MODEL_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
