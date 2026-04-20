import os

from openai import AzureOpenAI

from .BaseLLM import BaseLLM


class AzureOpenAILLM(BaseLLM):
    def __init__(self):
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01").strip()

        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required for AzureOpenAILLM")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required for AzureOpenAILLM")

        self.deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip()
        if not self.deployment:
            raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT is required for AzureOpenAILLM")

        self.temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.2"))
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error generating response: {str(e)}"
