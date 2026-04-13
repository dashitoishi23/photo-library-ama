import os
import glob
import logging
from typing import Any, Optional

import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from sentence_transformers import SentenceTransformer
from PIL import Image
import piexif
import chromadb

from src.config import get_settings
from src.handlers.geocoding import reverse_geocode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_blip2_processor: Optional[Blip2Processor] = None
_blip2_model: Optional[Blip2ForConditionalGeneration] = None
_embedding_model: Optional[SentenceTransformer] = None


class PhotoIndexingError(Exception):
    pass


class ModelLoadError(PhotoIndexingError):
    pass


class ChromaDBError(PhotoIndexingError):
    pass


def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ModelLoadError:
            raise
        except ChromaDBError:
            raise
        except PhotoIndexingError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            raise PhotoIndexingError(f"{func.__name__}: {str(e)}")
    return wrapper


def get_photo_files(photos_dir: str) -> list[str]:
    pattern = os.path.join(photos_dir, "*.jpg")
    return sorted(glob.glob(pattern))


def extract_exif(image_path: str) -> dict[str, Any]:
    exif_dict: dict[str, Any] = {}
    try:
        exif_dict_raw = piexif.load(image_path)
        exif_dict["date_taken"] = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.DateTime, "").decode()
        exif_dict["camera_make"] = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.Make, "").decode()
        exif_dict["camera_model"] = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.Model, "").decode()
        
        gps_ifd = exif_dict_raw.get("GPS", {})
        if gps_ifd:
            lat = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
            lon = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
            
            if lat and lon and lat_ref and lon_ref:
                def convert_to_decimal(coords, ref):
                    degrees = coords[0][0] / coords[0][1]
                    minutes = coords[1][0] / coords[1][1]
                    seconds = coords[2][0] / coords[2][1]
                    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
                    if ref in [b'S', b'W']:
                        decimal = -decimal
                    return decimal
                
                exif_dict["gps_lat"] = convert_to_decimal(lat, lat_ref)
                exif_dict["gps_lon"] = convert_to_decimal(lon, lon_ref)
    except Exception as e:
        logger.warning(f"Failed to extract EXIF from {image_path}: {e}")
    
    return exif_dict


def generate_caption(image_path: str, processor: Blip2Processor, model: Blip2ForConditionalGeneration) -> str:
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=100)
        
        caption = processor.decode(output[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        logger.error(f"Failed to generate caption for {image_path}: {e}")
        return ""


def create_embedding_text(metadata: dict[str, Any], caption: str) -> str:
    parts = [f"Photo: {caption}"]
    
    if metadata.get("date_taken"):
        parts.append(f"Taken on {metadata['date_taken']}")
    if metadata.get("camera_make"):
        parts.append(f"Camera: {metadata['camera_make']} {metadata.get('camera_model', '')}")
    if metadata.get("location"):
        parts.append(f"Location: {metadata['location']}")
    elif metadata.get("gps_lat") and metadata.get("gps_lon"):
        parts.append(f"Location: {metadata['gps_lat']}, {metadata['gps_lon']}")
    
    return ". ".join(parts)


@error_handler
def get_models():
    global _blip2_processor, _blip2_model, _embedding_model

    settings = get_settings()
    hf_cache = settings.HF_CACHE

    logger.info(f"HF_CACHE ==== {hf_cache}")
    
    if _blip2_processor is None:
        try:
            logger.info("Loading BLIP-2 model...")
            _blip2_processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b", cache_dir=hf_cache)
            _blip2_model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                torch_dtype=torch.float16
            )
            if torch.cuda.is_available():
                _blip2_model = _blip2_model.cuda()
                logger.info("Using CUDA")
            else:
                logger.warning("Using CPU (this will be slow)")
            _blip2_model.eval()
        except Exception as e:
            logger.exception("Failed to load BLIP-2 model")
            raise ModelLoadError(f"Failed to load BLIP-2 model: {e}")
    
    if _embedding_model is None:
        try:
            logger.info("Loading embedding model...")
            _embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            if torch.cuda.is_available():
                _embedding_model = _embedding_model.cuda()
        except Exception as e:
            logger.exception("Failed to load embedding model")
            raise ModelLoadError(f"Failed to load embedding model: {e}")
    
    return _blip2_processor, _blip2_model, _embedding_model


@error_handler
def index_photos(photos_dir: str, chroma_host: str, chroma_port: int) -> dict:
    processor, model, embedding_model = get_models()
    
    photo_files = get_photo_files(photos_dir)
    if not photo_files:
        return {"status": "ok", "indexed": 0, "message": "No photos found"}
    
    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        collection = client.get_or_create_collection(
            "photo_captions",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        logger.exception(f"Failed to connect to ChromaDB at {chroma_host}:{chroma_port}")
        raise ChromaDBError(f"Failed to connect to ChromaDB: {e}")
    
    try:
        existing_ids = set(collection.get()["ids"])
    except Exception as e:
        logger.exception("Failed to get existing IDs from ChromaDB")
        raise ChromaDBError(f"Failed to get existing IDs: {e}")
    
    photo_files = [f for f in photo_files if os.path.basename(f) not in existing_ids]
    
    if not photo_files:
        return {"status": "ok", "indexed": 0, "message": "No new photos to process"}
    
    ids = []
    documents = []
    metadatas = []
    embeddings = []
    
    for photo_path in photo_files:
        filename = os.path.basename(photo_path)
        
        try:
            caption = generate_caption(photo_path, processor, model)
        except Exception as e:
            logger.error(f"Skipping {filename}: caption generation failed: {e}")
            continue
        
        try:
            exif_data = extract_exif(photo_path)
        except Exception as e:
            logger.warning(f"Failed to extract EXIF from {filename}: {e}")
            exif_data = {}
        
        metadata = {
            "filename": filename,
            "filepath": photo_path,
            "caption": caption,
            "date_taken": exif_data.get("date_taken", ""),
            "camera_make": exif_data.get("camera_make", ""),
            "camera_model": exif_data.get("camera_model", ""),
            "gps_lat": exif_data.get("gps_lat"),
            "gps_lon": exif_data.get("gps_lon"),
        }
        
        if exif_data.get("gps_lat") and exif_data.get("gps_lon"):
            location = reverse_geocode(exif_data["gps_lat"], exif_data["gps_lon"])
            if location:
                metadata["location"] = location
        
        try:
            embedding_text = create_embedding_text(metadata, caption)
            embedding = embedding_model.encode(embedding_text).tolist()
        except Exception as e:
            logger.error(f"Skipping {filename}: embedding generation failed")
            continue
        
        ids.append(filename)
        documents.append(caption)
        metadatas.append(metadata)
        embeddings.append(embedding)
    
    if not ids:
        return {"status": "ok", "indexed": 0, "message": "Failed to process any photos"}
    
    try:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
    except Exception as e:
        logger.exception("Failed to upsert to ChromaDB")
        raise ChromaDBError(f"Failed to upsert to ChromaDB: {e}")
    
    return {"status": "ok", "indexed": len(ids)}


def main():
    settings = get_settings()
    
    try:
        result = index_photos(settings.PHOTOS_DIR, settings.CHROMA_HOST, settings.CHROMA_PORT)
        logger.info(f"Done! Indexed {result['indexed']} photos")
    except PhotoIndexingError as e:
        logger.error(f"Photo indexing failed: {e}")
        exit(1)
