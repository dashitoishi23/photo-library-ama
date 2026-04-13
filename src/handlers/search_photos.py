from typing import Optional, Any
import logging
import chromadb
from src.config import get_settings
from src.handlers import tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("search_photos")


@tools.register_tool
def search_photos(
    query: str,
    n_results: int = 10,
    filters: Optional[dict] = None
) -> dict[str, Any]:
    """
    Search for photos using semantic search in ChromaDB.
    
    Args:
        query: Natural language query (e.g., "beach photos at Kerala")
        n_results: Number of results to return (default: 10)
        filters: Optional metadata filters
    
    Returns:
        dict with success, results, count, query
    """
    settings = get_settings()
    
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        collection = client.get_collection("photo_captions")
    except Exception as e:
        logger.error(f"Failed to connect to ChromaDB: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
            "query": query
        }
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filters,
            include=["documents", "metadatas"]
        )
        
        photo_results = []
        for i in range(len(results["ids"])):
            photo_id = results["ids"][i]
            document = results["documents"][i]
            metadata = results["metadatas"][i] if isinstance(results["metadatas"][i], dict) else {}
            
            photo_results.append({
                "id": photo_id,
                "caption": document,
                "filename": metadata.get("filename", photo_id),
                "filepath": metadata.get("filepath", ""),
                "date_taken": metadata.get("date_taken", ""),
                "location": metadata.get("location", ""),
                "camera_make": metadata.get("camera_make", ""),
            })
        
        return {
            "success": True,
            "results": photo_results,
            "count": len(photo_results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
            "query": query
        }