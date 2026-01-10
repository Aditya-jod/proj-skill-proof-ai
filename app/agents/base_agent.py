from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Ensures that all agents have a consistent interface.
    """
    @abstractmethod
    def execute(self, data: dict) -> dict:
        """
        The main execution method for an agent.
        It takes data, performs its logic, and returns a result.
        """
        pass
