from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.problem_repository import ProblemRepository
from ..services.session_state import ProblemSpec, SessionState

PROMOTION_PASS_REQUIREMENTS = {
    "easy": 3,
    "medium": 4,
}


class AdaptationAgent(BaseAgent):
    def __init__(self, repository: Optional[ProblemRepository] = None) -> None:
        super().__init__(name="adaptation")
        self._repository = repository or ProblemRepository()
        self._request: Dict[str, Any] = {}
        self._candidate: Optional[ProblemSpec] = None
        self._decision_timestamp: Optional[datetime] = None

    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        payload = event.get("payload", {})
        self._request = {
            "difficulty": payload.get("difficulty", state.difficulty),
            "topic": payload.get("topic", state.topic),
        }
        self._candidate = None
        self._decision_timestamp = datetime.utcnow()

    def decide(self, state: SessionState) -> AgentDecision:
        requested_difficulty = self._request.get("difficulty", state.difficulty)
        topic = self._request.get("topic", state.topic)
        exclude_ids = set(state.assigned_problem_ids)
        if state.current_problem:
            exclude_ids.add(state.current_problem.id)
        problem = self._repository.find(topic, requested_difficulty, exclude_ids=exclude_ids) or self._repository.fallback(
            topic,
            requested_difficulty,
            exclude_ids=exclude_ids,
        )
        self._candidate = problem
        if not problem:
            return AgentDecision(
                agent=self.name,
                decision_type="assignment_error",
                rationale="No suitable problems available for requested criteria.",
                confidence=0.25,
                policy="fallback",
                metadata={"requested_topic": topic, "requested_difficulty": requested_difficulty},
            )
        return AgentDecision(
            agent=self.name,
            decision_type="assign_problem",
            rationale="Selected problem matching requested topic and difficulty.",
            confidence=0.82,
            policy="adaptive_curriculum",
            metadata={
                "problem_id": problem.id,
                "difficulty": problem.difficulty,
                "topic": problem.topic,
            },
        )

    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        if decision.decision_type != "assign_problem" or not self._candidate:
            state.status = "paused"
            return {"type": "assignment_error", "message": "No problems available"}
        state.mark_problem(self._candidate)
        state.status = "active"
        response = {
            "type": "problem_assigned",
            "payload": self._candidate.for_delivery(),
        }
        self._candidate = None
        return response

    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "decision": decision.decision_type,
            "requested": self._request,
            "timestamp": (self._decision_timestamp.isoformat() if self._decision_timestamp else None),
            "metadata": decision.metadata,
        }

    def after_submission(self, state: SessionState, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        if not state.current_problem:
            return {}

        decision = None
        next_problem: Optional[ProblemSpec] = None
        if evaluation.get("status") == "passed":
            next_problem = self._promote_problem(state)
            if next_problem:
                decision = "advance"
            else:
                next_problem = self._refresh_problem(state)
                if next_problem:
                    decision = "reinforce"
        else:
            failures = self._recent_failures(state)
            if failures >= 3:
                next_problem = self._remediate_problem(state)
                if next_problem:
                    decision = "remediate"
            else:
                next_problem = None

        if decision and state.current_problem and next_problem:
            return {"decision": decision, "new_problem": state.current_problem.for_delivery()}
        return {}

    def _promote_problem(self, state: SessionState) -> Optional[ProblemSpec]:
        required_passes = PROMOTION_PASS_REQUIREMENTS.get(state.difficulty, 3)
        if state.consecutive_passes() < required_passes:
            return None

        ladder = ["easy", "medium", "hard"]
        try:
            idx = ladder.index(state.difficulty)
        except ValueError:
            idx = 0
        if idx >= len(ladder) - 1:
            return None
        target_diff = ladder[idx + 1]
        exclude_ids = set(state.assigned_problem_ids)
        if state.current_problem:
            exclude_ids.add(state.current_problem.id)
        candidate = self._repository.find(state.topic, target_diff, exclude_ids=exclude_ids) or self._repository.fallback(
            state.topic,
            target_diff,
            exclude_ids=exclude_ids,
        )
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
        exclude_ids = set(state.assigned_problem_ids)
        if state.current_problem:
            exclude_ids.add(state.current_problem.id)
        candidate = self._repository.find(state.topic, target_diff, exclude_ids=exclude_ids) or self._repository.fallback(
            state.topic,
            target_diff,
            exclude_ids=exclude_ids,
        )
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate

    def _recent_failures(self, state: SessionState) -> int:
        current_difficulty = state.difficulty
        count = 0
        inspected = 0
        for record in reversed(state.submissions):
            if record.difficulty != current_difficulty:
                continue
            inspected += 1
            if record.status != "passed":
                count += 1
            if inspected >= 3:
                break
        return count

    def _refresh_problem(self, state: SessionState) -> Optional[ProblemSpec]:
        exclude_ids = set(state.assigned_problem_ids)
        if state.current_problem:
            exclude_ids.add(state.current_problem.id)
        candidate = self._repository.find(state.topic, state.difficulty, exclude_ids=exclude_ids)
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate
