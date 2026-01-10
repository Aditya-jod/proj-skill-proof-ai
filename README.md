# SkillProof AI

SkillProof AI is a prototype agentic platform for technical assessments. Instead of a single chatbot, it orchestrates specialized agents to adapt challenges, analyze code, guard integrity, and provide hints in near real time. Frontend clients (candidate IDE and admin dashboard) talk to the backend over WebSockets while persistence happens in SQLite.

## Feature Highlights

- **Agent Orchestration** – `OrchestratorAgent` receives every event and dispatches to specialists (adaptation, learning diagnosis, integrity).
- **Adaptive Problems** – `AdaptationAgent` selects starter code based on difficulty/topic chosen during session setup.
- **Live Session Monitoring** – Admin dashboard streams focus events, submissions, and status changes via WebSockets.
- **Groq-Powered Intelligence** – `AIService` integrates the Groq `llama3-8b-8192` model for code analysis and hint generation.
- **Integrity Enforcement** – `IntegrityAgent` reacts to tab switches or other suspicious signals and pushes warnings.
- **SQLite Persistence** – Session metadata is stored via SQLAlchemy against `sqlite:///./skillproof.db`.

## Repository Layout

```
app/
  agents/              # Specialized agent implementations
  api/                 # FastAPI routers for REST endpoints
  crud/                # SQLAlchemy CRUD helpers
  db/                  # Engine/session setup and Base declaration
  models/              # ORM models (e.g., Session)
  schemas/             # Pydantic schemas for payload validation
  services/            # Shared services (Groq AI, session manager)
  websockets/          # Connection manager and message router
static/                # Frontend assets (landing page, session UI, dashboard)
templates/             # Server-rendered HTML entry points
data/                  # SQLite database file lives here once created
```

## Agents Overview

| Agent | Role |
| --- | --- |
| `AdaptationAgent` | Chooses a problem template to match selected difficulty/topic. |
| `LearningDiagnosisAgent` | Reviews submissions to infer misconceptions and update skill profile. |
| `IntegrityAgent` | Monitors integrity signals (focus loss etc.) and advises warnings. |
| `HintStrategyAgent` | (Scaffolded) Determines hint style/when to reveal guidance. |
| `EvaluationAgent` | (Scaffolded) Aggregates scores across correctness, time, hints. |
| `OrchestratorAgent` | Entry point that wires everything together per user session. |

## Prerequisites

- Python 3.12+
- A Groq API key (free tier available at [console.groq.com/keys](https://console.groq.com/keys)).

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
    Create `.env` (already gitignored) and place your Groq key:
    ```env
    GROQ_API_KEY="gsk_your_actual_key"
    ```

4. **Run migrations (optional)**
    SQLite tables are created automatically on first boot via SQLAlchemy metadata. Delete `data/skillproof.db` if you need a clean slate.

5. **Launch application**
    ```bash
    uvicorn app.main:app --reload
    ```

6. **Open clients**
    - Landing page: `http://localhost:8000/`
    - Candidate session IDE: `http://localhost:8000/session`
    - Admin dashboard: `http://localhost:8000/dashboard`
    - Interactive docs: `http://localhost:8000/docs`

## How It Works

1. **User configures session** – Difficulty/topic selection from landing page; WebSocket connection established.
2. **Orchestrator handles events** – On `session_start` it calls `AdaptationAgent` to assign starter code.
3. **Submissions analyzed** – `LearningDiagnosisAgent` passes code to `AIService`, which queries Groq for analysis/hints.
4. **Integrity monitoring** – Focus loss or suspicious events trigger `IntegrityAgent` actions broadcast to dashboard.
5. **Admin visibility** – Dashboard consumes broadcasted payloads to present status, flags, and timestamps live.

## Persistence Notes

- Database file lives at `./skillproof.db` (relative to repo root). Update `DATABASE_URL` in `app/config.py` if you relocate it.
- CRUD helpers in `app/crud/crud_session.py` demonstrate how to read/write sessions.
- `SessionLocal()` from `app/db/session.py` should be used with `try/finally` for connection cleanup.

## Extending the Platform

- **Hints** – Flesh out `HintStrategyAgent` to consult `AIService.generate_hint` and push results back over the socket.
- **Evaluation** – Implement grading logic in `EvaluationAgent` and trigger on session completion.
- **Authentication** – Add OAuth or JWT if you need multi-tenant security.
- **Problem Bank** – Replace mocked problems with a real content service or database table.

## Testing

- Manual end-to-end: run server, open `/session` in one tab and `/dashboard` in another.
- Add automated tests under `tests/` (not yet created) using `pytest` targeting agents and API endpoints.

## Troubleshooting

- **`GROQ_API_KEY missing`**: ensure `.env` is populated and shell reloaded.
- **WebSocket closes immediately**: check server logs for stack traces (missing imports, collectors).
- **Static assets 404**: confirm app started via `uvicorn app.main:app --reload` so templates/static routes resolve.

## Roadmap

- Integrate additional Groq models for code execution feedback.
- Add persistence for per-event logs to power historical dashboards.
- Build automated integrity heuristics (tab timing, copy/paste detection).
- Deploy to a managed FastAPI hosting platform (Render/Fly.io) with managed SQLite or Postgres upgrade.

---

SkillProof AI is currently a working prototype. Contributions and feature experiments are welcome—feel free to fork and iterate on the agents or UI flows.
