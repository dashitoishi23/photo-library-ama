# Infrastructure Guide

**Project:** photo-library-ama  
**Date:** April 5, 2026  
**Status:** Reference Document

---

## Overview

The application runs three services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `llama-server` | `ghcr.io/ggml-org/llama.cpp:server-cuda13` | `8080` | LLM inference (Qwen 3.5 9B) |
| `chroma` | `chromadb/chroma:latest` | `8000` | Vector database |
| `ama-backend` | `./Dockerfile` (FastAPI) | `8081` | Application backend + static file serving |

The Qwen captioning pipeline (`src/handlers/generate_captions.py`) runs **outside Docker** as a one-time batch job directly on the host, using the GPU via the `transformers` library. It writes `data/captions.json` before any services are started.

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

huggingface-cli download Qwen/Qwen3.5-9B-Q4_K_M.gguf \
  --local-dir ./models
```

Expected file: `./models/Qwen_Qwen3.5-9B-Q4_K_M.gguf` (~5.5 GB)

---

## llama-server (llama.cpp)

### Image

The official image published by the llama.cpp team on GitHub Container Registry:

```
ghcr.io/ggml-org/llama.cpp:server-cuda13
```

This tag includes only `llama-server`, compiled with CUDA 13 support. No extra build steps are required.

### Standalone `docker run` (for testing)

Use this to verify the model loads and the GPU is being used before wiring up the full Compose stack:

```bash
docker run --rm \
  --gpus all \
  -p 8080:8080 \
  -v ./models:/app/models \
  -e LLAMA_ARG_MODEL=/app/models/Qwen_Qwen3.5-9B-Q4_K_M.gguf \
  -e LLAMA_ARG_CTX_SIZE=4096 \
  -e LLAMA_ARG_N_GPU_LAYERS=99 \
  -e LLAMA_ARG_HOST=0.0.0.0 \
  -e LLAMA_ARG_PORT=8080 \
  -e CUDA_VERSION=13.2.0 \
  ghcr.io/ggml-org/llama.cpp:server-cuda13
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
| `LLAMA_ARG_MODEL` | `/app/models/Qwen_Qwen3.5-9B-Q4_K_M.gguf` | Path inside container |
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

  llama_server:
    image: ghcr.io/ggml-org/llama.cpp:server-cuda13
    container_name: llama_server
    restart: unless-stopped
    ports:
      - "42069:8080"
    volumes:
      - ./models:/app/models
    environment:
      CUDA_VERSION: 13.2.0
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      LLAMA_ARG_MODEL: /app/models/Qwen_Qwen3.5-9B-Q4_K_M.gguf
      LLAMA_ARG_CTX_SIZE: 4096
      LLAMA_ARG_N_GPU_LAYERS: 99
      LLAMA_ARG_HOST: 0.0.0.0
      LLAMA_ARG_PORT: 8080
      LLAMA_ARG_N_PARALLEL: 1
      LLAMA_ARG_FLASH_ATTN: 1
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [compute,utility]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s   # allow time for model to load into VRAM
    networks:
      - ama-net

  chroma:
    image: chromadb/chroma:latest
    container_name: chroma
    restart: unless-stopped
    ports:
      - "6000:8000"
    volumes:
      - ./data/chroma_db:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - ama-net

  ama-backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ama-backend
    restart: unless-stopped
    ports:
      - "8081:8081"
    volumes:
      - ./data:/app/data
      - /mnt/f/immich-photos:/app/photos:ro
    environment:
      CHROMA_HOST: chroma
      CHROMA_PORT: 8000
      LLM_BASE_URL: http://llama_server:8080/v1
    depends_on:
      llama_server:
        condition: service_healthy
      chroma:
        condition: service_started
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
│  $ python -m src.handlers.generate_captions --input /photos --output data/captions.json
│  $ python -m src.handlers.vector_store --captions data/captions.json
│
└─── Docker: bridge network "ama-net" ─────────────────────────────────────┐
     │                                                                       │
     │   ┌─────────────────────┐                                            │
     │   │    ama-backend       │                                            │
     │   │    FastAPI          │◄──── host port 8081 ◄──── Browser / User   │
     │   │    :8081            │                                            │
     │   └──────┬─────────┬───┘                                            │
     │          │         │                                                  │
     │          │         │  HTTP /v1/chat/completions                      │
     │          │         └──────────────────────────►┌──────────────────┐ │
     │   chromadb HttpClient                           │  llama_server     │ │
     │          │                                      │  llama.cpp       │ │
     │          ▼                                      │  :8080           │ │
     │   ┌─────────────┐                              │  [GPU: RTX 3060] │ │
     │   │  chromadb   │                              └──────────────────┘ │
     │   │  :8000      │                                                    │
     │   │  (Chroma    │                                                    │
     │   │   server)   │                                                    │
     │   └─────────────┘                                                    │
     │                                                                       │
     │   Exposed to host:                                                    │
     │     localhost:8081  →  ama-backend                                   │
     │     localhost:6000  →  chroma  (dev access only)                    │
     │     localhost:42069  →  llama_server  (dev access only)            │
     │                                                                       │
     └───────────────────────────────────────────────────────────────────────┘

Bind mounts:
  ./models          →  llama_server:/app/models   (GGUF model file)
  ./data/chroma_db  →  chroma:/data         (vector store persistence)
  ./data            →  ama-backend:/app/data      (captions.json)
  /mnt/f/immich-photos →  ama-backend:/app/photos  (photo files, read-only)
