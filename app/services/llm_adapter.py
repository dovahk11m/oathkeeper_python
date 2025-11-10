# app/services/llm_adapter.py (스켈레톤)
def generate_with_llm(summary: dict, prompt: str, backend: str = "ollama", **kwargs) -> str:
    if backend == "ollama":
        # http://localhost:11434/api/generate 로 요청 보내기 (로컬 LLM)
        ...
    elif backend == "openai":
        # OPENAI_API_KEY 필요
        ...
    elif backend == "huggingface":
        # HF_API_TOKEN 필요 (Inference API)
        ...
    return "fallback text"
