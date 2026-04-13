# Context Engineering for LLM Chat

**Project:** photo-library-ama  
**Date:** April 12, 2026  
**Status:** Design Document

---

## Overview

This document defines the context structure fed to the LLM for every chat session. The context is composed of three parts:

1. **System Prompt** (fixed) — Instructions for the LLM's behavior
2. **Working Memory** — The current conversation in the session
3. **Retrieved Context** — Relevant chunks from semantic search

---

## Context Structure

```
┌─────────────────────────────────────────────────────────────┐
│                   CONTEXT                                 │
├─────────────────────────────────────────────────────────────┤
│ SYSTEM PROMPT (fixed)                                 │
│ ─────────────────                                  │
│ You are a helpful photo library assistant...        │
│                                                 │
├─────────────────────────────────────────────────────────────┤
│ WORKING MEMORY (conversation history)            │
│ ───────────────────────────────────────            │
│ User: Find photos of beach sunset                           │
│ Assistant: Here are some sunset photos...          │
│                                                 │
│ User: Show me ones from Goa                              │
│                                                 │
├─────────────────────────────────────────────────────────────┤
│ RETRIEVED CONTEXT (semantic search results)   │
│ ─────────────────────────────────────────       │
│ Chunk 1: [photo metadata + caption]              │
│ Chunk 2: [photo metadata + caption]              │
│ Chunk N: [photo metadata + caption]              │
└─────────────────────────────────────────────────────┘
```

---

## 1. System Prompt

**Status:** TBD (To Be Determined)

Example:

```
You are a helpful photo library assistant. Your task is to help users find photos 
from their collection using natural language queries.

You have access to:
- A vector database of photo captions with metadata (date, location, camera)
- Reverse-geocoded location data for each photo
- EXIF metadata including date taken, camera make/model, GPS coordinates

When responding:
1. Understand the user's query
2. Use semantic search to find relevant photos
3. Return results in the specified JSON format

Always be helpful, concise, and accurate.
```

---

## 2. Working Memory

The current conversation history in the session:

```python
working_memory = [
    {"role": "user", "content": "Find photos of sunset"},
    {"role": "assistant", "content": "Here are 2 sunset photos from your collection..."},
    {"role": "user", "content": "Show me ones from Goa"},
]
```

Working memory should include:
- Last N messages (e.g., last 5 turns = 10 messages)
- Truncated if too long for context window

---

## 3. Retrieved Context

Relevant chunks from ChromaDB semantic search, triggered by the user's query:

```python
query = "Beach sunset photos from Goa"

results = collection.query(
    query_texts=[query],
    n_results=10,
    include=["documents", "metadatas"]
)

# Retrieved chunks
retrieved_context = [
    {
        "id": "IMG_0001.jpg",
        "document": "A golden sunset over the beach",
        "metadata": {
            "filename": "IMG_0001.jpg",
            "date_taken": "2024:07:15 18:30:00",
            "location": "Benaulim, South Goa, Goa, India",
            "camera_make": "Samsung",
            "camera_model": "Galaxy S24 FE"
        }
    },
    {
        "id": "IMG_0002.jpg",
        "document": "Sunset over the Arabian Sea",
        "metadata": {
            "filename": "IMG_0002.jpg",
            "date_taken": "2024:07:16 17:45:00",
            "location": "Colva Beach, South Goa, Goa, India",
            "camera_make": "Samsung",
            "camera_model": "SM-S901E"
        }
    }
]
```

The retrieved context is formatted as text chunks for the LLM:

```
Retrieved Photos:

1. IMG_0001.jpg
   Caption: A golden sunset over the beach
   Date: 2024:07:15 18:30:00
   Location: Benaulim, South Goa, Goa, India
   Camera: Samsung Galaxy S24 FE

2. IMG_0002.jpg
   Caption: Sunset over the Arabian Sea
   Date: 2024:07:16 17:45:00
   Location: Colva Beach, South Goa, Goa, India
   Camera: Samsung SM-S901E
```

---

## Response Format

The LLM must respond in the following JSON format:

```json
{
    "user_query": "Find photos of sunset",
    "response_photos": "IMG_0001.jpg,IMG_0002.jpg",
    "response_additional_text": "Here are 2 sunset photos from your collection",
    "timestamp": "2026-04-12T15:30:00"
}
```

### Field Definitions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `user_query` | string | The original user query | "Find photos of sunset" |
| `response_photos` | string | Comma-separated photo IDs | "IMG_0001.jpg,IMG_0002.jpg" |
| `response_additional_text` | string | Natural language response | "Here are 2 sunset photos..." |
| `timestamp` | string | ISO 8601 timestamp | "2026-04-12T15:30:00" |

### Notes

- `response_photos` is stored in ChromaDB as `response_photos` metadata field (comma-separated)
- `timestamp` is stored for chat history tracking
- The actual photos are served via a separate static file endpoint

---

## Example Full Context

```
SYSTEM PROMPT (TBD):
You are a helpful photo library assistant...

---
WORKING MEMORY:
User: Find photos of beach sunset
Assistant: Here are 2 sunset photos from Goa...

User: Show me more from Kerala

---
RETRIEVED CONTEXT:
Query: "Kerala beach photos"

1. IMG_0123.jpg
   Caption: A beach scene with coconut trees
   Location: Kovalam Beach, Trivandrum, Kerala, India
   Date: 2024:03:15

2. IMG_0124.jpg
   Caption: Fishermen returning with catch at sunset
   Location: Fort Kochi, Kochi, Kerala, India
   Date: 2024:03:16
```

---

## Implementation Notes

### 1. Retrieval Strategy

- Use hybrid search: semantic (embedding) + keyword filters
- Filter by date range, location, camera if specified
- Return top N results (e.g., 10)

### 2. Context Window Management

- Monitor token count to stay within LLM context limit
- Truncate working memory if needed
- Prioritize recent messages + retrieved chunks

### 3. Chat History Storage

- After each response, store in ChromaDB collection `chat_history`
- Use `add_history_item()` from `src/handlers/chat_history.py`

---

## API Flow

```
User Query
    │
    ▼
┌─────────────────┐
│ Semantic Search │ ◄── ChromaDB query
│  (photo_captions)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Build Context  │
│ - System Prompt │
│ - Working Mem   │
│ - Retrieved   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Call LLM      │ ◄── llama-server
│  (chat API)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse Response   │
│ (JSON format)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Store in DB     │ ◄── chat_history
│ and Respond    │
└─────────────────┘
```

---

*Document Status: Draft*  
*Last Updated: April 12, 2026*