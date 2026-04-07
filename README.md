# Photo Library AMA

A RAG-powered chatbot that answers questions about your personal photo collection using semantic search and a locally hosted LLM.

---

## What It Does

```
Photos → EXIF Extraction → Captioning (BLIP-2) → ChromaDB (vector store)
                                                              ↓
User Query → Semantic Search → LLM (Llama-3.3-8B) → Answer
```

Ask questions like:
- *"Show me photos from my beach vacation"*
- *"When was the last photo of my dog taken?"*
- *"What events happened in 2024?"*

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Captioning | BLIP-2 (Salesforce) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Vector DB | Chroma (persistent) |
| LLM | Llama-3.3-8B-Instruct (Q4_K_M GGUF) |
| LLM Runtime | llama.cpp (CUDA, Docker) |
| App Framework | FastAPI |

---

## Setup

### 1. Download Model

```bash
mkdir -p models
huggingface-cli download bartowski/Llama-3.3-8B-Instruct-GGUF \
  Llama-3.3-8B-Instruct-Q4_K_M.gguf --local-dir ./models
```

### 2. Launch llama.cpp

```yaml
# docker-compose.yml
version: '3.8'
services:
  llama-server:
    image: ghcr.io/ggml-org/llama.cpp:server-cuda
    ports:
      - "8080:8080"
    volumes:
      - ./models:/models
    environment:
      LLAMA_ARG_MODEL: /models/Llama-3.3-8B-Instruct-Q4_K_M.gguf
      LLAMA_ARG_CTX_SIZE: 4096
      LLAMA_ARG_N_GPU_LAYERS: 99
      LLAMA_ARG_PORT: 8080
      LLAMA_ARG_HOST: 0.0.0.0
      LLAMA_ARG_N_PARALLEL: 1
      LLAMA_ARG_FLASH_ATTN: 1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

```bash
docker compose up -d
curl http://localhost:8080/health
```

### 3. Launch AMA + ChromaDB

```yaml
# docker-compose.yml (replace the above)
version: '3.8'
services:
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - ./data/chroma_db:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3

  ama:
    build: .
    ports:
      - "8001:8000"
    environment:
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      LLM_BASE_URL: http://host.docker.internal:8080/v1
    volumes:
      - ./data:/app/data
      - ./photos:/app/photos:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      chroma:
        condition: service_healthy
```

```bash
mkdir -p data/photos data/chroma_db photos
docker compose up -d
curl http://localhost:8001/health
```

---

## Run Backend (Development)

```bash
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8001
```

---

## Index Your Photos

Run once to caption and index your photos:

```bash
# Caption photos
python -m src.caption --input ./photos --output data/captions.json

# Build vector store
python -m src.vector_store --captions data/captions.json
```

---

## Data Schema

### ChromaDB Collection: `photo_captions`

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Filename |
| `document` | string | Generated caption |
| `metadata.filename` | string | Image filename |
| `metadata.filepath` | string | Full path |
| `metadata.caption` | string | Caption text |
| `metadata.date_taken` | string | DateTimeOriginal EXIF |
| `metadata.gps_lat` | float | GPS latitude |
| `metadata.gps_lon` | float | GPS longitude |
| `metadata.location` | string | Reverse-geocoded location |
| `metadata.camera_make` | string | Camera manufacturer |
| `metadata.camera_model` | string | Camera model |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/photos` | List indexed photos |
| POST | `/query` | Query with RAG |
| POST | `/index` | Re-index photos |

---

## Project Structure

```
photo-library-ama/
├── src/
│   ├── caption.py        # Image captioning
│   ├── exif.py           # EXIF extraction
│   ├── vector_store.py   # ChromaDB operations
│   ├── rag.py            # RAG pipeline
│   ├── llm.py            # LLM client
│   └── api.py            # FastAPI app
├── photos/               # Your photos
├── data/
│   ├── captions.json     # Generated captions
│   └── chroma_db/        # Vector store
├── models/               # GGUF model
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Ports

| Port | Service |
|------|---------|
| 8001 | AMA API |
| 8000 | ChromaDB (dev) |
| 8080 | llama-server (dev) |

---

## Prerequisites

- NVIDIA GPU with CUDA
- Docker + Docker Compose
- NVIDIA Container Toolkit for GPU passthrough

```bash
# Verify GPU passthrough
docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```
