from __future__ import annotations

from typing import Any, Dict, Optional

import google.generativeai as genai

from ..config import settings


class AIService:
    """Wrapper around Google AI Studio (Gemini) text generations."""

    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY missing. Add it to your .env file.")

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._model = genai.GenerativeModel("gemini-1.5-pro")
        self._generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            top_p=0.95,
            top_k=40,
            max_output_tokens=512,
        )

    def _ask_model(self, prompt: str) -> str:
        try:
            response = self._model.generate_content(
                prompt,
                generation_config=self._generation_config,
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise RuntimeError(f"Gemini request failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text

    def get_code_analysis(self, code: str, problem: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        summary_intro = (
            "You are SkillProof AI's learning diagnosis specialist. "
            "Inspect the Python submission below and produce three concise bullet points: "
            "(1) correctness status, (2) style/readability observation, and (3) one actionable improvement."
        )
        problem_context = (
            f"\nProblem description: {problem['description']}" if problem and problem.get("description") else ""
        )
        prompt = (
            f"{summary_intro}{problem_context}\nReturn each bullet on its own line and keep the response under 120 words.\n\n"
            f"Learner submission:\n```python\n{code}\n```"
        )
        try:
            analysis = self._ask_model(prompt)
        except RuntimeError:
            analysis = "Unable to retrieve AI feedback right now."
        return {"analysis": analysis}

    def generate_hint(self, context: Dict[str, Any]) -> str:
        level = context.get("level", "conceptual")
        problem = context.get("problem", {})
        fallback = context.get("fallback_hint")
        learner_code = context.get("code") or "# Learner has not submitted code yet."
        failure_summary = context.get("evaluation_summary", "")

        prompt = (
            "You are SkillProof AI's hint strategist. Provide a single, practical hint at the "
            f"{level} level for the problem below. Do not reveal the full solution. Keep the hint under 90 words, "
            "phrase it in second person (\"you\"), and end with one guiding question.\n\n"
            f"Problem title: {problem.get('title', 'Unknown Problem')}\n"
            f"Problem description: {problem.get('description', 'No description available.')}\n"
            f"Difficulty: {problem.get('difficulty', 'unknown')} | Topic: {problem.get('topic', 'unknown')}\n"
            f"Recent evaluation summary: {failure_summary or 'No automated feedback available.'}\n"
            "Existing static hint (if any): "
            f"{fallback or 'None provided.'}\n\n"
            "Latest learner submission:\n"
            f"```python\n{learner_code}\n```"
        )

        try:
            return self._ask_model(prompt)
        except RuntimeError:
            return fallback or ""

ai_service = AIService()
