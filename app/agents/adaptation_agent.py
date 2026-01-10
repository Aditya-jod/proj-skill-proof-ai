from .base_agent import BaseAgent

# Selects problems and difficulty adjustments based on the learner's session profile.

class AdaptationAgent(BaseAgent):
    """
    Adjusts problem difficulty and selects problems based on user performance.
    """
    def execute(self, data: dict) -> dict:
        difficulty = data.get("difficulty", "easy")
        topic = data.get("topic", "recursion")
        
        print(f"Adaptation Agent: Selecting a '{difficulty}' problem about '{topic}'.")

        # In a real system, this would query a database of problems.
        # For now, we mock it.
        if difficulty == "easy":
            return {
                "title": "Fix the Factorial Function",
                "difficulty": "Easy",
            "code": "# The factorial function below has a bug. Can you fix it?\ndef factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)"
            }
        elif difficulty == "medium":
            return {
                "title": "Implement Fibonacci Sequence",
                "difficulty": "Medium",
                "code": "# Implement the Fibonacci sequence up to the nth number.\ndef fibonacci(n):\n    # Your code here\n    pass"
            }
        else: # hard
            return {
                "title": "Solve Tower of Hanoi",
                "difficulty": "Hard",
                "code": "# Implement the Tower of Hanoi puzzle.\ndef tower_of_hanoi(n, source, auxiliary, destination):\n    # Your code here\n    pass"
            }
