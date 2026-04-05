# Infrastructure Guide

**Project:** photo-library-ama  
**Date:** April 5, 2026  
**Status:** Reference Document

---

## Overview

The application runs three services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `llama-server` | `ghcr.io/ggml-org/llama.cpp:server-cuda` | `8080` | LLM inference (Llama 3.3 8B) |
| `chromadb` | `chromadb/chroma:1.5.3` | `8001` | Vector database |
| `api` | `./Dockerfile` (FastAPI) | `8000` | Application backend + static file serving |

The LLaVA captioning pipeline (`src/caption.py`) runs **outside Docker** as a one-time batch job directly on the host, using the GPU via the `transformers` library. It writes `data/captions.json` before any services are started.

---

## Prerequisites

### 1. NVIDIA Container Toolkit

Required to pass the RTX 3060 through to the `llama-server` container. Install once on the host:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify GPU passthrough is working before proceeding:

```bash
docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

You should see your RTX 3060 listed. If this fails, do not proceed — `llama-server` will silently fall back to CPU-only inference.

### 2. Download the Model

The GGUF model file must be present on the host before starting the stack. It is bind-mounted into the container at runtime — the container does not download it.

```bash
mkdir -p models

pip install huggingface_hub

huggingface-cli download bartowski/Meta-Llama-3-8B-Instruct-GGUF \
  Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  --local-dir ./models
```

Expected file: `./models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf` (~5.5 GB)

---

## llama-server (llama.cpp)

### Image

The official image published by the llama.cpp team on GitHub Container Registry:

```
ghcr.io/ggml-org/llama.cpp:server-cuda
```

This tag includes only `llama-server`, compiled with CUDA 12 support. No extra build steps are required.

### Standalone `docker run` (for testing)

Use this to verify the model loads and the GPU is being used before wiring up the full Compose stack:

```bash
docker run --rm \
  --gpus all \
  -p 8080:8080 \
  -v ./models:/models \
  -e LLAMA_ARG_MODEL=/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  -e LLAMA_ARG_CTX_SIZE=4096 \
  -e LLAMA_ARG_N_GPU_LAYERS=99 \
  -e LLAMA_ARG_HOST=0.0.0.0 \
  -e LLAMA_ARG_PORT=8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda
```

Check it is healthy and using the GPU:

```bash
# Health check
curl http://localhost:8080/health
# Expected: {"status":"ok"}

# Test inference
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

### Configuration Reference

`llama-server` accepts all arguments via `LLAMA_ARG_*` environment variables. Key ones for this project:

| Variable | Value | Notes |
|---|---|---|
| `LLAMA_ARG_MODEL` | `/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf` | Path inside container |
| `LLAMA_ARG_CTX_SIZE` | `4096` | Context window — sufficient for RAG prompt + captions |
| `LLAMA_ARG_N_GPU_LAYERS` | `99` | Offload all layers to RTX 3060; model fits in 12GB VRAM |
| `LLAMA_ARG_HOST` | `0.0.0.0` | Required for container networking |
| `LLAMA_ARG_PORT` | `8080` | Internal port |
| `LLAMA_ARG_N_PARALLEL` | `1` | Single concurrent request; keeps VRAM headroom |
| `LLAMA_ARG_FLASH_ATTN` | `1` | Enables Flash Attention 2; faster inference |

---

## Docker Compose

### File: `docker-compose.yml`

```yaml
services:

  llama-server:
    image: ghcr.io/ggml-org/llama.cpp:server-cuda
    container_name: llama-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./models:/models
    environment:
      LLAMA_ARG_MODEL: /models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
      LLAMA_ARG_CTX_SIZE: 4096
      LLAMA_ARG_N_GPU_LAYERS: 99
      LLAMA_ARG_HOST: 0.0.0.0
      LLAMA_ARG_PORT: 8080
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
      start_period: 60s   # allow time for model to load into VRAM
    networks:
      - ama-net

  chromadb:
    image: chromadb/chroma:1.5.3
    container_name: chromadb
    restart: unless-stopped
    ports:
      - "8001:8000"       # host:8001 to avoid conflict with api:8000
    volumes:
      - ./data/chroma_db:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - ama-net

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ama-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data           # captions.json, chroma_db access
      - ./photos:/app/photos:ro    # photo files served as static assets
    environment:
      CHROMA_HOST: chromadb
      CHROMA_PORT: 8000
      LLM_BASE_URL: http://llama-server:8080/v1
    depends_on:
      llama-server:
        condition: service_healthy
      chromadb:
        condition: service_healthy
    networks:
      - ama-net

networks:
  ama-net:
    driver: bridge
```

