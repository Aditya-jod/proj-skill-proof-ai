from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..services.session_state import SessionState


class IntegrityAgent(BaseAgent):
    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        event = payload.get("event")
        now = datetime.utcnow()
        elapsed = (now - state.integrity.last_event_at).total_seconds()
        inactivity_alert = None
        if elapsed > 180:
            inactivity_alert = state.integrity.register_inactivity()
        state.integrity.advance(now)

        if event == "focus_lost":
            decision = state.integrity.register_focus_loss()
            message = "Focus lost multiple times" if decision != "warn" else "Focus left the assessment window"
        elif event == "focus_gained":
            decision = state.integrity.register_focus_gain()
            message = "Focus regained"
        elif event == "webcam_alert":
            flagged = payload.get("flagged", True)
            decision = state.integrity.register_webcam(flagged)
            message = "Webcam anomaly detected" if flagged else "Webcam normal"
        else:
            decision = "ack"
            message = "Integrity event recorded"

        if state.integrity.terminated:
            state.status = "terminated"
        elif state.integrity.paused:
            state.status = "paused"
        else:
            state.status = "active"

        response: Dict[str, Any] = {
            "type": "integrity",
            "decision": decision,
            "message": message,
            "integrity": state.integrity.as_dict(),
        }

        if inactivity_alert and inactivity_alert not in {decision, "ack"}:
            response.setdefault("alerts", []).append({"type": "inactivity", "decision": inactivity_alert})

        return response
