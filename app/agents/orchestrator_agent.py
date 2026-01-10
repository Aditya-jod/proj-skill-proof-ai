from .base_agent import BaseAgent

class OrchestratorAgent(BaseAgent):
    """
    The central brain of the system.
    It receives events and decides which agent to delegate the task to.
    """
    def __init__(self):
        # In a real app, these would be properly instantiated
        self.learning_agent = LearningDiagnosisAgent()
        self.adaptation_agent = AdaptationAgent()
        self.integrity_agent = IntegrityAgent()
        # etc.

    def execute(self, data: dict) -> dict:
        event_type = data.get("type")
        payload = data.get("payload")
        user_id = data.get("user_id")

        print(f"Orchestrator: Received event '{event_type}' from {user_id}")

        if event_type == 'session_start':
            problem_data = self.adaptation_agent.execute(payload)
            return {
                "action": "assign_problem",
                "data": {
                    "type": "problem_assigned",
                    "payload": problem_data
                }
            }
        
        elif event_type == 'code_submitted':
            return self.learning_agent.execute(payload)

        elif event_type == 'focus_lost':
            return self.integrity_agent.execute(payload)

        return {"status": "acknowledged", "event": event_type}
