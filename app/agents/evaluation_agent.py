from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.code_evaluator import CodeEvaluator
from ..services.session_state import SessionState


class EvaluationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="evaluation")
        self._evaluator = CodeEvaluator()
        self._latest_payload: Dict[str, Any] = {}
        self._last_result: Dict[str, Any] = {}
        self._decision_timestamp: Optional[datetime] = None

    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        self._latest_payload = event.get("payload", {})
        self._decision_timestamp = datetime.utcnow()
        self._last_result = {}

    def decide(self, state: SessionState) -> AgentDecision:
        if not state.current_problem:
            return AgentDecision(
                agent=self.name,
                decision_type="await_assignment",
                rationale="No active problem to evaluate.",
                confidence=0.1,
                policy="idle",
            )
        return AgentDecision(
            agent=self.name,
            decision_type="evaluate_submission",
            rationale="Process learner submission and update performance metrics.",
            confidence=0.9,
            policy="standard_evaluation",
            metadata={"has_code": bool(self._latest_payload.get("code"))},
        )

    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        if decision.decision_type != "evaluate_submission":
            return {"type": "evaluation", "result": {"status": "waiting"}}

        code = self._latest_payload.get("code", "")
        result = self._evaluator.evaluate(code, state.current_problem)
        submission = state.add_submission(code, result)

        score_bundle = self._score_submission(state, submission, result)
        enriched = {
            **result,
            "score": score_bundle["score"],
            "grade": score_bundle["grade"],
            "penalties": score_bundle["penalties"],
            "time_from_start": score_bundle["time_from_start"],
        }

        if enriched["status"] == "passed" and state.mode == "test":
            state.status = "completed"

        self._last_result = enriched

        return {
            "type": "evaluation",
            "result": enriched,
            "submission_metrics": {
                "diff_ratio": round(submission.diff_ratio, 3),
                "time_delta": round(submission.time_delta, 3),
                "tests_passed": submission.tests_passed,
                "tests_failed": submission.tests_failed,
            },
        }

    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "decision": decision.decision_type,
            "timestamp": (self._decision_timestamp.isoformat() if self._decision_timestamp else None),
            "metadata": decision.metadata,
            "result_status": self._last_result.get("status"),
        }

    def _score_submission(self, state: SessionState, submission, result: Dict[str, Any]) -> Dict[str, Any]:
        total = max(1, result.get("total_tests", submission.total_tests))
        correctness_ratio = result.get("passed", submission.tests_passed) / total
        hint_penalty = len(state.hints) * 5
        time_penalty = min(20, submission.time_delta / 60 * 5) if submission.time_delta else 0
        integrity_penalty = {"normal": 0, "warn": 8, "paused": 18, "terminated": 100}.get(state.integrity.severity, 0)
        raw_score = max(0, min(100, correctness_ratio * 100 - hint_penalty - time_penalty - integrity_penalty))
        grade = "pass" if correctness_ratio == 1.0 and raw_score >= 70 else "progress" if correctness_ratio >= 0.5 else "retry"

        time_from_start = (submission.created_at - state.started_at).total_seconds()

        return {
            "score": round(raw_score, 2),
            "grade": grade,
            "penalties": {
                "hint": round(hint_penalty, 2),
                "time": round(time_penalty, 2),
                "integrity": integrity_penalty,
            },
            "time_from_start": round(time_from_start, 2),
        }
