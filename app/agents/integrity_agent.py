from .base_agent import BaseAgent

class IntegrityAgent(BaseAgent):
    """
    Monitors user behavior for academic integrity.
    Detects tab switching, inactivity, etc.
    """
    def execute(self, data: dict) -> dict:
        # Logic to assess integrity signals (e.g., window focus lost)
        print("Integrity Agent: Monitoring user behavior...")
        # Decision: warn, log, or terminate
        return {"integrity_action": "warning_issued"}
