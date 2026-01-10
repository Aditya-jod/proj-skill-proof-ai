from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..services.session_state import SessionState, SubmissionRecord


class LearningDiagnosisAgent(BaseAgent):
    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        submission: Optional[SubmissionRecord] = context.get("submission")
        evaluation: Dict[str, Any] = context.get("evaluation", {})
        if not submission:
            return {"type": "learning_diagnosis", "message": "No submission to analyse"}

        previous = state.submissions[-2] if len(state.submissions) >= 2 else None
        guess_probability = self._estimate_guessing(submission, previous, evaluation)
        submission.guess_probability = guess_probability

        reasoning_label, deltas, notes = self._score_reasoning(submission, previous, evaluation)
        submission.reasoning_label = reasoning_label
        submission.notes = notes

        state.skill_profile.apply(*deltas)

        return {
            "type": "learning_diagnosis",
            "reasoning": reasoning_label,
            "guess_probability": round(guess_probability, 3),
            "skill_profile": state.skill_profile.as_dict(),
            "notes": notes,
        }

    def _estimate_guessing(self, submission: SubmissionRecord, previous: Optional[SubmissionRecord], evaluation: Dict[str, Any]) -> float:
        score = 0.25
        if previous:
            if submission.diff_ratio > 0.85 and evaluation.get("status") != "passed":
                score += 0.45
            if submission.time_delta < 25 and submission.diff_ratio < 0.2:
                score += 0.25
            if submission.tests_passed <= previous.tests_passed and submission.diff_ratio < 0.3:
                score += 0.2
        if evaluation.get("status") == "passed":
            score -= 0.4
        elif evaluation.get("failed", 0) > evaluation.get("passed", 0):
            score += 0.1
        return max(0.0, min(1.0, score))

    def _score_reasoning(self, submission: SubmissionRecord, previous: Optional[SubmissionRecord], evaluation: Dict[str, Any]) -> tuple[str, tuple[float, float, float, float], str]:
        if evaluation.get("status") == "passed":
            notes = "Consistent solution; tests all pass."
            return "mastered", (0.12, 0.12, 0.1, -0.2), notes

        improvement = False
        if previous:
            improvement = submission.tests_passed > previous.tests_passed

        if submission.guess_probability >= 0.6:
            notes = "High guess probability detected. Encourage deliberate debugging."
            return "guessing", (-0.05, -0.02, -0.04, 0.15), notes

        if improvement:
            notes = "Partial progress; reinforce strategy and continue iterating."
            return "working_through", (0.05, 0.04, 0.06, -0.05), notes

        notes = "Stagnation detected; suggest reviewing fundamentals."
        return "stalled", (0.0, -0.02, -0.01, 0.05), notes
