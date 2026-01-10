from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class AgentDecision:
    agent: str
    decision_type: str
    confidence: float
    rationale: str = ""
    policy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    next_action: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def decision(self) -> str:
        """Backward-compatible alias used by existing logging."""
        return self.decision_type

    def as_payload(self) -> Dict[str, Any]:
        payload = {
            "agent": self.agent,
            "decision_type": self.decision_type,
            "decision": self.decision_type,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "timestamp": self.created_at.isoformat(),
        }
        if self.next_action:
            payload["next_action"] = self.next_action
        if self.policy:
            payload["policy"] = self.policy
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload
