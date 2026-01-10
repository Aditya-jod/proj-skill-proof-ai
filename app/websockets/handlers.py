# This file will contain the logic for handling incoming WebSocket messages.
# It will route events to the appropriate agent via the SessionManager.
from fastapi import WebSocket
from .connection_manager import manager
from ..services.session_manager import session_manager

async def handle_websocket_message(websocket: WebSocket, data: dict):
    user_id = data.get("user_id")
    event_type = data.get("type")
    payload = data.get("payload")

    if not user_id or not event_type:
        return

    # Get the agent for this user, or start a new session
    agent = session_manager.get_session_agent(user_id)
    if not agent:
        agent = session_manager.start_session(user_id)

    # Let the orchestrator decide what to do
    result = agent.execute({"type": event_type, "payload": payload, "user_id": user_id})

    # If the orchestrator decided to assign a problem, send it directly to the user
    if result.get("action") == "assign_problem":
        await websocket.send_json(result['data'])
    
    # Broadcast all raw events and results to the admin dashboard
    broadcast_data = {
        "user_id": user_id,
        "type": event_type,
        "result": result
    }
    await manager.broadcast(f"{broadcast_data}")
