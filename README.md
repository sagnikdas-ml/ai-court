# Objection — research hiring workflow

## Run locally

Create a virtual environment, install the dependency, then start the Python service:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a modern browser. The service creates `objection.db` on first run and adds safe sample data.

The Python service exposes a REST API and persists projects, task dependencies, conversations, candidate data, hiring requests, and outreach logs in SQLite.

## Included workflow

- Create research projects and pipeline tasks
- Make tasks depend on previous work and track completion
- Discuss a task with a professor, PhD researcher, and assistant
- Select a candidate and pass the request to the HR board
- Record HR outreach by email or WhatsApp without sending an external message

The candidate search and communications are deliberately simulated. A production deployment would connect these points to the institution's authorised student directory, HR system, and email/WhatsApp provider. The API deliberately logs outreach rather than sending a message externally.

## API overview

- `GET, POST /api/projects`
- `GET, POST /api/projects/<project_id>/tasks`
- `PATCH, DELETE /api/tasks/<task_id>`
- `GET, POST /api/tasks/<task_id>/messages`
- `POST /api/tasks/<task_id>/candidates/search`
- `POST /api/tasks/<task_id>/hiring-requests`
- `GET /api/hiring-requests`
- `PATCH /api/hiring-requests/<request_id>`
- `POST /api/hiring-requests/<request_id>/outreach`
