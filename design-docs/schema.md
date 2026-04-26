# Chroma DB Schema Design

## 1. Overview

This document defines the schema for storing photo metadata in Chroma vector database, including extracted EXIF data (date, location), filenames, and generated captions.

---

## 2. EXIF Metadata Extraction

### Libraries Used
- **piexif**: For detailed EXIF parsing

### Metadata Extracted

| Field | EXIF Tag | Type | Description |
|-------|----------|------|-------------|
| `date_taken` | `DateTime` | string | ISO format: `YYYY:MM:DD HH:MM:SS` |
| `gps_lat` | `GPSInfo[GPSLatitude]` | float | Latitude decimal |
| `gps_lon` | `GPSInfo[GPSLongitude]` | float | Longitude decimal |
| `camera_make` | `Make` | string | Camera manufacturer |
| `camera_model` | `Model` | string | Camera model |

### Processing Logic

```python
def extract_exif(image_path: str) -> dict:
    """Extract EXIF metadata from image using piexif."""
    exif_dict = {}
    exif_dict_raw = piexif.load(image_path)
    
    # Date taken
    date_taken = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.DateTime, "").decode()
    exif_dict["date_taken"] = date_taken
    
    # Camera info
    exif_dict["camera_make"] = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.Make, "").decode()
    exif_dict["camera_model"] = exif_dict_raw.get("0th", {}).get(piexif.ImageIFD.Model, "").decode()
    
    # GPS coordinates
    gps_ifd = exif_dict_raw.get("GPS", {})
    if gps_ifd:
        lat = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
        lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
        lon = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
        lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
        
        if lat and lon and lat_ref and lon_ref:
            # GPS coords are stored as rationals (tuples of numerator/denominator)
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
    
    return exif_dict
```

---

## 3. Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   Image    │───▶│  Extract     │───▶│  Generate   │───▶│   Store     │
│   File     │    │  EXIF Data  │    │   Caption   │    │   in Chroma │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                                                    
    filename.jpg     date_taken          "A sunset over   id: filename
    /path/to/       gps_lat/lon         the ocean..."   metadata: {...}
    file            camera_info                            document: caption
```

---

## 4. Chroma Schema

### Collection Name
```
photo_captions
```

### Document Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (filename, e.g., `IMG_0001.jpg`) |
| `embedding` | float[384] | Sentence-transformer embedding of caption + metadata |
| `document` | string | The generated caption text |
| `metadata` | dict | Associated metadata |

### Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `filename` | string | Image filename | `IMG_0001.jpg` |
| `filepath` | string | Full path to image | `/photos/vacation/IMG_0001.jpg` |
| `caption` | string | Generated caption | `A sunset over the ocean...` |
| `date_taken` | string | When photo was taken (EXIF DateTime) | `2024:07:15 18:30:00` |
| `gps_lat` | float | Latitude | `34.0522` |
| `gps_lon` | float | Longitude | `-118.2437` |
| `location` | string | Reverse-geocoded address | `Santa Monica Beach, California, United States` |
| `camera_make` | string | Camera manufacturer | `Apple` |
| `camera_model` | string | Camera model | `iPhone 15 Pro` |

### Example Record

```python
{
    "id": "IMG_0001.jpg",
    "embedding": [0.123, -0.456, 0.789, ...],  # 384-dimensional
    
    "document": "A golden sunset over the Pacific Ocean with waves crashing on the shore",
    
    "metadata": {
        "filename": "IMG_0001.jpg",
        "filepath": "/home/user/photos/vacation/IMG_0001.jpg",
        "caption": "A golden sunset over the Pacific Ocean with waves crashing on the shore",
        "date_taken": "2024:07:15 18:30:00",
        "gps_lat": 34.0522,
        "gps_lon": -118.2437,
        "location": "Santa Monica Beach, Santa Monica, California, United States",
        "camera_make": "Apple",
        "camera_model": "iPhone 15 Pro"
    }
}
```

---

## 5. Implementation

### Python Code

```python
import chromadb
from sentence_transformers import SentenceTransformer
import piexif

