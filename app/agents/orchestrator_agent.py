from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .adaptation_agent import AdaptationAgent
from .evaluation_agent import EvaluationAgent
from .hint_strategy_agent import HintStrategyAgent
from .integrity_agent import IntegrityAgent
from .learning_diagnosis_agent import LearningDiagnosisAgent
from ..core.errors import SkillProofError, build_error_payload
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
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "session_start": self._handle_session_start,
            "code_submitted": self._handle_code_submitted,
            "hint_requested": self._handle_hint_requested,
            "session_end": self._handle_session_end,
            "resume_session": self._handle_resume_session,
        }

    def _handle_resume_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Orchestrator: Resume session requested", extra={"payload": payload})
        # Only allow resume if session is paused or terminated
        if self.state.status in {"paused", "terminated"}:
            self.state.status = "active"
            self.state.integrity.paused = False
            self.state.integrity.terminated = False
            self.state.integrity.severity = "normal"
            return {
                "type": "session_resumed",
                "status": self.state.status,
                "message": "Session resumed. You may continue.",
                "integrity": self.state.integrity.as_dict(),
            }
        return {
            "type": "session_resumed",
            "status": self.state.status,
            "message": "Session is not paused or terminated. No action taken.",
            "integrity": self.state.integrity.as_dict(),
        }


    import logging
    logger = logging.getLogger("skillproof.orchestrator_agent")

    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            envelope = self._build_envelope(event_type, payload)
            self._publish_envelope(envelope)
            self._advance_integrity_clock(event_type)
            self.logger.info("Orchestrator: Handling event", extra={"event_type": event_type, "payload": payload})
            if event_type in {"focus_lost", "focus_gained", "webcam_alert"}:
                return self._handle_integrity_event(event_type, payload)
            handler = self._handlers.get(event_type)
            if handler:
                return handler(payload)
            return self._handle_default(event_type)
        except Exception as exc:  # pylint: disable=broad-except
            err = exc if isinstance(exc, SkillProofError) else SkillProofError(
                "Orchestrator failed to process event",
                context={"event_type": event_type, "payload_keys": list(payload.keys())},
            )
            error_payload = build_error_payload(err, fallback_code="orchestrator_error").as_dict()
            self.state.status = "errored"
            self.state.append_feedback("orchestrator", f"error: {error_payload['message']}")
            self.state.record_decision("orchestrator", {"decision_type": "error", "error": error_payload, "event": event_type})
            return {
                "type": "error",
                "message": error_payload["message"],
                "error": error_payload,
                "status": self.state.status,
                "decision_log": self.state.decision_history[-5:],
                "feedback": self.state.agent_feedback,
            }

    def _handle_session_start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Orchestrator: Starting session", extra={"payload": payload})
        self.state.mode = payload.get("mode", self.state.mode)
        response = self.adaptation_agent.execute(self.state, payload)
        response.setdefault("meta", {})["skill_profile"] = self.state.skill_profile.as_dict()
        response["decision_log"] = self.state.decision_history[-3:]
        return response

    def _handle_code_submitted(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Orchestrator: Code submitted", extra={"payload": payload})
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

    def _handle_hint_requested(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Orchestrator: Hint requested", extra={"payload": payload})
        hint = self.hint_agent.execute(self.state, payload)
        hint["skill_profile"] = self.state.skill_profile.as_dict()
        hint["decision_log"] = self.state.decision_history[-3:]
        return hint


    def _build_envelope(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _publish_envelope(self, envelope: Dict[str, Any]) -> None:
        self.bus.publish("events", envelope)

    def _advance_integrity_clock(self, event_type: str) -> None:
        if event_type not in {"focus_lost", "focus_gained", "webcam_alert"}:
            self.state.integrity.advance(datetime.utcnow())

    def _handle_session_start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.state.mode = payload.get("mode", self.state.mode)
        response = self.adaptation_agent.execute(self.state, payload)
        response.setdefault("meta", {})["skill_profile"] = self.state.skill_profile.as_dict()
        response["decision_log"] = self.state.decision_history[-3:]
        return response

    def _handle_code_submitted(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        evaluation_bundle = self.evaluation_agent.execute(self.state, payload)
        submission = self.state.latest_submission()
        learning = self.learning_agent.execute(
            self.state,
            payload,
            {"submission": submission, "evaluation": evaluation_bundle["result"]},
        ) if submission else {"type": "learning_diagnosis", "message": "No submission"}


    def _handle_hint_requested(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        hint = self.hint_agent.execute(self.state, payload)
        hint["skill_profile"] = self.state.skill_profile.as_dict()
        hint["decision_log"] = self.state.decision_history[-3:]
        return hint

    def _handle_integrity_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        integrity_response = self.integrity_agent.execute(self.state, {"event": event_type, **payload})
        integrity_response["decision_log"] = self.state.decision_history[-3:]
        return integrity_response

    def _handle_session_end(self, _: Dict[str, Any]) -> Dict[str, Any]:
        return self._session_summary()

    def _handle_default(self, event_type: str) -> Dict[str, Any]:
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
            "difficulty": record.difficulty,
        }
