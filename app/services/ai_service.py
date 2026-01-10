from ..config import settings
# import openai

# openai.api_key = settings.OPENAI_API_KEY

class AIService:
    """
    Wrapper for making calls to external AI services (e.g., OpenAI).
    """
    def get_code_analysis(self, code: str) -> dict:
        """
        Sends code to an AI model for analysis.
        """
        # Mock response for now
        print(f"AI Service: Analyzing code...")
        if "error" in code:
            return {"analysis": "Code contains a syntax error."}
        return {"analysis": "Code looks plausible."}

    def generate_hint(self, context: dict) -> str:
        """
        Generates a hint based on the user's context.
        """
        print(f"AI Service: Generating hint...")
        return "Conceptual Hint: Think about the base case for your recursion."

ai_service = AIService()
