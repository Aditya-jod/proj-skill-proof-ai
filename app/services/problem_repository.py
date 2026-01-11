import random
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from uuid import uuid4

from .ai_service import ai_service
from .session_state import ProblemSpec


class ProblemRepository:
    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], List[ProblemSpec]] = {}
        self._random = random.Random()

    def _cache_key(self, topic: str, difficulty: str) -> Tuple[str, str]:
        return (topic.strip().lower(), difficulty.strip().lower())

    def _cache(self, topic: str, difficulty: str) -> List[ProblemSpec]:
        key = self._cache_key(topic, difficulty)
        return self._store.setdefault(key, [])

    def _generate_problem(self, topic: str, difficulty: str, *, exclude_ids: Set[str]) -> Optional[ProblemSpec]:
        attempts = 0
        while attempts < 3:
            attempts += 1
            payload = ai_service.generate_problem_spec(topic=topic, difficulty=difficulty)
            if not isinstance(payload, dict):
                continue

            payload.setdefault("topic", topic)
            payload.setdefault("difficulty", difficulty)
            payload.setdefault("hints", {})
            payload.setdefault("tests", [])
            payload.setdefault("starter_code", "")
            payload.setdefault("entrypoint", "solve")

            payload["title"] = str(payload.get("title", f"{topic.title()} challenge"))
            payload["description"] = str(payload.get("description", "Implement the required behaviour."))
            payload["starter_code"] = str(payload.get("starter_code", ""))
            payload["entrypoint"] = str(payload.get("entrypoint", "solve"))

            problem_id = payload.get("id") or f"{topic.lower()}-{difficulty.lower()}-{uuid4().hex[:8]}"
            if problem_id in exclude_ids:
                continue

            payload["id"] = problem_id

            topic_value = str(payload.get("topic", topic)).strip().lower() or topic
            difficulty_value = str(payload.get("difficulty", difficulty)).strip().lower() or difficulty
            payload["topic"] = topic_value
            payload["difficulty"] = difficulty_value

            hints = payload.get("hints", {})
            if not isinstance(hints, dict):
                hints = {}
            payload["hints"] = {
                "conceptual": hints.get("conceptual", "Break the problem into smaller steps."),
                "strategic": hints.get("strategic", "Consider edge cases and input constraints."),
                "implementation": hints.get("implementation", "Outline helper functions before coding."),
            }

            tests: Sequence[Dict[str, object]] = payload.get("tests", [])  # type: ignore[assignment]
            filtered_tests: List[Dict[str, object]] = []
            for test in tests:
                if not isinstance(test, dict):
                    continue
                args = test.get("args", [])
                kwargs = test.get("kwargs", {})
                if not isinstance(args, list) or not isinstance(kwargs, dict):
                    continue
                filtered_tests.append({
                    "args": args,
                    "kwargs": kwargs,
                    "expected": test.get("expected"),
                })
            if not filtered_tests:
                continue

            payload["tests"] = filtered_tests

            try:
                problem = ProblemSpec(**payload)
            except TypeError:
                continue

            cache_bucket = self._cache(problem.topic, problem.difficulty)
            cache_bucket.append(problem)
            return problem
        return None

    def all(self) -> Iterable[ProblemSpec]:
        for problems in self._store.values():
            for problem in problems:
                yield problem

    def by_topic(self, topic: str) -> List[ProblemSpec]:
        topic_key = topic.strip().lower()
        collected: List[ProblemSpec] = []
        for (cached_topic, _), problems in self._store.items():
            if cached_topic == topic_key:
                collected.extend(problems)
        return collected

    def find(self, topic: str, difficulty: str, *, exclude_ids: Optional[Iterable[str]] = None) -> Optional[ProblemSpec]:
        exclude: Set[str] = set(exclude_ids or [])
        bucket = self._cache(topic, difficulty)
        candidates = [problem for problem in bucket if problem.id not in exclude]
        if not candidates:
            generated = self._generate_problem(topic, difficulty, exclude_ids=exclude)
            if generated:
                return generated
        else:
            return self._random.choice(candidates)
        return None

    def fallback(
        self,
        topic: str,
        difficulty: str,
        *,
        exclude_ids: Optional[Iterable[str]] = None,
    ) -> Optional[ProblemSpec]:
        exclude: Set[str] = set(exclude_ids or [])
        ordering = ["easy", "medium", "hard"]
        try:
            idx = ordering.index(difficulty)
        except ValueError:
            idx = 1

        search_order = ordering[idx:] + ordering[:idx]
        for diff in search_order:
            candidate = self.find(topic, diff, exclude_ids=exclude)
            if candidate:
                return candidate
        return self._generate_problem(topic, difficulty, exclude_ids=exclude)

    def refresh(self) -> None:
        self._store.clear()
