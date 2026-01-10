from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..services.code_evaluator import CodeEvaluator
from ..services.session_state import SessionState


class EvaluationAgent(BaseAgent):
    def __init__(self) -> None:
        self._evaluator = CodeEvaluator()

    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        code = payload.get("code", "")
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
