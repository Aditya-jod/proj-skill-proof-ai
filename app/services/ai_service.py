# app/services/ai_service.py

import time
import json
import logging
import requests
from typing import Any, Dict, Optional, List

from ..config import settings

logger = logging.getLogger("skillproof.ai_service")


# =========================================================
# API CLIENT (transport only)
# =========================================================

class GroqClient:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY missing")

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        retries: int = 2,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        for attempt in range(retries + 1):
            try:
                logger.info("Calling Groq API", extra={"attempt": attempt})
                resp = requests.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                if resp.status_code != 200:
                    try:
                        error_body = resp.json()
                    except Exception:
                        error_body = resp.text
                    logger.error(f"Groq API error: {resp.status_code} - {error_body}")
                    resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()

            except Exception:
                logger.exception("Groq API call failed")
                if attempt >= retries:
                    raise
                time.sleep(1.5 * (attempt + 1))


# =========================================================
# PROMPT BUILDER
# =========================================================

class PromptBuilder:
    @staticmethod
    def build_problem_prompt(
        *,
        topic: str,
        difficulty: str,
        user_id: Optional[str],
        session_id: Optional[str],
        seed: Optional[int],
    ) -> str:
        return (
            "You are an expert programming challenge designer.\n"
            "Your task is to generate a DEBUGGING problem.\n\n"
            "STRICT RULES:\n"
            "- Starter code MUST contain a buggy implementation\n"
            "- DO NOT return stubs, pass, TODO, or comments-only code\n"
            "- Tests MUST fail on the buggy code\n"
            "- Problem must be original and non-trivial\n"
            "- Return ONLY valid JSON, no explanations, no markdown, no extra text, no code blocks, no comments, no preamble or postamble.\n"
            "- The 'hints' field MUST be a list of strings.\n\n"
            f"Topic: {topic}\n"
            f"Difficulty: {difficulty}\n"
            f"User: {user_id or 'anonymous'}\n"
            f"Session: {session_id or 'none'}\n"
            f"Seed: {seed or 'none'}\n\n"
            "Required JSON keys:\n"
            "id, topic, difficulty, title, description,\n"
            "starter_code, entrypoint, hints, tests, bug_hint\n"
        )


# =========================================================
# JSON EXTRACTION
# =========================================================

class JSONExtractor:
    @staticmethod
    def extract(text: str) -> Dict[str, Any]:
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Bracket counting fallback (robust to extra text)
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found in AI response")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
        raise ValueError("Unbalanced JSON")


# =========================================================
# PROBLEM VALIDATION
# =========================================================

class ProblemValidator:
    REQUIRED_FIELDS = {
        "id", "topic", "difficulty", "title",
        "description", "starter_code", "entrypoint",
        "hints", "tests", "bug_hint"
    }

    @staticmethod
    def validate(problem: Dict[str, Any]) -> None:
        missing = ProblemValidator.REQUIRED_FIELDS - problem.keys()
        if missing:
            raise ValueError(f"Missing fields: {missing}")

        code = str(problem["starter_code"]).strip()
        if not code or "pass" in code:
            raise ValueError("starter_code is a stub")

        if not isinstance(problem["tests"], list) or not problem["tests"]:
            raise ValueError("Invalid tests")

        if not isinstance(problem["hints"], list):
            raise ValueError("Invalid hints: must be a list of strings")


# =========================================================
# AI SERVICE (orchestration only)
# =========================================================

class AIService:
    def __init__(self):
        self.client = GroqClient()

    def generate_problem_spec(
        self,
        *,
        topic: str,
        difficulty: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        seed: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:

        prompt = PromptBuilder.build_problem_prompt(
            topic=topic,
            difficulty=difficulty,
            user_id=user_id,
            session_id=session_id,
            seed=seed,
        )

        max_tokens = 1500  # Increased for more complete responses
        retries = 2
        for attempt in range(retries + 1):
            raw = self.client.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            logger.info(f"Raw AI response received: {raw}")
            try:
                data = JSONExtractor.extract(raw)
                ProblemValidator.validate(data)
                return data
            except ValueError as e:
                logger.error(f"AI response parse error (attempt {attempt+1}): {e}\nRaw: {raw}")
                if attempt >= retries:
                    # Optionally, return a user-friendly error or None
                    logger.critical("AI generation failed after retries due to incomplete or malformed JSON.")
                    return None


# =========================================================
# SINGLETON
# =========================================================

_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
        logger.info("AIService singleton created")
    return _ai_service
