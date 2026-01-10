from .base_agent import BaseAgent

# Balances when and how hints are delivered so guidance stays meaningful.

class HintStrategyAgent(BaseAgent):
    """
    Decides if and what kind of hint to provide.
    Prevents spoon-feeding the user.
    """
    def execute(self, data: dict) -> dict:
        # Logic to determine hint necessity and level (conceptual, directional, code)
        print("Hint Strategy Agent: Deciding on a hint...")
        return {"hint": "Have you considered using a different data structure?"}
