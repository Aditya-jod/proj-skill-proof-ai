from datetime import datetime
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from ..services.session_state import SessionState


class HintStrategyAgent(BaseAgent):
    def execute(self, state: SessionState, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not state.current_problem:
            return {"type": "hint", "allowed": False, "message": "No active problem"}

        if len(state.hints) >= 3:
            return {"type": "hint", "allowed": False, "message": "Hint limit reached"}

        if state.hints:
            elapsed = (datetime.utcnow() - state.hints[-1].created_at).total_seconds()
            if elapsed < 45:
                return {"type": "hint", "allowed": False, "message": "Take more time before next hint"}

        level = self._select_level(state)
        level, hint_text = self._resolve_hint(state, level)
        if not hint_text:
            return {"type": "hint", "allowed": False, "message": "No additional hints available"}

        state.record_hint(level, hint_text)
        return {"type": "hint", "allowed": True, "payload": {"level": level, "text": hint_text}}

    def _select_level(self, state: SessionState) -> str:
        recent = state.latest_submission()
        used_levels = {hint.level for hint in state.hints}
        if recent and recent.reasoning_label in {"guessing", "stalled"}:
            return "conceptual" if "conceptual" not in used_levels else "directional"
        if recent and recent.tests_failed > 0:
            return "directional" if "directional" not in used_levels else "code"
        if state.skill_profile.conceptual < 0.45:
            return "conceptual"
        if state.skill_profile.implementation < 0.55:
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
