# Genesis: RAG-Powered Photo Collection Chatbot

**Date:** April 5, 2026  
**Status:** Planning Complete → Build Mode Engaged

---

## 1. Overview

This document outlines the architecture and implementation plan for building a RAG (Retrieval-Augmented Generation) powered chatbot that answers queries about a personal photo collection. The system generates captions for each image, stores them in a vector database, performs semantic search, and generates responses using a locally hosted LLM.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RAG Photo Chatbot Architecture                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────┐ │
│  │  Photos  │───▶│    EXIF      │───▶│ Captioning   │───▶│ Vector  │ │
│  │ (Local)  │    │  Extraction  │    │   (BLIP-2)   │    │  Store  │ │
│  └──────────┘    └──────────────┘    └──────────────┘    │(Chroma) │ │
│                                                                └────┬────┘ │
│                                                                     │      │
│                                                                     ▼      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         RAG Pipeline                              │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │   │
│  │  │    User     │───▶│  Semantic   │───▶│   LLM Response      │ │   │
│  │  │   Query     │    │   Search    │    │ Generation (llama.cpp)│ │   │
│  │  └─────────────┘    └─────────────┘    └─────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| OS | Linux | Target platform |
| Hardware | NVIDIA GPU | CUDA acceleration for LLM |
| Photo Count | 1,000 - 10,000 | Moderate scale |
| Captioning Model | BLIP-2 (Salesforce) | Fast, lightweight, quality captions |
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 | Fast, efficient embeddings |
| Vector Database | Chroma | Python-native, simple setup |
| LLM | Llama-3.1-8B-Instruct (GGUF) | Locally hosted, instruction-tuned |
| LLM Runtime | llama.cpp (CUDA-enabled) | GPU acceleration |

---

## 4. Implementation Phases

### Phase 1: Infrastructure & Setup

| Task | Description |
|------|-------------|
| 1.1 | Create project directory structure |
| 1.2 | Determine photo collection location (folder path) |
| 1.3 | Set up Python environment (venv/conda) |
| 1.4 | Install core dependencies: `transformers`, `chromadb`, `llama-cpp-python`, `sentence-transformers`, `torch`, `Pillow` |

**Dependencies:**
```bash
pip install transformers chromadb llama-cpp-python sentence-transformers torch pillow
# For CUDA support:
CMAKE_CUDA=on pip install llama-cpp-python
```

---

### Phase 2: Image Captioning Pipeline

| Task | Description |
|------|-------------|
| 2.1 | Select captioning model (recommend: BLIP-2 or LLaVA-1.5) |
| 2.2 | Download/load captioning model (`Salesforce/blip2-opt-2.7b` or `llava-hf/llava-1.5-7b-hf`) |
| 2.3 | Create image loader to scan photo directory (supported: jpg, jpeg, png, webp) |
| 2.4 | Implement batch captioning script with progress tracking |
| 2.5 | Run captioning on all photos (1K-10K images) |
| 2.6 | Save captions to JSON/CSV (filename → caption mapping) |

**Output Format:**
```json
{
  "photos": [
    {
      "filename": "IMG_0001.jpg",
      "caption": "A sunset over the ocean with orange and pink hues"
    }
  ]
}
```

---

### Phase 2.5: EXIF Metadata Extraction

| Task | Description |
|------|-------------|
| 2.7 | Implement EXIF extraction using Pillow (`PIL.Image.getexif()`) |
| 2.8 | Extract date taken (`DateTimeOriginal`), GPS coordinates (`GPSInfo`), camera make/model |
| 2.9 | Reverse geocode GPS coordinates to location names (optional) |
| 2.10 | Merge EXIF data with captions (filename → caption + EXIF) |

**EXIF Fields Extracted:**

| Field | EXIF Tag | Type | Example |
|-------|----------|------|---------|
| `date_taken` | `DateTimeOriginal` | string | `2024:07:15 18:30:00` |
| `gps_lat` | `GPSInfo[GPSLatitude]` | float | `34.0522` |
| `gps_lon` | `GPSInfo[GPSLongitude]` | float | `-118.2437` |
| `location` | (reverse geocoded) | string | `Santa Monica, CA` |
| `camera_make` | `Make` | string | `Apple` |
| `camera_model` | `Model` | string | `iPhone 15 Pro` |

**Combined Output Format:**
```json
{
  "photos": [
    {
      "filename": "IMG_0001.jpg",
      "filepath": "/photos/vacation/IMG_0001.jpg",
      "caption": "A sunset over the ocean with orange and pink hues",
      "date_taken": "2024:07:15 18:30:00",
      "gps_lat": 34.0522,
      "gps_lon": -118.2437,
      "location": "Santa Monica, CA",
      "camera_make": "Apple",
      "camera_model": "iPhone 15 Pro"
    }
  ]
}
```

