from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_data():
    """
    API endpoint for the admin dashboard to fetch initial data.
    Real-time updates will be pushed via WebSockets.
    """
    return {"active_users": 5, "integrity_flags": 1}
