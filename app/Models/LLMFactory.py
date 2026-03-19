import os
from .GeminiLLM import GeminiLLM
from .OllamaLLM import OllamaLLM

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    match provider:
        case "gemini":
            return GeminiLLM()
        case "ollama":
            return OllamaLLM(model_name='llama3')
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
