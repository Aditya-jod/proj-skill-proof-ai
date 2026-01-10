from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from ..core.decision import AgentDecision
from ..core.errors import AgentExecutionError, build_error_payload
from ..services.session_state import SessionState


class BaseAgent(ABC):
    """Interface for autonomous agents in SkillProof AI."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        """Consume raw events and update internal memory."""

    @abstractmethod
    def decide(self, state: SessionState) -> AgentDecision:
        """Produce a decision based on current state and internal memory."""

    @abstractmethod
    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        """Execute the decision, mutating state or emitting payloads."""

    @abstractmethod
    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        """Return a description of why the decision was made."""

    def reflect(self, decision: AgentDecision, state: SessionState) -> None:
        """Optional feedback hook for learning from outcomes."""
        return

    def execute(self, state: SessionState, payload: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        event = {"payload": payload, "context": context or {}}
        try:
            self.observe(event, state)
            decision = self.decide(state)
            outcome = self.act(decision, state)
            state.record_decision(self.name, decision.as_payload())
            self.reflect(decision, state)
            explanation = self.explain(decision)
            message = explanation.get("message") if isinstance(explanation, dict) else None
            note = message or decision.rationale
            state.append_feedback(self.name, note)
            if isinstance(outcome, dict):
                outcome.setdefault("explanation", explanation)
            return outcome
        except Exception as exc:  # pylint: disable=broad-except
            wrapped = exc if isinstance(exc, AgentExecutionError) else AgentExecutionError(
                f"{self.name} failed to complete execution", context={"agent": self.name, "payload_keys": list(payload.keys())}
            )
            error_payload = build_error_payload(wrapped, fallback_code="agent_error").as_dict()
            state.record_decision(self.name, {"decision_type": "error", "error": error_payload})
            state.append_feedback(self.name, f"error: {error_payload['message']}")
            return {"type": "agent_error", "agent": self.name, "error": error_payload}
