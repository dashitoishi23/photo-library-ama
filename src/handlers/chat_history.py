import logging
import uuid
from datetime import datetime
from typing import Optional
import chromadb
from src.config import get_settings
from src.handlers.embeddings import default_embedding_function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_history_item(user_query: str, response: dict) -> str:
    settings = get_settings()
    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    
    try:
        collection = client.get_collection("chat_history")
    except Exception:
        collection = client.create_collection(
            "chat_history",
            embedding_function=default_embedding_function
        )
    
    item_id = str(uuid.uuid4())
    document = f"User: {user_query}"
    metadata = {
        "user_query": user_query,
        "response_photos": ",".join(response.get("photos", [])),
        "response_additional_text": response.get("additional_text", ""),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    collection.add(
        ids=[item_id],
        documents=[document],
        metadatas=[metadata],
    )
    
    return item_id


def get_history_item(item_id: str) -> Optional[dict]:
    settings = get_settings()
    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    
    try:
        collection = client.get_collection("chat_history")
    except Exception:
        return None
    
    result = collection.get(ids=[item_id])
    
    if not result["ids"]:
        return None
    
    metadata = result["metadatas"][0]
    return {
        "id": result["ids"][0],
        "user_query": metadata.get("user_query"),
        "response": {
            "photos": metadata.get("response_photos", "").split(",") if metadata.get("response_photos") else [],
            "additional_text": metadata.get("response_additional_text", ""),
        },
        "timestamp": metadata.get("timestamp"),
    }
