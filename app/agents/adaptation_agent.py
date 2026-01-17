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



# --- SRP: ProblemSelector ---
class ProblemSelector:
    @staticmethod
    def select(repository: ProblemRepository, topic: str, difficulty: str, exclude_ids: set) -> Optional[ProblemSpec]:
        return repository.find(topic, difficulty, exclude_ids=exclude_ids) or repository.fallback(topic, difficulty, exclude_ids=exclude_ids)

# --- SRP: ProblemPromotion ---
class ProblemPromotion:
    @staticmethod
    def promote(repository: ProblemRepository, state: SessionState) -> Optional[ProblemSpec]:
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
        candidate = repository.find(state.topic, target_diff, exclude_ids=exclude_ids) or repository.fallback(state.topic, target_diff, exclude_ids=exclude_ids)
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate

# --- SRP: ProblemRemediation ---
class ProblemRemediation:
    @staticmethod
    def remediate(repository: ProblemRepository, state: SessionState) -> Optional[ProblemSpec]:
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
        candidate = repository.find(state.topic, target_diff, exclude_ids=exclude_ids) or repository.fallback(state.topic, target_diff, exclude_ids=exclude_ids)
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate

# --- SRP: ProblemRefresh ---
class ProblemRefresh:
    @staticmethod
    def refresh(repository: ProblemRepository, state: SessionState) -> Optional[ProblemSpec]:
        exclude_ids = set(state.assigned_problem_ids)
        if state.current_problem:
            exclude_ids.add(state.current_problem.id)
        candidate = repository.find(state.topic, state.difficulty, exclude_ids=exclude_ids)
        if not candidate:
            return None
        state.mark_problem(candidate)
        return candidate

# --- SRP: FailureCounter ---
class FailureCounter:
    @staticmethod
    def recent_failures(state: SessionState) -> int:
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

# --- SRP: AdaptationAgent orchestrates the process ---
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
        problem = ProblemSelector.select(self._repository, topic, requested_difficulty, exclude_ids)
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
            next_problem = ProblemPromotion.promote(self._repository, state)
            if next_problem:
                decision = "advance"
            else:
                next_problem = ProblemRefresh.refresh(self._repository, state)
                if next_problem:
                    decision = "reinforce"
        else:
            failures = FailureCounter.recent_failures(state)
            if failures >= 3:
                next_problem = ProblemRemediation.remediate(self._repository, state)
                if next_problem:
                    decision = "remediate"
            else:
                next_problem = None

        if decision and next_problem:
            return {"decision": decision, "new_problem": next_problem.for_delivery()}
        return {}
