from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.session_state import SessionState


class HintStrategyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="hint_strategy")
        self._payload: Dict[str, Any] = {}
        self._hint_level: Optional[str] = None
        self._hint_text: Optional[str] = None
        self._deny_message: Optional[str] = None
        self._decision_time: Optional[datetime] = None

    def observe(self, event: Dict[str, Any], state: SessionState) -> None:
        self._payload = event.get("payload", {})
        self._hint_level = None
        self._hint_text = None
        self._deny_message = None
        self._decision_time = datetime.utcnow()

    def decide(self, state: SessionState) -> AgentDecision:
        if not state.current_problem:
            self._deny_message = "No active problem"
            return AgentDecision(
                agent=self.name,
                decision_type="deny_hint",
                rationale="Cannot provide hint without an active problem.",
                confidence=0.3,
                policy="guardrails",
                metadata={"reason": "no_problem"},
            )

        if len(state.hints) >= 3:
            self._deny_message = "Hint limit reached"
            return AgentDecision(
                agent=self.name,
                decision_type="deny_hint",
                rationale="Maximum hint quota reached for this session.",
                confidence=0.7,
                policy="hint_budget",
                metadata={"reason": "limit"},
            )

        if state.hints:
            elapsed = (datetime.utcnow() - state.hints[-1].created_at).total_seconds()
            if elapsed < 45:
                self._deny_message = "Take more time before next hint"
                return AgentDecision(
                    agent=self.name,
                    decision_type="deny_hint",
                    rationale="Enforcing spacing interval between hints.",
                    confidence=0.6,
                    policy="hint_cadence",
                    metadata={"reason": "cooldown", "elapsed": elapsed},
                )

        level = self._select_level(state)
        level, hint_text = self._resolve_hint(state, level)
        if not hint_text:
            self._deny_message = "No additional hints available"
            return AgentDecision(
                agent=self.name,
                decision_type="deny_hint",
                rationale="Problem exhausted available hints for learner.",
                confidence=0.5,
                policy="resource_limit",
                metadata={"reason": "exhausted"},
            )

        self._hint_level = level
        self._hint_text = hint_text
        return AgentDecision(
            agent=self.name,
            decision_type="deliver_hint",
            rationale="Provide targeted scaffolding based on learner state.",
            confidence=0.78,
            policy="adaptive_scaffolding",
            metadata={"level": level},
        )

    def act(self, decision: AgentDecision, state: SessionState) -> Dict[str, Any]:
        if decision.decision_type != "deliver_hint" or not self._hint_level or not self._hint_text:
            return {"type": "hint", "allowed": False, "message": self._deny_message or "Hint deferred"}

        state.record_hint(self._hint_level, self._hint_text)
        payload = {
            "type": "hint",
            "allowed": True,
            "payload": {"level": self._hint_level, "text": self._hint_text},
        }
        self._hint_level = None
        self._hint_text = None
        return payload

    def explain(self, decision: AgentDecision) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "decision": decision.decision_type,
            "timestamp": (self._decision_time.isoformat() if self._decision_time else None),
            "metadata": decision.metadata,
            "message": self._deny_message,
        }

    def _select_level(self, state: SessionState) -> str:
        recent = state.latest_submission()
        used_levels = {hint.level for hint in state.hints}
        if recent and recent.reasoning_label in {"guessing", "stalled"}:
            return "conceptual" if "conceptual" not in used_levels else "directional"
        if recent and recent.tests_failed > 0:
            return "directional" if "directional" not in used_levels else "code"
        if state.skill_profile.problem_decomposition < 0.45:
            return "conceptual"
        if state.skill_profile.debugging < 0.55:
            return "directional"
        return "code"

    def _resolve_hint(self, state: SessionState, level: str) -> tuple[Optional[str], Optional[str]]:
        hints = state.current_problem.hints
        if level not in hints:
            for candidate in ("conceptual", "directional", "code"):
                if candidate in hints:
                    level = candidate
                    break
        used = {hint.level for hint in state.hints}
        if level in used and len(used) < len(hints):
            for candidate in ("conceptual", "directional", "code"):
                if candidate in hints and candidate not in used:
                    level = candidate
                    break
        if level not in hints:
            return None, None
        return level, hints[level]
