from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .api.endpoints import sessions, admin
from .websockets.connection_manager import manager
from .websockets.handlers import handle_websocket_message
from .db import session as db_session, base as db_base
from . import models  # noqa: F401  # Ensure SQLAlchemy models are registered
from .services.session_manager import session_manager
from .core.errors import SkillProofError, build_error_payload

db_base.Base.metadata.create_all(bind=db_session.engine)

app = FastAPI(title="SkillProof AI")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(admin.router, prefix="/api", tags=["admin"])


@app.exception_handler(SkillProofError)
async def handle_skillproof_error(_: Request, exc: SkillProofError) -> JSONResponse:
    payload = build_error_payload(exc).as_dict()
    return JSONResponse(status_code=400, content={"error": payload})


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:  # pylint: disable=broad-except
    payload = build_error_payload(exc).as_dict()
    return JSONResponse(status_code=500, content={"error": payload})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/session", response_class=HTMLResponse)
async def read_session(request: Request):
    return templates.TemplateResponse("session.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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
        session_manager.close_session(client_id)
        await manager.broadcast(f"Client #{client_id} left the chat")
