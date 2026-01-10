from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from .api.endpoints import sessions, admin
from .websockets.connection_manager import manager
from .websockets.handlers import handle_websocket_message
from .db import session as db_session, base as db_base

db_base.Base.metadata.create_all(bind=db_session.engine)

app = FastAPI(title="SkillProof AI")

# Mount static files (for the frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(admin.router, prefix="/api", tags=["admin"])

@app.get("/")
def read_root():
    return {"message": "Welcome to SkillProof AI Agentic System"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Add client_id to data to identify the user
            data['user_id'] = client_id
            await handle_websocket_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