class PhotoVectorStore:
    def __init__(self, CHROMA_HOST: str, CHROMA_PORT: int):
        self.client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.collection = self.client.get_or_create_collection(
            name="photo_captions",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def extract_exif(self, image_path: str) -> dict:
        """Extract EXIF metadata from image using piexif."""
        exif_dict = {}
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
        
        return exif_dict
    
    def add_photo(self, filename: str, filepath: str, caption: str, exif_data: dict):
        """Add a photo to the vector store."""
        
        # Build metadata from EXIF data
        metadata = {
            "filename": filename,
            "filepath": filepath,
            "caption": caption,
            "date_taken": exif_data.get("date_taken", ""),
            "camera_make": exif_data.get("camera_make", ""),
            "camera_model": exif_data.get("camera_model", ""),
            "gps_lat": exif_data.get("gps_lat"),
            "gps_lon": exif_data.get("gps_lon"),
        }
        
        # Filter out None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Generate embedding from caption + metadata
        embedding_text = f"Photo: {caption}"
        if metadata.get("date_taken"):
            embedding_text += f". Taken on {metadata['date_taken']}"
        if metadata.get("camera_make"):
            embedding_text += f". Camera: {metadata['camera_make']} {metadata.get('camera_model', '')}"
        
        embedding = self.embedding_model.encode(embedding_text)
        
        self.collection.add(
            ids=filename,
            embeddings=[embedding.tolist()],
            documents=[caption],
            metadatas=[metadata]
        )
```

---

## 6. Query Examples

### Semantic Search
```python
# Find photos matching "beach sunset"
results = collection.query(
    query_texts=["beach sunset"],
    n_results=5
)
```

### Filter by Date
```python
# Find photos from summer 2024
results = collection.get(
    where={"date_taken": {"$gte": "2024:06:01", "$lte": "2024:08:31"}}
)
```

### Filter by Location
```python
# Find photos near coordinates
results = collection.get(
    where={"gps_lat": {"$gte": 34.0, "$lte": 34.1}, "gps_lon": {"$gte": -118.3, "$lte": -118.2}}
)
```

### Combined Query + Filter
```python
# Find beach photos taken with specific camera
results = collection.query(
    query_texts=["beach vacation"],
    n_results=10,
    where={"camera_make": "Apple"}
)
```

---

## 7. Schema Validation

### Required Fields
- `id`: Must be unique (filename)
- `embedding`: Must be 384-dimensional float array
- `document`: Must be non-empty string
- `metadata.filename`: Required

### Optional Fields
All EXIF fields are optional - photos without EXIF data will have `null` values stored as `None` and filtered out.

Current optional fields:
- `date_taken`: string (EXIF DateTime format)
- `gps_lat`: float
- `gps_lon`: float
- `camera_make`: string
- `camera_model`: string

---

## 8. Indexing & Performance

Chroma automatically indexes the embeddings using HNSW. Additional indexes can be created on metadata fields for filtering:

```python
# Create index on date_taken for range queries
collection.create_index("date_taken")

# Create index on location for exact match
collection.create_index("location")
```

---

## 9. Chat History Schema

### Collection Name
```
chat_history
```

### Document Structure

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (UUID) |
| `document` | string | User query text |
| `metadata` | dict | Response and timestamp data |

### Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `user_query` | string | The user's query string | "Find photos of sunset" |
| `response_photos` | string | Comma-separated list of photo IDs | "photo1.jpg,photo2.jpg" |
| `response_additional_text` | string | Additional text response | "Here are some sunset photos..." |
| `timestamp` | string | ISO 8601 timestamp | "2026-04-12T15:30:00" |

### Example Record

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document": "User: Find photos of sunset",
    
    "metadata": {
        "user_query": "Find photos of sunset",
        "response_photos": "IMG_0001.jpg,IMG_0002.jpg",
        "response_additional_text": "Here are 2 sunset photos from your collection",
        "timestamp": "2026-04-12T15:30:00"
    }
}
```

### API Request Format

```python
# POST /add-history-item
{
    "user_query": "Find photos of sunset",
    "response": {
        "photos": ["IMG_0001.jpg", "IMG_0002.jpg"],
        "additional_text": "Here are 2 sunset photos from your collection"
    }
}
```

---

*Schema Version: 1.0*  
*Last Updated: April 12, 2026*
