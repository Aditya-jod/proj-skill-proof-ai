import json
import random
from pathlib import Path
from typing import Iterable, List, Optional, Set

from .session_state import ProblemSpec


class ProblemRepository:
    def __init__(self, data_path: Optional[Path] = None) -> None:
        base_path = Path(__file__).resolve().parents[2] / "data" / "problems.json"
        self._data_path = Path(data_path) if data_path else base_path
        self._problems: List[ProblemSpec] = self._load()
        self._random = random.Random()

    def _load(self) -> List[ProblemSpec]:
        with self._data_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return [ProblemSpec(**item) for item in raw]

    def all(self) -> Iterable[ProblemSpec]:
        return list(self._problems)

    def by_topic(self, topic: str) -> List[ProblemSpec]:
        return [problem for problem in self._problems if problem.topic == topic]

    def find(self, topic: str, difficulty: str, *, exclude_ids: Optional[Iterable[str]] = None) -> Optional[ProblemSpec]:
        candidates = [problem for problem in self._problems if problem.topic == topic and problem.difficulty == difficulty]
        if not candidates:
            return None

        exclude: Set[str] = set(exclude_ids or [])
        filtered = [problem for problem in candidates if problem.id not in exclude]
        pool = filtered or candidates
        return self._random.choice(pool)

    def fallback(
        self,
        topic: str,
        difficulty: str,
        *,
        exclude_ids: Optional[Iterable[str]] = None,
    ) -> Optional[ProblemSpec]:
        ordering = {"easy": 0, "medium": 1, "hard": 2}
        target = ordering.get(difficulty, 1)
        topic_matches = self.by_topic(topic) or list(self._problems)
        topic_matches.sort(key=lambda item: (abs(ordering.get(item.difficulty, target) - target), item.id))
        if not topic_matches:
            return None

        exclude: Set[str] = set(exclude_ids or [])
        for problem in topic_matches:
            if problem.id not in exclude:
                return problem
        return topic_matches[0]

    def refresh(self) -> None:
        self._problems = self._load()
