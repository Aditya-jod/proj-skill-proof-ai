# SkillProof AI

SkillProof AI is a prototype agentic platform for technical assessments. Instead of a single chatbot, it orchestrates specialized agents to adapt challenges, analyze code, guard integrity, and provide hints in near real time. Frontend clients (candidate IDE and admin dashboard) talk to the backend over WebSockets while persistence happens in SQLite.

## Feature Highlights

- **Agent Orchestration** – `OrchestratorAgent` now routes events through dedicated handlers, dispatching cleanly to adaptation, learning diagnosis, evaluation, integrity, and hint specialists.
- **Adaptive Problems** – `AdaptationAgent` selects starter code based on difficulty/topic chosen during session setup.
- **Live Session Monitoring** – Admin dashboard streams focus events, submissions, and status changes via WebSockets.
- **Gemini-Powered Intelligence** – `AIService` integrates Google AI Studio (Gemini 1.5 Pro) for analysis and adaptive hinting.
- **Integrity Enforcement** – `IntegrityAgent` reacts to tab switches or other suspicious signals and pushes warnings.
- **SQLite Persistence** – Session metadata is stored via SQLAlchemy against `sqlite:///./skillproof.db`.
- **Evidence-Based Scoring** – `EvaluationAgent` executes reference tests from the problem bank and applies penalties for hints, delay, and integrity states.
- **Reasoning Diagnostics** – `LearningDiagnosisAgent` tracks code deltas, attempt cadence, and outcomes to classify guessing vs. mastery and maintain a skill profile.
- **Guarded Hinting** – `HintStrategyAgent` throttles hint frequency, escalates through conceptual→directional→code granularity, and blocks when limit reached.

## Autonomous Architecture

- **Decision Lifecycle** – Every concrete agent now follows an `observe → decide → act → explain` loop defined in `BaseAgent`. The orchestrator captures each `AgentDecision`, storing rationale, policy, and metadata inside the session state for auditing.
- **Message Bus Telemetry** – `MessageBus` provides lightweight publish/subscribe transport. The orchestrator emits inbound events and agent decisions so future agents or analytics subscribers can react without tight coupling.
- **Persistent Skill Intelligence** – `SkillProfile` objects track debugging, logic, syntax, decomposition, and integrity confidence scores. Adjustments are marked dirty and persisted to the new `skill_profiles` table at session close, allowing longitudinal growth across attempts.
- **Feedback Ledger** – Agent explanations and governance notes append to `agent_feedback`. Entries flush to the `agent_feedback` table (linked to `sessions.id`) and surface in both the candidate IDE and admin dashboard.
- **Decision Log Surface** – WebSocket payloads now include rolling decision history, most recent submission metrics, and agent feedback so UIs can render transparency panels without additional queries.
- **WebSocket Message Pipeline** – Session retrieval and broadcast payload construction live in dedicated helpers, leaving the main socket handler focused on orchestration and error reporting.

## Governance & Policies

- **Hint Controls** – `HintStrategyAgent` enforces a three-hint ceiling, 45-second cooldown between hints, and escalates through conceptual/directional/code tiers before repeating, blocking if inventory is exhausted.
- **Integrity Escalation** – `IntegrityAgent` converts focus losses, inactivity, webcam alerts, and tab switches into a policy ladder: warn → pause → terminate. Severity updates set `SessionState.status`, which drives frontend messaging and dashboard flags.
- **Adaptive Progression** – `AdaptationAgent` promotes to harder problems after passes, remediates after repeated failures, and pauses the session if no suitable challenge is found (triggering administrator review).
- **Evaluation Scoring** – `EvaluationAgent` records penalties for hint usage, elapsed time, and integrity severity; only fully passing submissions with sufficient score mark test mode sessions as completed.
- **Decision Explainability** – Each agent returns structured explanations that the orchestrator logs and the UI displays. This forms the basis for compliance/audit trails and ensures users receive rationale for automated actions.
- **Resilient Error Handling** – Custom `SkillProofError` hierarchy feeds centralized logging, FastAPI exception hooks, and WebSocket safeguards. Agents fail gracefully with `agent_error` payloads, the orchestrator records structured failures, and WebSocket helpers broadcast trimmed diagnostics for administrators.

## Repository Layout

```
app/
  agents/              # Specialized agent implementations
  api/                 # FastAPI routers for REST endpoints
  crud/                # SQLAlchemy CRUD helpers
  db/                  # Engine/session setup and Base declaration
  models/              # ORM models (e.g., Session)
  schemas/             # Pydantic schemas for payload validation
    services/            # Shared services (Gemini AI client, session manager)
  websockets/          # Connection manager and message router
static/                # Frontend assets (landing page, session UI, dashboard)
templates/             # Server-rendered HTML entry points
data/                  # SQLite database file lives here once created
                                            # plus problems.json source of adaptive challenges
```

## Agents Overview

| Agent | Role |
| --- | --- |
| `AdaptationAgent` | Pulls problems from `data/problems.json`, escalates or remediates difficulty after each submission. |
| `LearningDiagnosisAgent` | Scores reasoning, detects guessing via diff/time heuristics, and updates the skill profile. |
| `HintStrategyAgent` | Uses recent performance to choose conceptual/directional/code hints while enforcing cooldown and caps. |
| `IntegrityAgent` | Tracks focus, inactivity, and webcam alerts; escalates from warn → pause → terminate. |
| `EvaluationAgent` | Executes canonical tests, applies penalties, and emits holistic scores/grades. |
| `OrchestratorAgent` | State-aware coordinator that bundles evaluation, diagnosis, adaptation, and broadcasts. |

## Prerequisites

- Python 3.12+
- A Google AI Studio API key (create one at [ai.google.dev](https://ai.google.dev/)).

## Setup & Execution

1. **Create virtual environment**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure environment**
    Create `.env` (already gitignored) and add your Google AI Studio key:
    ```env
    GOOGLE_API_KEY="AIza_sy_your_actual_key"
    ```

4. **Seed challenge catalog**
    The platform reads problems from `data/problems.json`. Update or extend this file to introduce new challenges, hints, and reference tests. Each entry supports:
    - `starter_code`: baseline snippet shown to the candidate
    - `hints`: conceptual/directional/code guidance
    - `tests`: argument/expected pairs for the evaluator to execute

5. **Run migrations (optional)**
    SQLite tables are created automatically on first boot via SQLAlchemy metadata. Delete `data/skillproof.db` if you need a clean slate or to pick up new columns (e.g., when upgrading from earlier scaffolds).

6. **Launch application**
    ```bash
    uvicorn app.main:app --reload
    ```

7. **Open clients**
    - Landing page: `http://localhost:8000/`
    - Candidate session IDE: `http://localhost:8000/session`
    - Admin dashboard: `http://localhost:8000/dashboard`
    - Interactive docs: `http://localhost:8000/docs`

## How It Works

1. **User configures session** – Difficulty/topic selection from landing page; WebSocket connection established.
2. **Orchestrator handles events** – On `session_start` it calls `AdaptationAgent` to assign starter code.
3. **Submissions analyzed** – `LearningDiagnosisAgent` and `HintStrategyAgent` call `AIService`, which queries Google Gemini for diagnostics and adaptive hints.
4. **Integrity monitoring** – Focus loss or suspicious events trigger `IntegrityAgent` actions broadcast to dashboard.
5. **Admin visibility** – Dashboard consumes broadcasted payloads to present status, flags, and timestamps live.

## Persistence Notes

- Database file lives at `./skillproof.db` (relative to repo root). Update `DATABASE_URL` in `app/config.py` if you relocate it.
- CRUD helpers in `app/crud/crud_session.py` demonstrate how to read/write sessions.
- `SessionLocal()` from `app/db/session.py` should be used with `try/finally` for connection cleanup.
- Session `end_time` is captured when the websocket disconnects or a `session_end` event fires; drop the database to refresh schema when new columns are introduced.

## Extending the Platform

- **Hints** – Flesh out `HintStrategyAgent` to consult `AIService.generate_hint` and push results back over the socket.
- **Evaluation** – Implement grading logic in `EvaluationAgent` and trigger on session completion.
- **Authentication** – Add OAuth or JWT if you need multi-tenant security.
- **Problem Bank** – Replace mocked problems with a real content service or database table.

## Testing

- Manual end-to-end: run server, open `/session` in one tab and `/dashboard` in another.
- Add automated tests under `tests/` (not yet created) using `pytest` targeting agents and API endpoints.

## Troubleshooting

- **`GOOGLE_API_KEY missing`**: ensure `.env` is populated and shell reloaded.
- **WebSocket closes immediately**: check server logs for stack traces (missing imports, collectors).
- **Static assets 404**: confirm app started via `uvicorn app.main:app --reload` so templates/static routes resolve.

## Roadmap

- Deepen Gemini usage for richer code execution feedback.
- Add persistence for per-event logs to power historical dashboards.
- Build automated integrity heuristics (tab timing, copy/paste detection).
- Deploy to a managed FastAPI hosting platform (Render/Fly.io) with managed SQLite or Postgres upgrade.

## Data Files

- `data/problems.json` – Master catalog for adaptive exercises; update difficulties, hints, and regression tests here.
- `data/skillproof.db` – SQLite datastore (auto-generated). Delete this file if you change ORM models to let SQLAlchemy recreate the schema.

---

SkillProof AI is currently a working prototype. Contributions and feature experiments are welcome—feel free to fork and iterate on the agents or UI flows.
