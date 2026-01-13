from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from google import genai

from ..config import settings


class AIService:
    """Wrapper around Google AI Studio (Gemini) text generations."""

    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY missing. Add it to your .env file.")

        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self._model_name = "gemini-1.5-pro"
        self._generation_config = genai.types.GenerateContentConfig(
            temperature=0.4,
            top_p=0.95,
            top_k=40,
            max_output_tokens=512,
        )

    def _ask_model(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=self._generation_config,
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

    def generate_problem_spec(self, *, topic: str, difficulty: str) -> Dict[str, Any]:
        instructions = (
            "You are SkillProof AI's problem author. Create a Python coding challenge. "
            "Respond with JSON ONLY (no markdown, no commentary). The JSON object must have keys: "
            "title, description, difficulty, topic, starter_code, entrypoint, tests, hints. "
            "Follow these rules:\n"
            "- difficulty must exactly match the requested difficulty.\n"
            "- topic must exactly match the requested topic.\n"
            "- starter_code should define the function signature with TODO comments but no solution.\n"
            "- entrypoint must match the function name in starter_code.\n"
            "- tests must be an array with at least three items; each item needs args (array), kwargs (object), expected (JSON-serialisable).\n"
            "- hints must be an object with keys: conceptual, strategic, implementation. Keep each hint under 60 words.\n"
            "- Use only JSON literals; do not include python-specific syntax like tuples.\n"
        )
        prompt = (
            f"{instructions}\n"
            f"Requested topic: {topic}.\nRequested difficulty: {difficulty}.\n"
            "Return the JSON object now."
        )

        raw = self._ask_model(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise RuntimeError("Gemini returned non-JSON problem spec") from None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Unable to parse Gemini problem spec JSON") from exc

ai_service = AIService()
