from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


@dataclass
class ProblemSpec:
    id: str
    title: str
    difficulty: str
    topic: str
    description: str
    starter_code: str
    entrypoint: str
    tests: List[Dict[str, Any]]
    hints: Dict[str, str]

    def for_delivery(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "topic": self.topic,
            "description": self.description,
            "code": self.starter_code,
        }


@dataclass
class SubmissionRecord:
    code: str
    created_at: datetime
    diff_ratio: float
    time_delta: float
    tests_passed: int
    tests_failed: int
    total_tests: int
    status: str
    guess_probability: float = 0.0
    reasoning_label: str = "undetermined"
    notes: str = ""


@dataclass
class HintRecord:
    level: str
    text: str
    created_at: datetime


@dataclass
class IntegrityState:
    focus_losses: int = 0
    inactivity_flags: int = 0
    webcam_flags: int = 0
    tab_switches: int = 0
    webcam_risk: float = 0.0
    severity: str = "normal"
    paused: bool = False
    terminated: bool = False
    last_event_at: datetime = field(default_factory=datetime.utcnow)

    def advance(self, timestamp: datetime) -> None:
        self.last_event_at = timestamp

    def register_focus_loss(self) -> str:
        self.focus_losses += 1
        if self.focus_losses >= 5:
            self.terminated = True
            self.paused = False
            self.severity = "terminated"
            return "terminate"
        if self.focus_losses >= 3:
            self.paused = True
            self.severity = "paused"
            return "pause"
        self.severity = "warn"
        return "warn"

    def register_focus_gain(self) -> str:
        if not self.terminated:
            self.paused = False
            if self.focus_losses <= 1 and self.inactivity_flags == 0 and self.webcam_flags == 0:
                self.severity = "normal"
        return "resume"

    def register_inactivity(self) -> str:
        self.inactivity_flags += 1
        if self.inactivity_flags >= 2 and not self.terminated:
            self.severity = "warn"
        if self.inactivity_flags >= 3:
            self.paused = True
            self.severity = "paused"
            return "pause"
        return "warn"

    def register_webcam(self, flagged: bool) -> str:
        if not flagged:
            return "ok"
        self.webcam_flags += 1
        self.webcam_risk = min(1.0, self.webcam_risk + 0.25)
        if self.webcam_flags >= 2:
            self.severity = "warn"
        if self.webcam_flags >= 3:
            self.paused = True
            self.severity = "paused"
            return "pause"
        return "warn"

    def register_tab_switch(self) -> str:
        self.tab_switches += 1
        if self.tab_switches >= 4:
            self.severity = "terminated"
            self.terminated = True
            self.paused = False
            return "terminate"
        if self.tab_switches >= 2:
            self.severity = "warn"
        return "warn"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "focus_losses": self.focus_losses,
            "inactivity_flags": self.inactivity_flags,
            "webcam_flags": self.webcam_flags,
            "tab_switches": self.tab_switches,
            "webcam_risk": round(self.webcam_risk, 3),
            "severity": self.severity,
            "paused": self.paused,
            "terminated": self.terminated,
        }


