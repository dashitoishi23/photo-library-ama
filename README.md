# Photo Library AMA

A RAG-powered chatbot that answers questions about your personal photo collection using semantic search and a locally hosted LLM.

---

## What It Does

```
Photos → EXIF Extraction → Captioning (BLIP-2/Qwen VLA) → ChromaDB (vector store)
                                                                      ↓
User Query → Semantic Search → LLM (Qwen 3.5 9B) → Answer
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
| LLM | Qwen 3.5 9B (Q4_K_M GGUF) |
| LLM Runtime | llama.cpp (CUDA 13, Docker) |
| App Framework | FastAPI |
| Frontend | Vite + React |

---

## Prerequisites

- NVIDIA GPU with CUDA (RTX 3060 12GB recommended)
- Docker + Docker Compose
- NVIDIA Container Toolkit for GPU passthrough

```bash
# Verify GPU passthrough
docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

---

## Setup

### 1. Download LLM Model

```bash
mkdir -p models
huggingface-cli download Qwen/Qwen3.5-9B-Q4_K_M.gguf --local-dir ./models
```

Expected file: `./models/Qwen_Qwen3.5-9B-Q4_K_M.gguf`

### 2. Photo Directory

Photos are read from `/mnt/f/immich-photos` (configured in docker-compose.yml). Ensure this path contains your images.

### 3. Run with Docker Compose

```bash
docker compose up -d
```

### Services

| Port | Service |
|------|---------|
| 8081 | AMA Backend (FastAPI) |
| 2398 | AMA Frontend (Vite/React) |
| 42069 | llama.cpp server (LLM) |
| 6000 | ChromaDB (vector store) |

### Health Checks

```bash
curl http://localhost:8081/health    # Backend
curl http://localhost:2398           # Frontend (returns HTML)
curl http://localhost:42069/health   # LLM server
curl http://localhost:6000/api/v2/heartbeat  # ChromaDB
```

---

## Run Backend (Development)

```bash
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8081
```

---

## Index Your Photos

Run once to caption and index your photos:

```bash
# Caption photos (uses BLIP-2 on GPU)
python -m src.handlers.generate_captions --input /mnt/f/immich-photos --output data/captions.json

# Build vector store (if using ChromaDB directly)
python -m src.handlers.embeddings --captions data/captions.json
```

Or use the API endpoint:

```bash
# Trigger re-indexing via API
curl -X POST http://localhost:8081/index-photos
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/photos` | List indexed photos |
| GET | `/stats` | Collection statistics |
| POST | `/query` | Query with RAG |
| POST | `/index-photos` | Re-index photos |
| POST | `/generate-captions` | Generate captions |

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
| `metadata.embedding_text` | string | Text used for embedding |

---

## Project Structure

```
photo-library-ama/
├── src/
│   ├── api.py                    # FastAPI app
│   ├── config.py                 # Configuration
│   ├── __main__.py              # CLI entry point
│   ├── handlers/
│   │   ├── generate_captions.py # Image captioning (BLIP-2)
│   │   ├── embeddings.py         # ChromaDB operations
│   │   ├── search_photos.py    # Semantic search
│   │   ├── chat_history.py     # Chat history storage
│   │   ├── geocoding.py     # Reverse geocoding
│   │   ├── tools.py          # Tool definitions
│   │   └── agentic_loop.py  # Agentic RAG loop
│   └── llm/
│       ├── llm_call.py         # LLM API calls
│       └── generate_system_prompt.py
├── photo-library-ama-ui/         # Frontend (Vite/React)
├── data/
│   ├── captions.json           # Generated captions
│   └── chroma_db/             # Vector store
├── design-docs/                # Design documentation
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Troubleshooting

**llama_server uses CPU instead of GPU**
- Ensure NVIDIA Container Toolkit is installed and configured
- Run: `nvidia-ctk runtime configure --runtime=docker`
- Restart Docker: `sudo systemctl restart docker`

**Port conflicts**
- 8081: ama-backend
- 2398: ama-frontend
- 42069: llama_server
- 6000: chroma

---

*Last Updated: April 30, 2026*