from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.ai_service import get_ai_service
from ..services.session_state import SessionState, SubmissionRecord


class LearningDiagnosisAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="learning_diagnosis")
        self._context: Dict[str, Any] = {}
        self._submission: Optional[SubmissionRecord] = None
        self._evaluation: Dict[str, Any] = {}
        self._previous: Optional[SubmissionRecord] = None
        self._reasoning: str = "undetermined"
        self._notes: str = ""
        self._guess_probability: float = 0.0
        self._adjustments: Dict[str, float] = {}
        self._decision_time: Optional[datetime] = None

    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        self._context = event.get("context", {})
        self._submission = self._context.get("submission")
        self._evaluation = self._context.get("evaluation", {})
        self._previous = state.submissions[-2] if len(state.submissions) >= 2 else None
        self._reasoning = "undetermined"
        self._notes = ""
        self._guess_probability = 0.0
        self._adjustments = {}
        self._decision_time = datetime.utcnow()

    def decide(self, state: SessionState) -> AgentDecision:
        if not isinstance(self._submission, SubmissionRecord):
            return AgentDecision(
                agent=self.name,
                decision_type="skip_diagnosis",
                rationale="No submission provided for diagnosis.",
                confidence=0.2,
                policy="diagnostics",
            )

        self._guess_probability = self._estimate_guessing(self._submission, self._previous, self._evaluation)
        reasoning_label, adjustments, notes = self._score_reasoning(self._submission, self._previous, self._evaluation)
        self._reasoning = reasoning_label
        self._notes = notes
        self._adjustments = adjustments

        ai_notes = self._generate_ai_notes(state)
        if ai_notes:
            self._notes = f"{self._notes}\n{ai_notes}" if self._notes else ai_notes

        return AgentDecision(
            agent=self.name,
            decision_type="diagnose_learning",
            rationale="Analyse submission telemetry to update learner model.",
            confidence=0.85,
            policy="learning_diagnostics",
            metadata={
                "reasoning": reasoning_label,
                "guess_probability": round(self._guess_probability, 3),
            },
        )

    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        if decision.decision_type != "diagnose_learning" or not isinstance(self._submission, SubmissionRecord):
            return {"type": "learning_diagnosis", "message": "No submission to analyse"}

        self._submission.guess_probability = self._guess_probability
        self._submission.reasoning_label = self._reasoning
        self._submission.notes = self._notes

        state.skill_profile.apply(**self._normalize_adjustments(self._adjustments))

        return {
            "type": "learning_diagnosis",
            "reasoning": self._reasoning,
            "guess_probability": round(self._guess_probability, 3),
            "skill_profile": state.skill_profile.as_dict(),
            "notes": self._notes,
        }

    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "decision": decision.decision_type,
            "timestamp": (self._decision_time.isoformat() if self._decision_time else None),
            "reasoning": self._reasoning,
            "guess_probability": round(self._guess_probability, 3),
            "notes": self._notes,
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

    def _score_reasoning(
        self,
        submission: SubmissionRecord,
        previous: Optional[SubmissionRecord],
        evaluation: Dict[str, Any],
    ) -> tuple[str, Dict[str, float], str]:
        adjustments: Dict[str, float]
        if evaluation.get("status") == "passed":
            notes = "Consistent solution; tests all pass."
            adjustments = {
                "debugging": 0.12,
                "logic": 0.12,
                "syntax": 0.1,
                "problem_decomposition": -0.2,
                "integrity_confidence": 0.05,
            }
            return "mastered", adjustments, notes

        improvement = previous is not None and submission.tests_passed > previous.tests_passed

        if submission.guess_probability >= 0.6:
            notes = "High guess probability detected. Encourage deliberate debugging."
            adjustments = {
                "debugging": -0.05,
                "logic": -0.02,
                "syntax": -0.04,
                "problem_decomposition": 0.15,
                "integrity_confidence": -0.1,
            }
            return "guessing", adjustments, notes

        if improvement:
            notes = "Partial progress; reinforce strategy and continue iterating."
            adjustments = {
                "debugging": 0.05,
                "logic": 0.04,
                "syntax": 0.06,
                "problem_decomposition": -0.05,
                "integrity_confidence": 0.02,
            }
            return "working_through", adjustments, notes

        notes = "Stagnation detected; suggest reviewing fundamentals."
        adjustments = {
            "debugging": 0.0,
            "logic": -0.02,
            "syntax": -0.01,
            "problem_decomposition": 0.05,
            "integrity_confidence": -0.05,
        }
        return "stalled", adjustments, notes

    def _normalize_adjustments(self, adjustments: Dict[str, float]) -> Dict[str, float]:
        return {
            "debugging": adjustments.get("debugging", 0.0),
            "logic": adjustments.get("logic", 0.0),
            "syntax": adjustments.get("syntax", 0.0),
            "problem_decomposition": adjustments.get("problem_decomposition", 0.0),
            "integrity_confidence": adjustments.get("integrity_confidence", 0.0),
        }

    def _generate_ai_notes(self, state: SessionState) -> str:
        if not self._submission or not self._submission.code:
            return ""
        context = {
            "code": self._submission.code,
            "problem": {
                "title": state.current_problem.title if state.current_problem else None,
                "description": state.current_problem.description if state.current_problem else None,
            } if state.current_problem else {},
        }
        try:
            analysis = get_ai_service().analyze_behavior(context)
        except Exception:
            return ""
        return analysis.get("analysis", "").strip()
