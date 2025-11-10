import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

async def generate_ko(system: str, prompt: str) -> str:
    payload = {
        "model": "llama3.1",
        "system": system,
        "prompt": prompt,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
