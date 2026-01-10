from datetime import datetime
from typing import Any, Dict, Optional

from .adaptation_agent import AdaptationAgent
from .evaluation_agent import EvaluationAgent
from .hint_strategy_agent import HintStrategyAgent
from .integrity_agent import IntegrityAgent
from .learning_diagnosis_agent import LearningDiagnosisAgent
from ..core.message_bus import MessageBus
from ..services.problem_repository import ProblemRepository
from ..services.session_state import SessionState, SubmissionRecord


class OrchestratorAgent:
    def __init__(self, state: SessionState, repository: Optional[ProblemRepository] = None) -> None:
        self.state = state
        self._repository = repository or ProblemRepository()
        self.bus = MessageBus()
        self.learning_agent = LearningDiagnosisAgent()
        self.adaptation_agent = AdaptationAgent(self._repository)
        self.integrity_agent = IntegrityAgent()
        self.hint_agent = HintStrategyAgent()
        self.evaluation_agent = EvaluationAgent()

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        envelope = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.bus.publish("events", envelope)
        if event_type not in {"focus_lost", "focus_gained", "webcam_alert"}:
            self.state.integrity.advance(datetime.utcnow())

        if event_type == "session_start":
            self.state.mode = payload.get("mode", self.state.mode)
            response = self.adaptation_agent.execute(self.state, payload)
            response.setdefault("meta", {})["skill_profile"] = self.state.skill_profile.as_dict()
            response["decision_log"] = self.state.decision_history[-3:]
            return response

        if event_type == "code_submitted":
            evaluation_bundle = self.evaluation_agent.execute(self.state, payload)
            submission = self.state.latest_submission()
            learning = self.learning_agent.execute(
                self.state,
                payload,
                {"submission": submission, "evaluation": evaluation_bundle["result"]},
            ) if submission else {"type": "learning_diagnosis", "message": "No submission"}
            adaptation_update = self.adaptation_agent.after_submission(self.state, evaluation_bundle["result"])

            response: Dict[str, Any] = {
                "type": "code_feedback",
                "evaluation": evaluation_bundle["result"],
                "submission": evaluation_bundle["submission_metrics"],
                "diagnosis": learning,
                "skill_profile": self.state.skill_profile.as_dict(),
                "integrity": self.state.integrity.as_dict(),
                "status": self.state.status,
                "decision_log": self.state.decision_history[-5:],
                "feedback": self.state.agent_feedback,
            }
            if adaptation_update.get("new_problem"):
                response["next_problem"] = {
                    "decision": adaptation_update.get("decision"),
                    "payload": adaptation_update["new_problem"],
                }
            return response

        if event_type == "hint_requested":
            hint = self.hint_agent.execute(self.state, payload)
            hint["skill_profile"] = self.state.skill_profile.as_dict()
            # keep log small for hints
            hint["decision_log"] = self.state.decision_history[-3:]
            return hint

        if event_type in {"focus_lost", "focus_gained", "webcam_alert"}:
            integrity_response = self.integrity_agent.execute(self.state, {"event": event_type, **payload})
            integrity_response["decision_log"] = self.state.decision_history[-3:]
            return integrity_response

        if event_type == "session_end":
            return self._session_summary()

        return {"type": "ack", "message": f"Unhandled event: {event_type}"}

    def _session_summary(self) -> Dict[str, Any]:
        submissions = [self._describe_submission(record) for record in self.state.submissions]
        return {
            "type": "session_summary",
            "status": self.state.status,
            "skill_profile": self.state.skill_profile.as_dict(),
            "integrity": self.state.integrity.as_dict(),
            "submissions": submissions,
            "hints": [
                {"level": hint.level, "timestamp": hint.created_at.isoformat()} for hint in self.state.hints
            ],
            "decision_log": self.state.decision_history,
            "feedback": self.state.agent_feedback,
        }

    def _describe_submission(self, record: SubmissionRecord) -> Dict[str, Any]:
        return {
            "timestamp": record.created_at.isoformat(),
            "status": record.status,
            "tests_passed": record.tests_passed,
            "tests_failed": record.tests_failed,
            "diff_ratio": round(record.diff_ratio, 3),
            "guess_probability": round(record.guess_probability, 3),
            "reasoning_label": record.reasoning_label,
        }
