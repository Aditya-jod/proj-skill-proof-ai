from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Dict, Optional

from fastapi import Request

from ..config import settings
from ..crud import crud_user
from ..db.session import SessionLocal
from ..models.user_account import UserAccount


class AuthService:
    """Persisted account management with session storage."""

    _HASH_ITERATIONS = 150_000

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._HASH_ITERATIONS,
        )
        encoded_salt = base64.b64encode(salt).decode("utf-8")
        encoded_hash = base64.b64encode(derived).decode("utf-8")
        return f"{encoded_salt}:{encoded_hash}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            encoded_salt, encoded_hash = password_hash.split(":", 1)
        except ValueError:
            return False
        salt = base64.b64decode(encoded_salt.encode("utf-8"))
        expected = base64.b64decode(encoded_hash.encode("utf-8"))
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._HASH_ITERATIONS,
        )
        return secrets.compare_digest(derived, expected)

    def _serialize_user(self, user: UserAccount) -> Dict[str, str]:
        return {
            "role": user.role,
            "user_id": str(user.id),
            "name": user.name,
            "email": user.email,
        }

    def register_user(self, *, name: str, email: str, password: str, role: str = "candidate") -> UserAccount:
        db = SessionLocal()
        try:
            existing = crud_user.get_by_email(db, email)
            if existing:
                raise ValueError("Email already registered")
            password_hash = self._hash_password(password)
            return crud_user.create_user(db, name=name.strip(), email=email.strip(), password_hash=password_hash, role=role)
        finally:
            db.close()

    def authenticate_user(self, email: str, password: str) -> Optional[UserAccount]:
        db = SessionLocal()
        try:
            user = crud_user.get_by_email(db, email.strip())
            if not user:
                return None
            if not self._verify_password(password, user.password_hash):
                return None
            return user
        finally:
            db.close()

    def login_user(self, request: Request, user: UserAccount) -> Dict[str, str]:
        payload = self._serialize_user(user)
        request.session["user"] = payload
        return payload

    def logout(self, request: Request) -> None:
        request.session.clear()

    def current_user(self, request: Request) -> Optional[Dict[str, str]]:
        payload = request.session.get("user")
        if not isinstance(payload, dict) or "user_id" not in payload:
            return None
        try:
            user_id = int(payload["user_id"])
        except (ValueError, TypeError):
            return None
        db = SessionLocal()
        try:
            user = crud_user.get(db, user_id)
            if not user:
                request.session.clear()
                return None
            refreshed = self._serialize_user(user)
            request.session["user"] = refreshed
            return refreshed
        finally:
            db.close()

    def ensure_admin_account(self) -> None:
        admin_email = settings.ADMIN_EMAIL.strip().lower()
        admin_password = settings.ADMIN_PASSWORD
        if not admin_email or not admin_password:
            return
        db = SessionLocal()
        try:
            existing = crud_user.get_by_email(db, admin_email)
            if existing:
                if existing.role != "admin":
                    existing.role = "admin"
                    db.commit()
                return
            password_hash = self._hash_password(admin_password)
            crud_user.create_user(db, name="Administrator", email=admin_email, password_hash=password_hash, role="admin")
        finally:
            db.close()


auth_service = AuthService()



