from google import genai
from .BaseLLM import BaseLLM
import os
import dotenv

dotenv.load_dotenv()

class GeminiLLM(BaseLLM):

    def __init__(self):
        self.model_name = os.getenv("GEMINI_MODEL")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def generate(self, prompt:str) -> str:
        try: 
            response = self.client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents={'text' : prompt},
                config={
                    'temperature': 0.2,
                    'top_p': 0.9,
                    'top_k': 20,
                },
            )
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"
