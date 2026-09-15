import os
import requests
import dspy

def check_ollama_available(url: str = "http://localhost:11434") -> bool:
    """Check if local Ollama instance is running and reachable."""
    try:
        res = requests.get(f"{url}/api/tags", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

def get_dspy_lm():
    """
    Returns an configured DSPy LM instance.
    Checks Ollama first, then OpenAI if key is present, otherwise configures a default fallback LM.
    """
    ollama_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "ollama/phi3.5:3.8b-mini-instruct-q4_K_M")
    
    if check_ollama_available(ollama_url):
        print(f"[INFO] Connected to local Ollama at {ollama_url}")
        lm = dspy.LM(
            model=model_name,
            api_base=ollama_url,
            temperature=0.0,
            num_predict=1000,
            num_ctx=8192
        )
    elif os.getenv("OPENAI_API_KEY"):
        openai_model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
        print(f"[INFO] Using OpenAI API: {openai_model}")
        lm = dspy.LM(
            model=openai_model,
            temperature=0.0
        )
    else:
        print(f"[WARNING] Ollama is not running on {ollama_url} and OPENAI_API_KEY is not set.")
        print(f"[WARNING] Configured DSPy LM for default local Ollama instance.")
        lm = dspy.LM(
            model=model_name,
            api_base=ollama_url,
            temperature=0.0,
            num_predict=1000,
            num_ctx=8192
        )
    
    return lm
