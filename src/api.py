import logging
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.handlers import index_photos, get_stats, add_history_item, get_history_item
from src.handlers.agentic_loop import run_agent
from src.handlers.generate_captions import PhotoIndexingError, ModelLoadError, ChromaDBError
from src.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Photo Library AMA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AddHistoryItemRequest(BaseModel):
    user_query: str
    response: dict


class AddHistoryItemResponse(BaseModel):
    id: str


class LLMCallRequest(BaseModel):
    query: str
    max_iterations: int = 10


class ToolCallInfo(BaseModel):
    tool: str
    args: dict



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/photos/{filename}")
def get_photo(filename: str):
    settings = get_settings()
    print(f"{settings}")
    filepath = os.path.join(settings.PHOTOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(filepath)


@app.post("/llm_call")
def api_llm_call(request: LLMCallRequest):
    try:
        return run_agent(request.query, request.max_iterations)
    except Exception as e:
        logger.exception(f"Failed to run agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-stats")
def api_get_stats():
    try:
        return get_stats()
    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-history-item", response_model=AddHistoryItemResponse)
def api_add_history_item(request: AddHistoryItemRequest):
    try:
        item_id = add_history_item(request.user_query, request.response)
        return AddHistoryItemResponse(id=item_id)
    except Exception as e:
        logger.exception(f"Failed to add history item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-history-item")
def api_get_history_item(item_id: str):
    try:
        result = get_history_item(item_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get history item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/photos")
def list_photos():
    raise NotImplementedError


@app.post("/query")
def query():
    raise NotImplementedError


@app.post("/index")
def index():
    raise NotImplementedError


@app.post("/generate-captions")
def generate_captions():
    settings = get_settings()
    # logger.info(f"Photos dir: {settings.PHOTOS_DIR}, Chroma host: {settings.CHROMA_HOST}")
    
    try:
        result = index_photos(settings.PHOTOS_DIR, settings.CHROMA_HOST, settings.CHROMA_PORT)
        return result
    except ModelLoadError as e:
        logger.error(f"Model load error: {e}")
        raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")
    except ChromaDBError as e:
        logger.error(f"ChromaDB error: {e}")
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
    except PhotoIndexingError as e:
        logger.error(f"Photo indexing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
