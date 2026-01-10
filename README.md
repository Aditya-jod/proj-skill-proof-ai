# SkillProof AI

This project is an agentic AI system for learning, testing, hiring, and assessment. It uses a multi-agent architecture to autonomously make decisions instead of just responding to users.

## Architecture

- **Backend**: Python with FastAPI
- **Database**: SQLite with SQLAlchemy
- **Real-time**: WebSockets

## Running the Project

1.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the server:**
    ```bash
    uvicorn app.main:app --reload
    ```

4.  **Access the application:**
    -   **User Interface**: Open a browser to `http://localhost:8000/static/index.html`
    -   **Admin Dashboard**: Open another browser tab to `http://localhost:8000/static/dashboard.html`
    -   **API Docs**: `http://localhost:8000/docs`
