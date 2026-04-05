# Chroma DB Schema Design

## 1. Overview

This document defines the schema for storing photo metadata in Chroma vector database, including extracted EXIF data (date, location), filenames, and generated captions.

---

## 2. EXIF Metadata Extraction

### Libraries Used
- **Pillow (PIL)**: Built-in EXIF reading via `Image.getexif()`
- **piexif**: For more detailed EXIF parsing (optional)

### Metadata Extracted

| Field | EXIF Tag | Type | Description |
|-------|----------|------|-------------|
| `date_taken` | `DateTimeOriginal` | string | ISO format: `YYYY:MM:DD HH:MM:SS` |
| `date_modified` | `DateTime` | string | File modification date |
| `gps_lat` | `GPSInfo[GPSLatitude]` | float | Latitude decimal |
| `gps_lon` | `GPSInfo[GPSLongitude]` | float | Longitude decimal |
| `gps_lat_ref` | `GPSInfo[GPSLatitudeRef]` | string | "N" or "S" |
| `gps_lon_ref` | `GPSInfo[GPSLongitudeRef]` | string | "E" or "W" |
| `camera_make` | `Make` | string | Camera manufacturer |
| `camera_model` | `Model` | string | Camera model |
| `orientation` | `Orientation` | int | Image orientation |

### Processing Logic

```python
def extract_exif(image_path: str) -> dict:
    """Extract EXIF metadata from image."""
    metadata = {}
    
    with Image.open(image_path) as img:
        exif = img.getexif()
        
        # Date taken
        if exif.get(0x9003):  # DateTimeOriginal
            metadata['date_taken'] = exif[0x9003]
        
        # GPS coordinates
        gps_ifd = exif.get(0x8825)  # GPSInfo
        if gps_ifd:
            lat = gps_ifd.get(0x0002)
            lat_ref = gps_ifd.get(0x0001)
            lon = gps_ifd.get(0x0004)
            lon_ref = gps_ifd.get(0x0003)
            
            if lat and lon:
                metadata['gps_lat'] = convert_gps(lat)
                metadata['gps_lat_ref'] = lat_ref
                metadata['gps_lon'] = convert_gps(lon)
                metadata['gps_lon_ref'] = lon_ref
    
    return metadata
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
| `embedding` | float[384] | Sentence-transformer embedding of caption |
| `document` | string | The generated caption text |
| `metadata` | dict | Associated metadata |

### Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `filename` | string | Image filename | `IMG_0001.jpg` |
| `filepath` | string | Full path to image | `/photos/vacation/IMG_0001.jpg` |
| `caption` | string | Generated caption | `A sunset over the ocean...` |
| `date_taken` | string | When photo was taken | `2024:07:15 18:30:00` |
| `date_modified` | string | File modification date | `2024:07:15 18:35:00` |
| `gps_lat` | float | Latitude | `34.0522` |
| `gps_lon` | float | Longitude | `-118.2437` |
| `location` | string | Reverse-geocoded location | `Los Angeles, CA` |
| `camera_make` | string | Camera manufacturer | `Apple` |
| `camera_model` | string | Camera model | `iPhone 15 Pro` |
| `orientation` | int | Image orientation | `1` |

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
        "date_modified": "2024:07:15 18:35:00",
        "gps_lat": 34.0522,
        "gps_lon": -118.2437,
        "location": "Santa Monica, CA",
        "camera_make": "Apple",
        "camera_model": "iPhone 15 Pro",
        "orientation": 1
    }
}
```

---

## 5. Implementation

### Python Code

```python
import chromadb
from chromadb.config import Settings
from PIL import Image
from sentence_transformers import SentenceTransformer

class PhotoVectorStore:
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="photo_captions",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_photo(self, filename: str, filepath: str, caption: str, exif_data: dict):
        """Add a photo to the vector store."""
        
        # Generate embedding from caption
        embedding = self.embedding_model.encode(caption)
        
        # Build metadata
        metadata = {
            "filename": filename,
            "filepath": filepath,
            "caption": caption,
            "date_taken": exif_data.get("date_taken"),
            "date_modified": exif_data.get("date_modified"),
            "gps_lat": exif_data.get("gps_lat"),
            "gps_lon": exif_data.get("gps_lon"),
            "location": exif_data.get("location"),
            "camera_make": exif_data.get("camera_make"),
            "camera_model": exif_data.get("camera_model"),
        }
        
        # Filter out None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
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
    where={"location": "Los Angeles, CA"}
)
```

### Combined Query + Filter
```python
# Find beach photos from California
results = collection.query(
    query_texts=["beach vacation"],
    n_results=10,
    where={"location": {"$contains": "CA"}}
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

*Schema Version: 1.0*  
*Last Updated: April 5, 2026*
