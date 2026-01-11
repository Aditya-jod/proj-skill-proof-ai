from fastapi import APIRouter, HTTPException, Request

from ...services.session_manager import session_manager
from ...services.auth_service import auth_service


router = APIRouter()


@router.get("/dashboard")
def get_dashboard_data(request: Request):
    user = auth_service.current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")
    sessions = [state.as_summary() for state in session_manager.all_states().values()]
    total_flags = sum(
        summary["integrity"]["focus_losses"] + summary["integrity"]["inactivity_flags"] + summary["integrity"]["webcam_flags"]
        for summary in sessions
    )
    return {
        "active_users": len(sessions),
        "integrity_flags": total_flags,
        "sessions": sessions,
    }