### Starting the Stack

```bash
# First time — pull images, then start
docker compose pull
docker compose up -d

# Watch logs during startup (model load takes ~30-60s)
docker compose logs -f llama-server

# Check all services are healthy
docker compose ps
```

### Stopping / Rebuilding

```bash
# Stop all services
docker compose down

# Rebuild the api image after code changes
docker compose build api
docker compose up -d api

# Full teardown including volumes (destructive — wipes chroma_db)
docker compose down -v
```

---

## Architecture Diagram

```
HOST MACHINE (Linux, RTX 3060 12GB, 48GB DDR4)
│
│  [One-time batch — runs on host, not in Docker]
│  $ python -m src.caption --input /photos --output data/captions.json
│  $ python -m src.vector_store --captions data/captions.json
│
└─── Docker: bridge network "ama-net" ─────────────────────────────────────┐
     │                                                                       │
     │   ┌─────────────────────┐                                            │
     │   │    ama-api          │                                            │
     │   │    FastAPI          │◄──── host port 8000 ◄──── Browser / User  │
     │   │    :8000            │                                            │
     │   └──────┬─────────┬───┘                                            │
     │          │         │                                                  │
     │          │         │  HTTP /v1/chat/completions                      │
     │          │         └──────────────────────────►┌──────────────────┐ │
     │          │                                      │  llama-server    │ │
     │   chromadb HttpClient                           │  llama.cpp       │ │
     │          │                                      │  :8080           │ │
     │          ▼                                      │  [GPU: RTX 3060] │ │
     │   ┌─────────────┐                              └──────────────────┘ │
     │   │  chromadb   │                                                    │
     │   │  :8000      │                                                    │
     │   │  (Chroma    │                                                    │
     │   │   server)   │                                                    │
     │   └─────────────┘                                                    │
     │                                                                       │
     │   Exposed to host:                                                    │
     │     localhost:8000  →  ama-api                                       │
     │     localhost:8001  →  chromadb  (dev access only)                   │
     │     localhost:8080  →  llama-server  (dev access only)               │
     │                                                                       │
└───────────────────────────────────────────────────────────────────────────┘

Bind mounts:
  ./models          →  llama-server:/models   (GGUF model file)
  ./data/chroma_db  →  chromadb:/data         (vector store persistence)
  ./data            →  ama-api:/app/data      (captions.json)
  ./photos          →  ama-api:/app/photos    (photo files, read-only)
```

---

## Port Reference

| Port (host) | Service | Exposed to |
|---|---|---|
| `8000` | `ama-api` (FastAPI) | Public — browser, frontend |
| `8001` | `chromadb` | Dev only — direct DB inspection |
| `8080` | `llama-server` | Dev only — direct LLM testing |

In production, only port `8000` should be exposed. Ports `8001` and `8080` are internal services that the `ama-api` container accesses over `ama-net` by service name, not via the host.

---

## Troubleshooting

**`llama-server` starts but uses CPU instead of GPU**  
The NVIDIA Container Toolkit is not configured correctly. Re-run `nvidia-ctk runtime configure --runtime=docker` and restart Docker. Confirm with `docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`.

**`api` starts before `llama-server` is ready**  
The `depends_on: condition: service_healthy` block handles this, but `start_period: 60s` in the healthcheck gives the model time to load. If the model file is large and storage is slow, increase `start_period` to `120s`.

**ChromaDB data is lost after `docker compose down`**  
Only `docker compose down -v` removes volumes. Plain `docker compose down` preserves the `./data/chroma_db` bind mount on the host. Ensure you are not accidentally using a named volume instead of a bind mount.

**Port 8000 conflict**  
If something on the host is already using port 8000, change the host-side mapping in `docker-compose.yml` to e.g. `"8080:8080"` for the api service. Internal container networking is unaffected.

---

*Document Status: Ready for Implementation*  
*Last Updated: April 5, 2026*