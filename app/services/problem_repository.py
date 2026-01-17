# app/services/problem_repository.py

import logging
import random
from typing import Dict, Iterable, List, Optional, Set, Tuple
from uuid import uuid4

from .ai_service import get_ai_service
from .session_state import ProblemSpec

logger = logging.getLogger("skillproof.problem_repository")


# =========================================================
# CACHE
# =========================================================

class ProblemCache:
    def __init__(self):
        self._store: Dict[Tuple[str, str, str, str], List[ProblemSpec]] = {}

    def _key(self, topic: str, difficulty: str, user_id: Optional[str], session_id: Optional[str]) -> Tuple[str, str, str, str]:
        return (
            topic.lower(),
            difficulty.lower(),
            user_id or "_anon_",
            session_id or "_anon_",
        )

    def get(self, topic: str, difficulty: str, user_id: Optional[str], session_id: Optional[str]) -> List[ProblemSpec]:
        return self._store.setdefault(self._key(topic, difficulty, user_id, session_id), [])

    def add(self, problem: ProblemSpec, user_id: Optional[str], session_id: Optional[str]) -> None:
        bucket = self.get(problem.topic, problem.difficulty, user_id, session_id)
        bucket.append(problem)
        if len(bucket) > 5:
            del bucket[:-5]

    def clear(self) -> None:
        self._store.clear()


# =========================================================
# GENERATOR
# =========================================================

class ProblemGenerator:
    MAX_ATTEMPTS = 5

    def generate(
        self,
        topic: str,
        difficulty: str,
        exclude_ids: Set[str],
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> Optional[ProblemSpec]:

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                payload = get_ai_service().generate_problem_spec(
                    topic=topic,
                    difficulty=difficulty,
                    user_id=user_id,
                    session_id=session_id,
                    seed=random.randint(0, 1_000_000),
                    temperature=0.8,
                )
            except Exception:
                logger.exception("AI generation failed")
                continue

            payload.setdefault("id", f"{topic}-{difficulty}-{uuid4().hex[:8]}")
            if payload["id"] in exclude_ids:
                continue

            try:
                return ProblemSpec(**payload)
            except Exception:
                logger.exception("Invalid ProblemSpec from AI")
                return None

        return None


# =========================================================
# REPOSITORY
# =========================================================

class ProblemRepository:
    def __init__(self):
        self._cache = ProblemCache()
        self._generator = ProblemGenerator()
        self._rng = random.Random()

    def _fallback_problem(self, topic: str, difficulty: str) -> ProblemSpec:
        return ProblemSpec(
            id=f"fallback-{uuid4().hex[:8]}",
            topic=topic,
            difficulty=difficulty,
            title="Debug the Logic Error",
            description="The function below contains a logical bug. Fix it.",
            starter_code=(
                "def solve(n):\n"
                "    if n == 0:\n"
                "        return 1  # BUG\n"
                "    return n + solve(n - 1)\n"
            ),
            entrypoint="solve",
            hints={
                "conceptual": "Check the base case.",
                "strategic": "What should solve(0) return?",
                "implementation": "Fix the incorrect return value.",
            },
            tests=[
                {"args": [3], "kwargs": {}, "expected": 6},
                {"args": [0], "kwargs": {}, "expected": 0},
            ],
            bug_hint="Base case returns incorrect value",
        )

    def find(
        self,
        topic: str,
        difficulty: str,
        *,
        exclude_ids: Optional[Iterable[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ProblemSpec:

        exclude = set(exclude_ids or [])
        cached = [
            p for p in self._cache.get(topic, difficulty, user_id, session_id)
            if p.id not in exclude
        ]

        if cached:
            return self._rng.choice(cached)

        problem = self._generator.generate(topic, difficulty, exclude, user_id, session_id)
        if problem:
            self._cache.add(problem, user_id, session_id)
            return problem

        logger.critical("AI generation failed — using fallback")
        fallback = self._fallback_problem(topic, difficulty)
        self._cache.add(fallback, user_id, session_id)
        return fallback

    def refresh(self) -> None:
        self._cache.clear()
# =========================================================