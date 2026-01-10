from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..services.problem_repository import ProblemRepository
from ..services.session_state import ProblemSpec, SessionState


class AdaptationAgent(BaseAgent):
    def __init__(self, repository: Optional[ProblemRepository] = None) -> None:
        self._repository = repository or ProblemRepository()

    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        requested_difficulty = payload.get("difficulty", state.difficulty)
        topic = payload.get("topic", state.topic)
        problem = self._repository.find(topic, requested_difficulty) or self._repository.fallback(topic, requested_difficulty)
        if not problem:
            state.status = "paused"
            return {"type": "assignment_error", "message": "No problems available"}
        state.mark_problem(problem)
        state.status = "active"
        return {"type": "problem_assigned", "payload": problem.for_delivery()}

    def after_submission(self, state: SessionState, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        if not state.current_problem:
            return {}

        decision = None
        if evaluation.get("status") == "passed":
            next_problem = self._promote_problem(state)
            if next_problem:
                decision = "advance"
        else:
            failures = self._recent_failures(state)
            if failures >= 3:
                next_problem = self._remediate_problem(state)
                if next_problem:
                    decision = "remediate"
            else:
                next_problem = None

        if decision and state.current_problem:
            return {"decision": decision, "new_problem": state.current_problem.for_delivery()}
        return {}

    def _promote_problem(self, state: SessionState) -> Optional[ProblemSpec]:
        ladder = ["easy", "medium", "hard"]
        try:
            idx = ladder.index(state.difficulty)
        except ValueError:
            idx = 0
        if idx >= len(ladder) - 1:
            return None
        target_diff = ladder[idx + 1]
        candidate = self._repository.find(state.topic, target_diff)
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate

    def _remediate_problem(self, state: SessionState) -> Optional[ProblemSpec]:
        ladder = ["easy", "medium", "hard"]
        try:
            idx = ladder.index(state.difficulty)
        except ValueError:
            idx = 0
        if idx == 0:
            return None
        target_diff = ladder[idx - 1]
        candidate = self._repository.find(state.topic, target_diff)
        if not candidate or state.current_problem and candidate.id == state.current_problem.id:
            return None
        state.mark_problem(candidate)
        return candidate

    def _recent_failures(self, state: SessionState) -> int:
        recent = state.submissions[-3:]
        return sum(1 for record in recent if record.status != "passed")
