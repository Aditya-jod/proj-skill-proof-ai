# SkillProof AI

SkillProof AI is an agentic assessment platform that coordinates multiple autonomous services to adapt challenges, analyze learner code, defend assessment integrity, and surface transparent feedback in real time. The backend exposes FastAPI endpoints and WebSockets, while a lightweight frontend delivers the candidate and admin experiences.

## Feature Highlights

- **Persistent Accounts** – Email/password registration with PBKDF2 hashing, admin seeding on startup, and session-backed authentication.
- **Dynamic Problem Generation** – `ProblemRepository` requests fresh coding challenges from Google Gemini (JSON constraints enforced) with automatic fallback to the local catalog when the API is unavailable.
- **Agent Orchestration** – The orchestrator routes events through adaptation, evaluation, hinting, learning diagnosis, and integrity agents, each following a strict observe → decide → act → explain loop.
- **Real-Time Insights** – WebSocket streams deliver decision logs, integrity alerts, hints, and evaluation summaries to both the candidate IDE and admin dashboard.
- **Integrity Enforcement** – Focus loss, inactivity, webcam, and tab-switch signals escalate through warn → pause → terminate policies, keeping administrators informed.
- **SQLite/Postgres Ready** – SQLAlchemy models persist sessions, users, skill profiles, and agent feedback; `DATABASE_URL` can target any SQLAlchemy-compatible database.

## Technology Stack

- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2, Starlette sessions
- Google Gemini (google.generativeai) for hints, problem generation, and code analysis
- Vanilla JavaScript, Jinja2 templates, CSS modules for the UI
- WebSockets for live session streaming

## Autonomous Architecture

- **Message Bus Telemetry** – `MessageBus` publishes orchestration events so additional agents or analytics subscribers can react without tight coupling.
- **Skill Intelligence** – `SkillProfile` tracks debugging, logic, syntax, decomposition, and integrity confidence; updates persist at session close.
- **Feedback Ledger** – Agents append explanations to the feedback journal for auditability; items flush to the `agent_feedback` table.
- **Resilience** – Centralized `SkillProofError` handling ensures API and WebSocket clients receive structured diagnostics instead of crashes.

## Environment Variables

Configure these in `.env` (local) or your hosting provider:

| Variable | Description |
| --- | --- |
| `GOOGLE_API_KEY` | Required. Gemini API key used by `AIService` for hints, analysis, and problem generation. |
| `DATABASE_URL` | Optional. SQLAlchemy connection string (defaults to `sqlite:///./skillproof.db`). |
| `SESSION_SECRET_KEY` | Required. Random string for signing session cookies. |
| `ADMIN_EMAIL` | Required. Seeded admin account email. |
| `ADMIN_PASSWORD` | Required. Seeded admin password. |

## Setup

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
3. **Create `.env`** with the variables listed above.
4. **Launch FastAPI**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. **Visit the UI**
   - Landing page: http://localhost:8000/
   - Candidate IDE: http://localhost:8000/session
   - Admin dashboard: http://localhost:8000/dashboard
   - Interactive docs: http://localhost:8000/docs

## Deployment Notes

- Render or similar platforms should use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the start command.
- Remember to set all environment variables in the host dashboard; Gemini requests will fail without `GOOGLE_API_KEY`.
- SQLite works for demos, but move to managed Postgres by switching `DATABASE_URL` in production.

## Agents Overview

| Agent | Responsibilities |
| --- | --- |
| `AdaptationAgent` | Requests problems from Gemini (with JSON validation and caching) and escalates/remediates difficulty based on recent performance. |
| `LearningDiagnosisAgent` | Analyzes submissions for guessing vs mastery, updates the skill profile, and surfaces targeted feedback. |
| `HintStrategyAgent` | Chooses conceptual/strategic/implementation hints, enforces cooldowns, and calls Gemini for natural-language guidance. |
| `IntegrityAgent` | Monitors focus, inactivity, tab switches, and webcam alerts to enforce warn/pause/terminate policies. |
| `EvaluationAgent` | Executes unit tests against learner code, reports pass/fail counts, and aggregates scoring metadata. |
| `OrchestratorAgent` | Coordinates all other agents, records decisions, and emits structured payloads over WebSockets. |

## How It Works

1. User signs in or registers; the session cookie captures the user payload.
2. When a session starts, the orchestrator calls `AdaptationAgent`, which fetches (or falls back to cached/static) problems via `ProblemRepository`.
3. Learner submissions invoke `EvaluationAgent` and `LearningDiagnosisAgent`, which provide scoring and reasoning analysis.
4. Hint requests route through `HintStrategyAgent`, which may query Gemini for guidance.
5. Integrity events continuously update the dashboard and session state severity.

## File Structure

Full repository layout (excluding virtual environment, git metadata, and `__pycache__` directories):

```text
.
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── skillproof.db
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── adaptation_agent.py
│   │   ├── base_agent.py
│   │   ├── evaluation_agent.py
│   │   ├── hint_strategy_agent.py
│   │   ├── integrity_agent.py
│   │   ├── learning_diagnosis_agent.py
│   │   └── orchestrator_agent.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── admin.py
│   │       ├── auth.py
│   │       └── sessions.py
│   ├── core/
│   │   ├── decision.py
│   │   ├── errors.py
│   │   └── message_bus.py
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── crud_agent_feedback.py
│   │   ├── crud_session.py
│   │   ├── crud_skill_profile.py
│   │   └── crud_user.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent_feedback.py
│   │   ├── session.py
│   │   ├── skill_profile.py
│   │   └── user_account.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── feedback.py
│   │   ├── session.py
│   │   ├── skill_profile.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       ├── ai_service.py
│       ├── auth_service.py
│       ├── code_evaluator.py
│       ├── problem_repository.py
│       ├── session_manager.py
│       └── session_state.py
├── data/
│   └── problems.json
├── Documents/
│   └── ... (marketing copy, assets, etc.)
├── static/
│   ├── css/
│   │   ├── access.css
│   │   ├── app.css
│   │   ├── dashboard.css
│   │   ├── home.css
│   │   ├── main.css
│   │   └── styles.css
│   └── js/
│       ├── access.js
│       ├── admin-login.js
│       ├── auth.js
│       ├── dashboard.js
│       ├── footer.js
│       ├── main.js
│       ├── navbar.js
│       └── site.js
├── templates/
│   ├── about.html
│   ├── access.html
│   ├── admin_login.html
│   ├── dashboard.html
│   ├── features.html
│   ├── index.html
│   ├── platform.html
│   ├── session.html
│   └── use_cases.html
├── tmp/
│   └── (empty or transient files)
└── .venv/ (virtual environment, excluded from tree)
```

## Troubleshooting

- **Gemini errors** – Ensure `GOOGLE_API_KEY` is valid; the repository will fall back to `data/problems.json` if the API fails repeatedly.
- **Authentication issues** – Confirm admin credentials in environment variables and restart the app to trigger seeding.
- **Render deploy fails on `email_validator`** – `requirements.txt` includes the dependency; redeploy after pulling the latest changes.

## Roadmap

- Migrate from `google.generativeai` to the newer `google.genai` SDK per deprecation notice.
- Add automated testing for agent decision flows and API endpoints.
- Expand problem validation (static type checks, runtime guardrails) before releasing Gemini-generated challenges to users.

---

SkillProof AI remains an experiment in coordinated agentic assessments. Contributions and ideas to evolve the agents, UI, or deployment story are welcome.
