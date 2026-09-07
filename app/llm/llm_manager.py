from app.llm.groq_client import GroqClient


class LLMManager:

    def __init__(self):
        self.client = GroqClient()

    def generate(self, prompt: str) -> str:
        return self.client.generate(prompt)