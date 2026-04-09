import os
import logging
from fastapi import FastAPI, HTTPException
from src.handlers import index_photos
from src.handlers.generate_captions import PhotoIndexingError, ModelLoadError, ChromaDBError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Photo Library AMA")


@app.get("/health")
def health():
    return {"status": "ok"}


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
    photos_dir = os.getenv("PHOTOS_DIR", "/app/photos")
    chroma_host = os.getenv("CHROMA_HOST", "chroma")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

    logger.info(f"{photos_dir}, {chroma_host}")
    
    try:
        result = index_photos(photos_dir, chroma_host, chroma_port)
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
