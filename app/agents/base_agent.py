from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..services.session_state import SessionState


class BaseAgent(ABC):
    """Shared contract for all specialist agents."""

    @abstractmethod
    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError
