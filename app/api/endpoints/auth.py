from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from ...services.auth_service import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _build_response(payload: dict) -> dict:
    return {"status": "ok", "role": payload.get("role", "candidate"), "user": payload}


@router.post("/register")
async def register(payload: RegisterRequest, request: Request) -> dict:
    try:
        user = auth_service.register_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session_user = auth_service.login_user(request, user)
    return _build_response(session_user)


@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> dict:
    user = auth_service.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    session_user = auth_service.login_user(request, user)
    return _build_response(session_user)


@router.post("/logout")
async def logout(request: Request) -> dict:
    auth_service.logout(request)
    return {"status": "ok"}


@router.get("/me")
async def me(request: Request) -> dict:
    user = auth_service.current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return _build_response(user)