@dataclass
class SkillProfile:
    debugging: float = 0.5
    logic: float = 0.5
    syntax: float = 0.5
    problem_decomposition: float = 0.5
    integrity_confidence: float = 0.5
    attempts: int = 0
    dirty: bool = False

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def apply(
        self,
        *,
        debugging: float = 0.0,
        logic: float = 0.0,
        syntax: float = 0.0,
        problem_decomposition: float = 0.0,
        integrity_confidence: float = 0.0,
    ) -> None:
        self.debugging = self._clamp(self.debugging + debugging)
        self.logic = self._clamp(self.logic + logic)
        self.syntax = self._clamp(self.syntax + syntax)
        self.problem_decomposition = self._clamp(self.problem_decomposition + problem_decomposition)
        self.integrity_confidence = self._clamp(self.integrity_confidence + integrity_confidence)
        self.attempts += 1
        self.dirty = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "debugging": round(self.debugging, 3),
            "logic": round(self.logic, 3),
            "syntax": round(self.syntax, 3),
            "problem_decomposition": round(self.problem_decomposition, 3),
            "integrity_confidence": round(self.integrity_confidence, 3),
            "attempts": self.attempts,
        }

    def mark_clean(self) -> None:
        self.dirty = False

    @classmethod
    def from_persistent(cls, payload: Dict[str, Any]) -> "SkillProfile":
        instance = cls(
            debugging=payload.get("debugging", 0.5),
            logic=payload.get("logic", 0.5),
            syntax=payload.get("syntax", 0.5),
            problem_decomposition=payload.get("problem_decomposition", 0.5),
            integrity_confidence=payload.get("integrity_confidence", 0.5),
            attempts=payload.get("attempts", 0),
        )
        instance.dirty = False
        return instance

    def for_update(self) -> Dict[str, Any]:
        return {
            "debugging": self.debugging,
            "logic": self.logic,
            "syntax": self.syntax,
            "problem_decomposition": self.problem_decomposition,
            "integrity_confidence": self.integrity_confidence,
            "attempts": self.attempts,
        }


@dataclass
class SessionState:
    user_id: str
    mode: str = "learning"
    session_id: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_problem: Optional[ProblemSpec] = None
    difficulty: str = "easy"
    topic: str = "recursion"
    status: str = "active"
    submissions: List[SubmissionRecord] = field(default_factory=list)
    hints: List[HintRecord] = field(default_factory=list)
    integrity: IntegrityState = field(default_factory=IntegrityState)
    skill_profile: SkillProfile = field(default_factory=SkillProfile)
    difficulty_history: List[str] = field(default_factory=list)
    decision_history: List[Dict[str, Any]] = field(default_factory=list)
    agent_feedback: Dict[str, List[str]] = field(default_factory=dict)
    feedback_events: List[Dict[str, Any]] = field(default_factory=list)

    def mark_problem(self, problem: ProblemSpec) -> None:
        self.current_problem = problem
        self.difficulty = problem.difficulty
        self.topic = problem.topic
        self.difficulty_history.append(problem.difficulty)

    def add_submission(self, code: str, evaluation: Dict[str, Any]) -> SubmissionRecord:
        now = datetime.utcnow()
        diff_ratio = 1.0
        time_delta = 0.0
        if self.submissions:
            previous = self.submissions[-1]
            diff_ratio = SequenceMatcher(None, previous.code, code).ratio()
            time_delta = (now - previous.created_at).total_seconds()
        passed = evaluation.get("passed", 0)
        failed = evaluation.get("failed", 0)
        total_tests = evaluation.get("total_tests", passed + failed)
        status = evaluation.get("status", "unknown")
        record = SubmissionRecord(
            code=code,
            created_at=now,
            diff_ratio=diff_ratio,
            time_delta=time_delta,
            tests_passed=passed,
            tests_failed=failed,
            total_tests=total_tests,
            status=status,
        )
        self.submissions.append(record)
        return record

    def record_hint(self, level: str, text: str) -> None:
        self.hints.append(HintRecord(level=level, text=text, created_at=datetime.utcnow()))

    def record_decision(self, agent: str, decision: Dict[str, Any]) -> None:
        entry = {
            "agent": agent,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.decision_history.append(entry)

    def append_feedback(self, agent: str, note: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        self.agent_feedback.setdefault(agent, []).append(note)
        self.feedback_events.append({"agent": agent, "note": note, "timestamp": timestamp})

    def latest_submission(self) -> Optional[SubmissionRecord]:
        if not self.submissions:
            return None
        return self.submissions[-1]

    def as_summary(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "status": self.status,
            "difficulty": self.difficulty,
            "topic": self.topic,
            "submissions": len(self.submissions),
            "hints": len(self.hints),
            "integrity": self.integrity.as_dict(),
            "skill_profile": self.skill_profile.as_dict(),
        }
