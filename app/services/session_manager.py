from datetime import datetime
from typing import Dict, Optional

from ..agents.orchestrator_agent import OrchestratorAgent
from ..crud import crud_session
from ..crud import crud_skill_profile, crud_agent_feedback
from ..db.session import SessionLocal
from ..schemas.session import SessionCreate
from ..schemas.skill_profile import SkillProfileUpdate
from ..schemas.feedback import AgentFeedbackCreate
from .problem_repository import ProblemRepository
from .session_state import SessionState


class SessionManager:
    def __init__(self) -> None:
        self._problem_repository = ProblemRepository()
        self._active: Dict[str, Dict[str, object]] = {}

    def start_session(self, user_id: str, meta: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        if user_id in self._active:
            return self._active[user_id]

        meta = meta or {}
        mode = meta.get("mode", "learning")
        state = SessionState(user_id=user_id, mode=mode)
        state.difficulty = meta.get("difficulty", state.difficulty)
        state.topic = meta.get("topic", state.topic)
        state.session_id = self._create_persistent_session(state)
        self._hydrate_state(state)
        orchestrator = OrchestratorAgent(state, self._problem_repository)
        self._active[user_id] = {"state": state, "agent": orchestrator}
        return self._active[user_id]

    def get_session(self, user_id: str) -> Optional[Dict[str, object]]:
        return self._active.get(user_id)

    def get_agent(self, user_id: str) -> Optional[OrchestratorAgent]:
        bundle = self._active.get(user_id)
        return bundle["agent"] if bundle else None

    def get_state(self, user_id: str) -> Optional[SessionState]:
        bundle = self._active.get(user_id)
        return bundle["state"] if bundle else None

    def close_session(self, user_id: str) -> None:
        bundle = self._active.pop(user_id, None)
        if bundle:
            self._finalize_persistent_session(bundle["state"])

    def record_feedback(self, state: SessionState) -> None:
        if not state.session_id or not state.feedback_events:
            return
        db = SessionLocal()
        try:
            for event in state.feedback_events:
                payload = AgentFeedbackCreate(
                    session_id=state.session_id,
                    agent=event["agent"],
                    note=event["note"],
                )
                crud_agent_feedback.create_feedback(db, payload)
            state.feedback_events.clear()
        finally:
            db.close()

    def all_states(self) -> Dict[str, SessionState]:
        return {key: bundle["state"] for key, bundle in self._active.items()}

    def _create_persistent_session(self, state: SessionState) -> Optional[int]:
        db = SessionLocal()
        try:
            record = crud_session.create_session(db, SessionCreate(user_id=state.user_id, mode=state.mode))
            return record.id
        finally:
            db.close()

    def _finalize_persistent_session(self, state: SessionState) -> None:
        if not state.session_id:
            return
        db = SessionLocal()
        try:
            record = crud_session.get_session(db, state.session_id)
            if record:
                record.end_time = datetime.utcnow()
                record.mode = state.mode
                db.commit()
            if state.skill_profile.dirty:
                update_payload = SkillProfileUpdate(**state.skill_profile.for_update())
                crud_skill_profile.update_profile(db, state.user_id, update_payload)
                state.skill_profile.mark_clean()
            if state.feedback_events:
                for event in state.feedback_events:
                    payload = AgentFeedbackCreate(
                        session_id=state.session_id,
                        agent=event["agent"],
                        note=event["note"],
                    )
                    crud_agent_feedback.create_feedback(db, payload)
                state.feedback_events.clear()
        finally:
            db.close()

    def _hydrate_state(self, state: SessionState) -> None:
        db = SessionLocal()
        try:
            profile = crud_skill_profile.get_profile(db, state.user_id)
            if profile:
                state.skill_profile = state.skill_profile.from_persistent(profile.as_dict())
        finally:
            db.close()


session_manager = SessionManager()
