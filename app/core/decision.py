from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class AgentDecision:
    decision: str
    confidence: float
    next_action: Optional[str] = None
    reason: str = ""
    policy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def as_payload(self) -> Dict[str, Any]:
        payload = {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.created_at.isoformat(),
        }
        if self.next_action:
            payload["next_action"] = self.next_action
        if self.policy:
            payload["policy"] = self.policy
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload
