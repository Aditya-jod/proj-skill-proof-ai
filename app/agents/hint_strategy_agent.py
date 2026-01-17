from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..core.decision import AgentDecision
from ..services.ai_service import get_ai_service
from ..services.session_state import SessionState



# --- SRP: HintLevelSelector ---
class HintLevelSelector:
    @staticmethod
    def select(state: SessionState) -> str:
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

# --- SRP: HintFormatter ---
class HintFormatter:
    @staticmethod
    def resolve_hint(state: SessionState, level: str) -> tuple[Optional[str], Optional[str]]:
        import logging
        logger = logging.getLogger("skillproof.hint_strategy_agent")
        hints = state.current_problem.hints
        if not hints or not isinstance(hints, list):
            logger.error("Hints missing or not a list in current_problem: %s", hints)
            return None, None

        level_order = ["conceptual", "directional", "code"]
        level_to_index = {name: idx for idx, name in enumerate(level_order)}
        used = {hint.level for hint in state.hints}
        chosen_idx = level_to_index.get(level, 0)
        for idx, name in enumerate(level_order):
            if idx < len(hints) and name not in used:
                chosen_idx = idx
                level = name
                break
        if chosen_idx >= len(hints):
            for idx, hint in enumerate(hints):
                if idx not in [level_to_index.get(h.level, -1) for h in state.hints]:
                    chosen_idx = idx
                    level = level_order[idx] if idx < len(level_order) else f"level_{idx}"
                    break
        fallback_hint = hints[chosen_idx] if chosen_idx < len(hints) else None
        ai_hint = HintFormatter._generate_ai_hint(state, level, fallback_hint)
        if ai_hint:
            return level, ai_hint
        if fallback_hint:
            return level, fallback_hint
        logger.warning("No available hints for level %s. Hints: %s", level, hints)
        return None, None

    @staticmethod
    def _generate_ai_hint(state: SessionState, level: str, fallback: Optional[str]) -> Optional[str]:
        if not state.current_problem:
            return fallback
        latest = state.latest_submission()
        evaluation_summary = ""
        if latest:
            evaluation_summary = (
                f"Last submission status: {latest.status}. Tests passed: {latest.tests_passed}/{latest.total_tests}. "
                f"Reasoning label: {latest.reasoning_label}."
            )
        context = {
            "level": level,
            "problem": {
                "title": state.current_problem.title,
                "description": state.current_problem.description,
                "difficulty": state.current_problem.difficulty,
                "topic": state.current_problem.topic,
            },
            "code": latest.code if latest else None,
            "evaluation_summary": evaluation_summary,
            "fallback_hint": fallback,
        }
        try:
            hint = get_ai_service().generate_hint(context).strip()
        except Exception:
            hint = ""
        if hint:
            return hint
        return fallback

# --- SRP: HintStrategyAgent orchestrates the process ---
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

        level = HintLevelSelector.select(state)
        level, hint_text = HintFormatter.resolve_hint(state, level)
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
