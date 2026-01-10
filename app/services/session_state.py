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
        if self.webcam_flags >= 2:
            self.severity = "warn"
        if self.webcam_flags >= 3:
            self.paused = True
            self.severity = "paused"
            return "pause"
        return "warn"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "focus_losses": self.focus_losses,
            "inactivity_flags": self.inactivity_flags,
            "webcam_flags": self.webcam_flags,
            "severity": self.severity,
            "paused": self.paused,
            "terminated": self.terminated,
        }


@dataclass
class SkillProfile:
    conceptual: float = 0.5
    implementation: float = 0.5
    reasoning: float = 0.5
    guessing: float = 0.0
    attempts: int = 0

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def apply(self, conceptual_delta: float, implementation_delta: float, reasoning_delta: float, guessing_delta: float) -> None:
        self.conceptual = self._clamp(self.conceptual + conceptual_delta)
        self.implementation = self._clamp(self.implementation + implementation_delta)
        self.reasoning = self._clamp(self.reasoning + reasoning_delta)
        self.guessing = self._clamp(self.guessing + guessing_delta)
        self.attempts += 1

    def as_dict(self) -> Dict[str, Any]:
        return {
            "conceptual": round(self.conceptual, 3),
            "implementation": round(self.implementation, 3),
            "reasoning": round(self.reasoning, 3),
            "guessing": round(self.guessing, 3),
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
