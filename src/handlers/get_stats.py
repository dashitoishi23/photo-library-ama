import os
import glob
import logging
import chromadb
from src.config import get_settings
from src.handlers.embeddings import default_embedding_function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def count_photos(photos_dir: str) -> int:
    pattern = os.path.join(photos_dir, "*.jpg")
    return len(glob.glob(pattern))


def count_chroma_entries(chroma_host: str, chroma_port: int) -> int:
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    try:
        collection = client.get_collection("photo_captions")
    except Exception:
        return 0
    return collection.count()


def get_stats() -> dict:
    settings = get_settings()

    print(f"{settings}")
    
    photo_count = count_photos(settings.photos_dir)
    
    chroma_count = count_chroma_entries(settings.chroma_host, settings.chroma_port)
    
    return {
        "photo_count": photo_count,
        "chroma_count": chroma_count,
    }
