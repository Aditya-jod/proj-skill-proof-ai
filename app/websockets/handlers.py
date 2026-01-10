import json

from fastapi import WebSocket

from .connection_manager import manager
from ..services.session_manager import session_manager


async def handle_websocket_message(websocket: WebSocket, data: dict) -> None:
    user_id = data.get("user_id")
    event_type = data.get("type")
    payload = data.get("payload", {})

    if not user_id or not event_type:
        return

    bundle = session_manager.get_session(user_id)
    if event_type == "session_start" or not bundle:
        bundle = session_manager.start_session(user_id, payload if event_type == "session_start" else None)

    orchestrator = bundle["agent"]
    result = orchestrator.handle_event(event_type, payload)

    await websocket.send_json(result)

    if event_type == "session_end":
        session_manager.close_session(user_id)

    # Prepare concise data for dashboards
    state = bundle["state"]
    broadcast_payload = {
        "user_id": user_id,
        "event": event_type,
        "status": state.status,
        "integrity": state.integrity.as_dict(),
        "skill_profile": state.skill_profile.as_dict(),
    }

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
    elif result.get("type") == "integrity":
        broadcast_payload["integrity_decision"] = result.get("decision")
    elif result.get("type") == "hint":
        hint_payload = result.get("payload", {})
        broadcast_payload["hint_level"] = hint_payload.get("level") if result.get("allowed") else None

    await manager.broadcast(json.dumps(broadcast_payload))