---

### Phase 3: Vector Database Setup

| Task | Description |
|------|-------------|
| 3.1 | Initialize Chroma client (persistent) |
| 3.2 | Create collection `photo_captions` |
| 3.3 | Load embedding model (sentence-transformers/all-MiniLM-L6-v2) |
| 3.4 | Generate embeddings for all captions |
| 3.5 | Store (id=filename, embedding, metadata={caption, filepath}) in Chroma |
| 3.6 | Persist Chroma database to disk |

**Data Model:**
```python
{
  "id": "IMG_0001.jpg",
  "embedding": [0.123, -0.456, ...],  # 384-dim vector
  "metadata": {
    "caption": "A sunset over the ocean with orange and pink hues",
    "filepath": "/photos/IMG_0001.jpg"
  }
}
```

---

### Phase 4: LLM Setup (llama.cpp)

| Task | Description |
|------|-------------|
| 4.1 | Download Llama-3.1-8B-Instruct GGUF model |
| 4.2 | Select quantization level (Q4_K_M recommended for 8GB VRAM) |
| 4.3 | Set up llama-cpp-python bindings with CUDA |
| 4.4 | Configure GPU acceleration |
| 4.5 | Test model inference with sample prompt |

**Model Options:**
| Quantization | VRAM Required | Quality |
|--------------|---------------|---------|
| Q2_K | ~4GB | Lower |
| Q4_K_M | ~8GB | Recommended |
| Q5_K_S | ~10GB | Higher |

**Download Source:**
- HuggingFace: `uygarkurt/Llama-3.1-8B-Instruct-GGUF`
- Or: `TheBloke/Llama-3.1-8B-Instruct-GGUF`

---

### Phase 5: RAG Chatbot Implementation

| Task | Description |
|------|-------------|
| 5.1 | Create query embedding function using sentence-transformers |
| 5.2 | Implement semantic search (top-k=3 retrieval from Chroma) |
| 5.3 | Build prompt template with retrieved context |
| 5.4 | Implement LLM response generation |
| 5.5 | Create chat interface (CLI or REST API) |

**Prompt Template:**
```
You are a helpful assistant that answers questions about a photo collection.
Based on the following images and their captions, answer the user's question.

Context:
- {filename1}: {caption1}
- {filename2}: {caption2}
- {filename3}: {caption3}

User Question: {query}

Answer:
```

---

### Phase 6: Optimization & Polish

| Task | Description |
|------|-------------|
| 6.1 | Add batch processing for captioning |
| 6.2 | Implement incremental updates (detect new photos) |
| 6.3 | Add error handling and logging |
| 6.4 | Performance tuning (KV cache, context length) |
| 6.5 | Optional: Add photo display with answers |

---

## 5. Project Structure

```
photo-library-ama/
├── design-docs/
│   ├── genesis.md
│   └── schema.md
├── src/
│   ├── __init__.py
│   ├── exif.py               # EXIF metadata extraction
│   ├── caption.py            # Image captioning module
│   ├── vector_store.py       # Chroma DB operations
│   ├── llm.py                # llama.cpp integration
│   ├── rag.py                # RAG pipeline
│   └── cli.py                # Chat interface
├── data/
│   ├── photos/               # Photo collection (to be determined)
│   ├── captions.json         # Generated captions with EXIF
│   └── chroma_db/           # Persisted vector database
├── models/
│   └── Llama-3.1-8B-Instruct-Q4_K_M.gguf
├── requirements.txt
└── README.md
```

---

## 6. Usage Workflow

### Initial Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure photo path
export PHOTO_DIR="/path/to/photos"

# 3. Extract EXIF metadata (optional - creates metadata.json)
python -m src.exif --input /path/to/photos --output data/metadata.json

# 4. Run captioning (includes EXIF merge if metadata.json exists)
python -m src.caption --input /path/to/photos --output data/captions.json

# 5. Build vector database
python -m src.vector_store --captions data/captions.json

# 6. Start chatbot
python -m src.cli
```

### Query Examples
```
User: "Show me photos of beaches"
-> Semantic search -> Retrieve beach-related captions -> LLM generates response

User: "When was the last photo of my dog taken?"
-> Semantic search for "dog" -> Find most recent matching photo
```

---

## 7. Key Decisions Pending

- [ ] **Photo location:** Directory path to be determined
- [ ] **Captioning model:** BLIP-2 (faster) vs LLaVA (more descriptive)
- [ ] **Quantization level:** Q4_K_M vs Q5_K_S
- [ ] **API interface:** CLI-only or REST API with frontend

---

## 8. Next Steps

1. Confirm photo collection location
2. Set up Python environment
3. Install dependencies
4. Begin Phase 2: Captioning pipeline

---

*Document Status: Ready for Implementation*
