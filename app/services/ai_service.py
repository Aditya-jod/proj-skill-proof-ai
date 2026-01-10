from groq import Groq

from ..config import settings

class AIService:
    """Wrapper around Groq chat completions."""

    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY missing. Add it to your .env file.")

        self._client = Groq(api_key=settings.GROQ_API_KEY)
        self._model = "llama3-8b-8192"

    def _ask_model(self, prompt: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as exc:
            return f"Error contacting Groq: {exc}"

    def get_code_analysis(self, code: str) -> dict:
        prompt = (
            "Summarize the correctness, style, and one improvement for this Python snippet.\n\n"
            f"```python\n{code}\n```"
        )
        return {"analysis": self._ask_model(prompt)}

    def generate_hint(self, context: dict) -> str:
        code = context.get("code", "# Code not provided")
        prompt = (
            "Provide a single actionable hint for the student working on this code."
            " Avoid giving the solution.\n\n"
            f"```python\n{code}\n```"
        )
        return self._ask_model(prompt)

ai_service = AIService()
