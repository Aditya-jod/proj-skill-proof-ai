# This file will contain logic for managing active user sessions.
# For example, it might hold a dictionary mapping user_ids to
# their corresponding OrchestratorAgent instance.

class SessionManager:
    def __init__(self):
        self.active_sessions = {}

    def start_session(self, user_id: str):
        from ..agents.orchestrator_agent import OrchestratorAgent
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = OrchestratorAgent()
            print(f"Session started for user: {user_id}")
        return self.active_sessions[user_id]

    def get_session_agent(self, user_id: str):
        return self.active_sessions.get(user_id)

session_manager = SessionManager()
