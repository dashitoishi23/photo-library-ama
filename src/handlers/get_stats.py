import os
import glob
import logging
import chromadb
from src.config import get_settings
from src.handlers.embeddings import default_embedding_function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def count_photos(PHOTOS_DIR: str) -> int:
    pattern = os.path.join(PHOTOS_DIR, "*.jpg")
    return len(glob.glob(pattern))


def count_chroma_entries(CHROMA_HOST: str, CHROMA_PORT: int) -> int:
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    try:
        collection = client.get_collection("photo_captions")
    except Exception:
        return 0
    return collection.count()


def get_stats() -> dict:
    settings = get_settings()

    print(f"{settings}")
    
    photo_count = count_photos(settings.PHOTOS_DIR)
    
    chroma_count = count_chroma_entries(settings.CHROMA_HOST, settings.CHROMA_PORT)
    
    return {
        "photo_count": photo_count,
        "chroma_count": chroma_count,
    }
