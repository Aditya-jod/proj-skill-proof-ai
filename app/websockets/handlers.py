import json
from typing import Any, Dict

from fastapi import WebSocket

from .connection_manager import manager
from ..services.session_manager import session_manager
from ..core.errors import SkillProofError, build_error_payload


async def handle_websocket_message(websocket: WebSocket, data: dict) -> None:
    user_id = data.get("user_id")
    event_type = data.get("type")
    payload = data.get("payload", {})

    if not user_id or not event_type:
        return

    bundle = None
    state = None
    orchestrator = None
    result: Dict[str, Any] | None = None
    error_payload: Dict[str, Any] | None = None

    try:
        bundle = session_manager.get_session(user_id)
        if event_type == "session_start" or not bundle:
            bundle = session_manager.start_session(user_id, payload if event_type == "session_start" else None)

        state = bundle.get("state") if bundle else None
        orchestrator = bundle.get("agent") if bundle else None

        if orchestrator is None:
            raise SkillProofError("Orchestrator missing for session", code="orchestrator_missing", context={"user_id": user_id})
        result = orchestrator.handle_event(event_type, payload)
        if state:
            session_manager.record_feedback(state)
        await websocket.send_json(result)
    except Exception as exc:  # pylint: disable=broad-except
        err = exc if isinstance(exc, SkillProofError) else SkillProofError(
            "Failed to handle websocket event",
            code="websocket_event_failed",
            context={"user_id": user_id, "event_type": event_type, "error": str(exc)},
        )
        error_payload = build_error_payload(err, fallback_code="websocket_error").as_dict()
        if state:
            state.append_feedback("websocket", f"error: {error_payload['message']}")
            state.record_decision("websocket", {"decision_type": "error", "error": error_payload})
        await websocket.send_json({"type": "error", "message": error_payload["message"], "error": error_payload})
    else:
        if event_type == "session_end" and state:
            session_manager.close_session(user_id)

    if not state:
        return

    broadcast_payload = {
        "user_id": user_id,
        "event": event_type,
        "status": state.status,
        "integrity": state.integrity.as_dict(),
        "skill_profile": state.skill_profile.as_dict(),
    }

    if result:
        if result.get("decision_log"):
            broadcast_payload["decision_log"] = result["decision_log"]

        if result.get("feedback"):
            broadcast_payload["feedback"] = result["feedback"]

        if result.get("type") == "code_feedback":
            evaluation = result.get("evaluation", {})
            broadcast_payload["evaluation"] = {
                "status": evaluation.get("status"),
                "score": evaluation.get("score"),
                "grade": evaluation.get("grade"),
            }
            diagnosis = result.get("diagnosis", {})
            broadcast_payload["reasoning"] = diagnosis.get("reasoning")
            broadcast_payload["guess_probability"] = diagnosis.get("guess_probability")
            if result.get("submission"):
                broadcast_payload["submission"] = result["submission"]
        elif result.get("type") == "integrity":
            broadcast_payload["integrity_decision"] = result.get("decision")
        elif result.get("type") == "hint":
            hint_payload = result.get("payload", {})
            broadcast_payload["hint_level"] = hint_payload.get("level") if result.get("allowed") else None
    elif error_payload:
        broadcast_payload["error"] = error_payload

    await manager.broadcast(json.dumps(broadcast_payload))
