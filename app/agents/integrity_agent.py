from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.session_state import SessionState


class IntegrityAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="integrity")
        self._payload: Dict[str, Any] = {}
        self._timestamp: Optional[datetime] = None
        self._elapsed: float = 0.0
        self._pending_inactivity: bool = False
        self._last_message: str = ""

    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        self._payload = event.get("payload", {})
        self._timestamp = datetime.utcnow()
        self._elapsed = (self._timestamp - state.integrity.last_event_at).total_seconds()
        self._pending_inactivity = self._elapsed > 180
        self._last_message = ""

    def decide(self, state: SessionState) -> AgentDecision:
        event_type = self._payload.get("event", "unknown")
        metadata = {
            "event": event_type,
            "elapsed_since_last": round(self._elapsed, 2),
            "inactivity_check": self._pending_inactivity,
        }
        if event_type == "focus_lost":
            return AgentDecision(
                agent=self.name,
                decision_type="register_focus_loss",
                rationale="User focus left the assessment window.",
                confidence=0.8,
                policy="integrity_focus",
                metadata=metadata,
            )
        if event_type == "focus_gained":
            return AgentDecision(
                agent=self.name,
                decision_type="register_focus_gain",
                rationale="User returned focus to the assessment window.",
                confidence=0.7,
                policy="integrity_focus",
                metadata=metadata,
            )
        if event_type == "webcam_alert":
            metadata["flagged"] = self._payload.get("flagged", True)
            return AgentDecision(
                agent=self.name,
                decision_type="register_webcam",
                rationale="Process webcam monitoring signal.",
                confidence=0.75,
                policy="integrity_webcam",
                metadata=metadata,
            )
        return AgentDecision(
            agent=self.name,
            decision_type="record_event",
            rationale="Track generic integrity event for auditing.",
            confidence=0.5,
            policy="integrity_audit",
            metadata=metadata,
        )

    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        now = self._timestamp or datetime.utcnow()
        inactivity_alert = None
        if self._pending_inactivity:
            inactivity_alert = state.integrity.register_inactivity()
        state.integrity.advance(now)

        event_decision = decision.decision_type
        if event_decision == "register_focus_loss":
            result = state.integrity.register_focus_loss()
            message = "Focus lost multiple times" if result != "warn" else "Focus left the assessment window"
        elif event_decision == "register_focus_gain":
            result = state.integrity.register_focus_gain()
            message = "Focus regained"
        elif event_decision == "register_webcam":
            flagged = bool(decision.metadata.get("flagged", True))
            result = state.integrity.register_webcam(flagged)
            message = "Webcam anomaly detected" if flagged else "Webcam normal"
        else:
            result = "ack"
            message = "Integrity event recorded"

        if state.integrity.terminated:
            state.status = "terminated"
        elif state.integrity.paused:
            state.status = "paused"
        else:
            state.status = "active"

        self._last_message = message
        response: Dict[str, Any] = {
            "type": "integrity",
            "decision": result,
            "message": message,
            "integrity": state.integrity.as_dict(),
        }

        if inactivity_alert and inactivity_alert not in {result, "ack"}:
            response.setdefault("alerts", []).append({"type": "inactivity", "decision": inactivity_alert})

        return response

    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "decision": decision.decision_type,
            "message": self._last_message,
            "timestamp": (self._timestamp.isoformat() if self._timestamp else None),
            "metadata": decision.metadata,
        }
