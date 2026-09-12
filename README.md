# Objection — research hiring workflow

## Run locally

Create a virtual environment, install the dependencies, then start the Streamlit app:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the local Streamlit URL shown in the terminal (normally http://localhost:8501). The app creates `objection.db` on first run and adds safe sample data.

## Login portal

The app has separate role-based demo accounts:

- Researcher: `researcher@lab.local` / `research123`
- HR: `hr@lab.local` / `hr123`

Researcher accounts manage projects, tasks, task chat, and candidate requests. HR accounts can access the HR board to approve/reject requests and record outreach. These local accounts are for development only; use your university SSO/OIDC provider for a production deployment.

The Streamlit app persists projects, task dependencies, conversations, candidate data, hiring requests, and outreach logs in SQLite.

## Included workflow

- Create research projects and pipeline tasks
- Make tasks depend on previous work and track completion
- Discuss a task with a professor, PhD researcher, and assistant
- Select a candidate and pass the request to the HR board
- Record HR outreach by email or WhatsApp without sending an external message

The candidate search and communications are deliberately simulated. A production deployment would connect these points to the institution's authorised student directory, HR system, and email/WhatsApp provider. The API deliberately logs outreach rather than sending a message externally.

Project descriptions can generate an editable starter task plan. Each task has a Start button, which moves it to **In progress** only after its dependencies are complete.

## OpenRouter AI task planner

The app can send a project description to an OpenRouter model and request a strict JSON task plan. It shows the plan for review before creating any task or dependency. Add this to `.streamlit/secrets.toml` locally, then restart Streamlit:

```toml
OPENROUTER_API_KEY = "your-openrouter-key"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
```

OpenRouter is cloud-hosted; it is not a local model runtime. To run the model entirely on your machine instead, use an Ollama integration (which does not require an API key). The planner detects whether the chosen model supports schema-enforced JSON; models such as `inclusionai/ling-3.0-flash-vl:free` use a JSON-only prompt with local validation instead.

## Ambiguous AI integration

Ambiguous provides bearer-token REST APIs for workspace resources, including tasks, plus MCP connectivity. This app has an opt-in task-sync client. Set `AMBIGUOUS_API_KEY` as an environment variable before starting Streamlit, or place it in `.streamlit/secrets.toml` locally:

```toml
AMBIGUOUS_API_KEY = "your-token"
```

Restart Streamlit afterward. The sidebar confirms configuration; selecting **Sync project tasks to Ambiguous** is the only action that sends project/task data to Ambiguous. Do not commit credentials. Before enabling automatic task generation with the Ambiguous Assistant, provide the API key-enabled Assistant endpoint schema from the workspace OpenAPI reference so the request body and response parsing can be implemented accurately.
