import ollama
from .BaseLLM import BaseLLM

class OllamaLLM(BaseLLM):

    def __init__(self, model_name:str = "llama3"):
        self.model_name = model_name

    def generate(self, prompt:str) -> str:
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            print(response)
            return response['message']['content']
        except Exception as e:
            return f"Error generating response: {str(e)}"