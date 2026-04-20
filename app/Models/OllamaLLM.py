import os

import ollama
from .BaseLLM import BaseLLM


class OllamaLLM(BaseLLM):

    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.host = os.getenv("OLLAMA_HOST", "").strip()

    def generate(self, prompt: str) -> str:
        try:
            kwargs = {}
            if self.host:
                kwargs["host"] = self.host

            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response["message"]["content"]
        except Exception as e:
            return f"Error generating response: {str(e)}"