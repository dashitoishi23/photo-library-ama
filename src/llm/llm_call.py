import requests
from typing import Optional, Any
from src.config import get_settings

def llm_call(
    messages: list[dict[str, Any]],
    temperature: float = 0.0,
    max_tokens: int = 500
) -> dict[str, Any]:
    settings = get_settings()
    print(f"{settings}")
    url = f"http://{settings.LLAMA_HOST}:{settings.LLAMA_PORT}/v1/chat/completions"
    
    payload = {
        "model": "local-model",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    response.raise_for_status()
    
    return response.json()