```
HOST MACHINE (Linux, RTX 3060 12GB, 48GB DDR4)
│
│  [One-time batch — runs on host, not in Docker]
│  $ python -m src.handlers.generate_captions --input /photos --output data/captions.json
│
└─── Docker: bridge network "ama-net" ─────────────────────────────────────┐
     │                                                                       │
     │   ┌─────────────────────┐                                            │
     │   │    ama-backend      │                                            │
     │   │    FastAPI          │◄──── host port 8081 ◄──── Browser / User   │
     │   │    :8081            │                                            │
     │   └──────┬─────────┬───┘                                            │
     │          │         │                                                  │
     │          │         │  HTTP /v1/chat/completions                      │
     │          │         └──────────────────────────►┌──────────────────┐ │
     │          │                                      │  llama_server   │ │
     │   chromadb HttpClient                           │  llama.cpp      │ │
     │          │                                      │  :8080          │ │
     │          ▼                                      │  [GPU: RTX 3060]│ │
     │   ┌─────────────┐                              └──────────────────┘ │
     │   │  chroma     │                                                    │
     │   │  :8000      │                                                    │
     │   │  (Chroma     │                                                    │
     │   │   server)   │                                                    │
     │   └─────────────┘                                                    │
     │                                                                       │
     │   Exposed to host:                                                    │
     │     localhost:8081  →  ama-backend                                   │
     │     localhost:6000  →  chroma  (dev access only)                      │
     │     localhost:42069  →  llama_server  (dev access only)              │
     │                                                                       │
     └───────────────────────────────────────────────────────────────────────────┘

Bind mounts:
  ./models          →  llama_server:/app/models   (GGUF model file)
  ./data/chroma_db  →  chroma:/data         (vector store persistence)
  ./data            →  ama-backend:/app/data      (captions.json)
  /mnt/f/immich-photos →  ama-backend:/app/photos  (photo files, read-only)
```

---

## Port Reference

| Port (host) | Service | Exposed to |
|---|---|---|
| `8081` | `ama-backend` (FastAPI) | Public — browser, frontend |
| `6000` | `chroma` | Dev only — direct DB inspection |
| `42069` | `llama_server` | Dev only — direct LLM testing |

In production, only port `8081` should be exposed. Ports `6000` and `42069` are internal services that the `ama-backend` container accesses over `ama-net` by service name, not via the host.

---

## Troubleshooting

**`llama_server` starts but uses CPU instead of GPU**  
The NVIDIA Container Toolkit is not configured correctly. Re-run `nvidia-ctk runtime configure --runtime=docker` and restart Docker. Confirm with `docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`.

**`ama-backend` starts before `llama_server` is ready**  
The `depends_on: condition: service_healthy` block handles this, but `start_period: 60s` in the healthcheck gives the model time to load. If the model file is large and storage is slow, increase `start_period` to `120s`.

**ChromaDB data is lost after `docker compose down`**  
Only `docker compose down -v` removes volumes. Plain `docker compose down` preserves the `./data/chroma_db` bind mount on the host. Ensure you are not accidentally using a named volume instead of a bind mount.

**Port 8081 conflict**  
If something on the host is already using port 8081, change the host-side mapping in `docker-compose.yml` to e.g. `"8082:8081"` for the ama-backend service. Internal container networking is unaffected.

---

## Geocoding Utilities

### Overview

The system stores GPS coordinates from EXIF data in two fields:
- `gps_lat` — Latitude (decimal degrees, e.g., `34.0522`)
- `gps_lon` — Longitude (decimal degrees, e.g., `-118.2437`)

Two utility functions are provided:

| Function | Description | Example |
|---|---|---|
| **Reverse Geocoding** | Convert coordinates → human-readable address | `34.0522, -118.2437` → "Los Angeles, CA" |
| **Geocoding** | Convert address → coordinates | "Santa Monica Pier" → `(34.0086, -118.4970)` |

### Dependencies

```bash
pip install geopy
```

### Implementation

```python
# src/handlers/geocoding.py
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from typing import Optional
import time

_geocoder = Nominatim(user_agent="photo-library-ama")


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Convert GPS coordinates to a human-readable address."""
    try:
        location = _geocoder.reverse((lat, lon), exactly_one=True)
        if location:
            return location.address
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None


def geocode(address: str) -> Optional[tuple[float, float]]:
    """Convert an address to GPS coordinates."""
    try:
        location = _geocoder.geocode(address, exactly_one=True)
        if location:
            return (location.latitude, location.longitude)
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None


def rate_limited_geocode(address: str, delay: float = 1.0) -> Optional[tuple[float, float]]:
    """Geocode with rate limiting to respect Nominatim's usage policy."""
    time.sleep(delay)
    return geocode(address)
```

### Usage

```python
from src.handlers.geocoding import reverse_geocode, geocode

# Reverse geocode GPS coordinates from EXIF
gps_lat = 34.0522
gps_lon = -118.2437
address = reverse_geocode(gps_lat, gps_lon)
print(address)  # "Los Angeles, California, United States"

# Geocode an address to get coordinates
coords = geocode("Santa Monica Pier, CA")
print(coords)   # (34.0086, -118.4970)
```

### Rate Limits

The Nominatim service (OpenStreetMap) enforces a strict usage policy:
- Maximum 1 request per second
- No commercial use without permission

For production use, consider:
- **Paid alternatives**: Google Geocoding API, Mapbox, OpenCage
- **Local solution**: Use a self-hosted Nominatim instance or offline database (e.g., GeoPandas with Natural Earth data)

### Storing Location Data

When reverse geocoding is performed, store the result in ChromaDB metadata:

```python
metadata = {
    "filename": filename,
    "gps_lat": gps_lat,
    "gps_lon": gps_lon,
    "location": address,  # NEW: human-readable address
    # ... other fields
}
```

---

*Document Status: Ready for Implementation*  
*Last Updated: April 12, 2026*