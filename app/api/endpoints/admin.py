from fastapi import APIRouter

from ...services.session_manager import session_manager


router = APIRouter()


@router.get("/dashboard")
def get_dashboard_data():
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
