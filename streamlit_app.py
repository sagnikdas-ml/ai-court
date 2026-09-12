"""Objection research operations — Streamlit interface.

Run: streamlit run streamlit_app.py
"""
from __future__ import annotations

import sqlite3
import hashlib
import hmac
import os
import re
import secrets
import tomllib
from contextlib import closing
from pathlib import Path

import streamlit as st

from ambiguous_client import AmbiguousClient
from openrouter_client import OpenRouterClient

DATABASE = Path(__file__).resolve().parent / "objection.db"

st.set_page_config(page_title="Objection · Research operations", page_icon=":material/account_tree:", layout="wide")
def initialise_database() -> None:
    """Create the data model used by Streamlit without requiring Flask."""
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'upcoming', is_complete INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS task_dependencies (task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, depends_on_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, PRIMARY KEY(task_id, depends_on_id));
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, author TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS chat_task_suggestions (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, programme TEXT NOT NULL, experience TEXT NOT NULL, skills TEXT NOT NULL, availability_hours INTEGER NOT NULL, email TEXT NOT NULL, whatsapp TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS hiring_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, candidate_id INTEGER NOT NULL REFERENCES candidates(id), requested_by TEXT NOT NULL DEFAULT 'Arjun Shah', status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(task_id, candidate_id));
            CREATE TABLE IF NOT EXISTS outreach_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, hiring_request_id INTEGER NOT NULL REFERENCES hiring_requests(id) ON DELETE CASCADE, channel TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL CHECK(role IN ('researcher', 'hr')), password_salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """
        )
        if connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            connection.execute("INSERT INTO projects(name,description) VALUES (?,?)", ("Vision benchmark evaluation", "Prepare, evaluate, and report on the new vision benchmark with a student assistant."))
        if connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 0:
            connection.executemany("INSERT INTO candidates(name,programme,experience,skills,availability_hours,email,whatsapp) VALUES (?,?,?,?,?,?,?)", [
                ("Mira Patel", "MSc Computer Science", "Computer-vision lab project", "Python, PyTorch, OpenCV", 10, "mira.patel@example.edu", "+49 151 000001"),
                ("Leon Fischer", "MSc Data Science", "PyTorch and MLOps", "Python, PyTorch, MLflow", 8, "leon.fischer@example.edu", "+49 151 000002"),
                ("Sofia Romano", "MSc Robotics", "Image segmentation", "Python, CV, ROS", 12, "sofia.romano@example.edu", "+49 151 000003"),
            ])
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            for name, email, role, password in [
                ("Arjun Shah", "researcher@lab.local", "researcher", "research123"),
                ("Maya Hoffmann", "hr@lab.local", "hr", "hr123"),
            ]:
                salt = secrets.token_hex(16)
                digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
                connection.execute("INSERT INTO users(name,email,role,password_salt,password_hash) VALUES(?,?,?,?,?)", (name, email, role, salt, digest))
        connection.commit()


initialise_database()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with closing(connect()) as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def execute(sql: str, params: tuple = ()) -> int:
    with closing(connect()) as connection:
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.lastrowid


def authenticate(email: str, password: str) -> dict | None:
    records = query_all("SELECT * FROM users WHERE email=?", (email.strip().lower(),))
    if not records:
        return None
    user = records[0]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), user["password_salt"].encode(), 200_000).hex()
    return user if hmac.compare_digest(digest, user["password_hash"]) else None


def projects() -> list[dict]:
    return query_all("SELECT p.*, COUNT(t.id) AS task_count FROM projects p LEFT JOIN tasks t ON t.project_id=p.id GROUP BY p.id ORDER BY p.id")


def tasks(project_id: int) -> list[dict]:
    records = query_all("SELECT * FROM tasks WHERE project_id=? ORDER BY id", (project_id,))
    for task in records:
        task["is_complete"] = bool(task["is_complete"])
        task["dependencies"] = [row["depends_on_id"] for row in query_all("SELECT depends_on_id FROM task_dependencies WHERE task_id=?", (task["id"],))]
    return records


def messages(task_id: int) -> list[dict]:
    return query_all("SELECT * FROM messages WHERE task_id=? ORDER BY id", (task_id,))


def inferred_tasks(description: str) -> list[tuple[str, str]]:
    """Small transparent planner; replace with an approved LLM/service later."""
    text = description.lower()
    suggestions = [("Clarify scope and success criteria", "Confirm the deliverable, quality bar, and owner.")]
    if any(word in text for word in ("data", "dataset", "collection", "annotation")):
        suggestions += [("Collect and validate data", "Gather source material and verify completeness."), ("Prepare data documentation", "Record provenance, schema, and quality checks.")]
    if any(word in text for word in ("hire", "student", "hiwi", "assistant", "candidate")):
        suggestions.append(("Hire student assistant", "Find, approve, and onboard a suitable candidate."))
    if any(word in text for word in ("model", "pipeline", "evaluation", "benchmark", "python")):
        suggestions += [("Implement the working pipeline", "Build the agreed implementation and test the happy path."), ("Evaluate and report results", "Run the work, assess outcomes, and share findings.")]
    if len(suggestions) == 1:
        suggestions += [("Plan the implementation", "Break the work into deliverable milestones."), ("Execute and review", "Complete the work and review it with the supervisor.")]
    return suggestions


def task_suggestion_from_chat(message: str) -> dict | None:
    """Turn an actionable chat message into a small, reviewable task proposal."""
    text = message.strip()
    if not text:
        return None
    direct_match = re.match(r"^(?:add|create)\s+(?:a\s+)?task\s*:\s*(.+)$", text, re.IGNORECASE)
    if direct_match:
        title = direct_match.group(1).strip().rstrip(".")
        return {"title": title[:120], "description": f"Created from the task conversation: {text}", "direct": True}

    normalized = text.lower()
    suggestions = [
        (("dataset", "data collection", "collect data"), "Collect and validate dataset", "Gather the required data, check quality, and document provenance."),
        (("preprocess", "clean data", "annotation", "annotate"), "Preprocess and annotate data", "Prepare a reproducible dataset with documented quality checks."),
        (("train", "training", "action policy", "model"), "Train the action policy", "Train and validate the agreed model or policy."),
        (("evaluate", "benchmark", "metrics", "generalization"), "Evaluate and report results", "Define metrics, run the evaluation, and share the findings."),
        (("ros", "simulator", "mujoco", "isaac"), "Run the system in a simulator", "Integrate the work with the simulator or robot controller and test it safely."),
        (("candidate", "hiwi", "hire", "student assistant"), "Hire student assistant", "Find a suitable candidate and submit the selected person to HR."),
    ]
    for keywords, title, description in suggestions:
        if any(keyword in normalized for keyword in keywords):
            return {"title": title, "description": description, "direct": False}
    return None


def ready(task: dict, task_map: dict[int, dict]) -> bool:
    return all(task_map[dependency]["is_complete"] for dependency in task["dependencies"] if dependency in task_map)


def set_task_status(task_id: int, status: str, completed: bool = False) -> None:
    execute("UPDATE tasks SET status=?, is_complete=? WHERE id=?", (status, int(completed), task_id))


def select_task(task_id: int) -> None:
    st.session_state.selected_task_id = task_id
    st.session_state.view = "Task workspace"


def ambiguous_key() -> str | None:
    """Read the key from Streamlit secrets first, then a local environment variable."""
    try:
        return st.secrets.get("AMBIGUOUS_API_KEY") or os.getenv("AMBIGUOUS_API_KEY")
    except FileNotFoundError:
        return os.getenv("AMBIGUOUS_API_KEY")


def openrouter_setting(name: str, default: str | None = None) -> str | None:
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        configured = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
        if configured.get(name):
            return configured[name]
    try:
        return st.secrets.get(name) or os.getenv(name, default)
    except FileNotFoundError:
        return os.getenv(name, default)


for key, value in {"view": "Project board", "selected_task_id": None, "selected_project_id": None, "user": None, "ai_task_plan": None}.items():
    st.session_state.setdefault(key, value)

if not st.session_state.user:
    st.title("Objection")
    st.subheader("Research operations workspace")
    st.write("Sign in to manage research work or review candidate outreach.")
    login, info = st.columns([2, 1])
    with login:
        with st.form("login"):
            email = st.text_input("Email", placeholder="researcher@lab.local")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", icon=":material/login:")
            if submitted:
                user = authenticate(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")
    with info:
        with st.container(border=True):
            st.subheader("Demo accounts")
            st.markdown("**Researcher**\n\n`researcher@lab.local`\n\n`research123`")
            st.markdown("**HR**\n\n`hr@lab.local`\n\n`hr123`")
            st.caption("Use an identity provider such as your university SSO before production deployment.")
    st.stop()

available_projects = projects()
if not available_projects:
    st.error("No project is available. Create one in the sidebar.")
    st.stop()
if st.session_state.selected_project_id not in {project["id"] for project in available_projects}:
    st.session_state.selected_project_id = available_projects[0]["id"]

with st.sidebar:
    st.title("Objection")
    st.caption(f"Signed in as **{st.session_state.user['name']}** · {st.session_state.user['role'].upper()}")
    if st.button("Sign out", icon=":material/logout:", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.divider()
    client = AmbiguousClient(ambiguous_key())
    openrouter = OpenRouterClient(openrouter_setting("OPENROUTER_API_KEY"), openrouter_setting("OPENROUTER_MODEL"))
    st.subheader("Ambiguous AI")
    if client.configured:
        st.success("Connected configuration found", icon=":material/check_circle:")
        st.caption("Sync is always manual; no tasks or messages are sent automatically.")
    else:
        st.info("Not configured", icon=":material/key:")
        st.caption("Add an API key to enable task sync.")
    st.subheader("OpenRouter planner")
    if openrouter.configured:
        st.success(f"Ready · {openrouter.model}", icon=":material/auto_awesome:")
    else:
        st.info("Not configured", icon=":material/key:")
    views = ["Project board", "Task workspace"] + (["HR board"] if st.session_state.user["role"] == "hr" else [])
    if st.session_state.view not in views:
        st.session_state.view = "Project board"
    st.session_state.view = st.segmented_control(
        "Workspace",
        views,
        key="navigation",
        default=st.session_state.view,
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Projects")
    names = {project["name"]: project["id"] for project in available_projects}
    selected_name = next(name for name, identifier in names.items() if identifier == st.session_state.selected_project_id)
    choice = st.selectbox("Active project", list(names), index=list(names).index(selected_name), key="project_picker")
    st.session_state.selected_project_id = names[choice]
    with st.expander("Create project", icon=":material/add:"):
        with st.form("new_project", clear_on_submit=True):
            name = st.text_input("Project name")
            description = st.text_area("Project description", placeholder="Describe the research outcome and constraints.")
            if st.form_submit_button("Create project", type="primary", icon=":material/add:"):
                if not name.strip():
                    st.error("A project name is required.")
                else:
                    st.session_state.selected_project_id = execute("INSERT INTO projects(name, description) VALUES (?, ?)", (name.strip(), description.strip()))
                    st.success("Project created.")
                    st.rerun()

project_id = st.session_state.selected_project_id
project = next(item for item in projects() if item["id"] == project_id)
project_tasks = tasks(project_id)
task_by_id = {task["id"]: task for task in project_tasks}


def project_board() -> None:
    st.title(project["name"])
    st.caption(project["description"] or "Add a project description to generate an initial task plan.")
    total = len(project_tasks)
    completed = sum(task["is_complete"] for task in project_tasks)
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Tasks complete", f"{completed}/{total}", border=True)
    metric_b.metric("In progress", sum(task["status"] == "active" for task in project_tasks), border=True)
    metric_c.metric("Waiting on dependencies", sum(task["status"] == "blocked" for task in project_tasks), border=True)
    st.progress(completed / total if total else 0, text=f"{completed} of {total} tasks complete")

    with st.expander("Generate tasks from this project description", expanded=not project_tasks, icon=":material/auto_awesome:"):
        st.write("This creates a transparent, editable starter plan based on the project description.")
        suggestions = inferred_tasks(project["description"])
        st.dataframe([{"Suggested task": title, "Why it belongs": detail} for title, detail in suggestions], hide_index=True)
        if st.button("Add suggested tasks", type="primary", icon=":material/add_task:"):
            existing = {task["title"].lower() for task in project_tasks}
            for title, detail in suggestions:
                if title.lower() not in existing:
                    execute("INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)", (project_id, title, detail, "upcoming"))
            st.success("Suggested tasks added. Set dependencies below when needed.")
            st.rerun()

    with st.expander("Generate an AI task plan with OpenRouter", icon=":material/psychology:"):
        st.caption("Your project description will be sent to the selected OpenRouter model. The resulting plan is a preview: no tasks are created until you confirm it.")
        if not openrouter.configured:
            st.info("Add OPENROUTER_API_KEY to .streamlit/secrets.toml, then restart Streamlit.")
        elif st.button("Draft task plan", type="primary", icon=":material/auto_awesome:"):
            if not project["description"].strip():
                st.error("Add a project description before generating a plan.")
            else:
                try:
                    with st.spinner("Generating a reviewable task plan…"):
                        st.session_state.ai_task_plan = openrouter.task_plan(project["description"])
                except Exception as error:
                    st.error(f"OpenRouter planning failed: {error}")
        plan = st.session_state.get("ai_task_plan")
        if plan:
            st.dataframe(
                [{"#": index + 1, "Task": item["title"], "Description": item["description"], "Depends on": ", ".join(str(dep + 1) for dep in item["depends_on"]) or "—"} for index, item in enumerate(plan)],
                hide_index=True,
            )
            if st.button("Create reviewed AI tasks", type="primary", icon=":material/add_task:"):
                created_ids: list[int] = []
                for item in plan:
                    status = "blocked" if item["depends_on"] else "upcoming"
                    created_ids.append(execute("INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)", (project_id, item["title"], item["description"], status)))
                for task_id, item in zip(created_ids, plan):
                    for dependency_index in item["depends_on"]:
                        if 0 <= dependency_index < len(created_ids):
                            execute("INSERT INTO task_dependencies(task_id,depends_on_id) VALUES(?,?)", (task_id, created_ids[dependency_index]))
                st.session_state.ai_task_plan = None
                st.success("AI-proposed tasks were created.")
                st.rerun()

    if client.configured:
        with st.expander("Sync project tasks to Ambiguous", icon=":material/sync:"):
            st.caption("Creates a corresponding task in your Ambiguous workspace for each selected local task. This will write project details to Ambiguous only when you press the button.")
            eligible = [task for task in project_tasks if task["status"] != "done"]
            selection = st.multiselect("Tasks to sync", [task["title"] for task in eligible], default=[task["title"] for task in eligible])
            if st.button("Sync selected tasks", type="primary", icon=":material/cloud_upload:"):
                try:
                    for task in eligible:
                        if task["title"] in selection:
                            client.create_task(task["title"], task["description"], "in_progress" if task["status"] == "active" else "todo")
                    st.success(f"Synced {len(selection)} task(s) to Ambiguous.")
                except Exception as error:
                    st.error(f"Ambiguous sync failed: {error}")

    with st.expander("Add a task", icon=":material/add:"):
        with st.form("add_task", clear_on_submit=True):
            title = st.text_input("Task name")
            description = st.text_area("Task description")
            dependency_options = {f"{task['id']} · {task['title']}": task["id"] for task in project_tasks}
            dependencies = st.multiselect("Depends on", list(dependency_options))
            if st.form_submit_button("Add task", type="primary"):
                if not title.strip():
                    st.error("A task name is required.")
                else:
                    status = "blocked" if dependencies else "upcoming"
                    task_id = execute("INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)", (project_id, title.strip(), description.strip(), status))
                    for dependency in dependencies:
                        execute("INSERT INTO task_dependencies(task_id,depends_on_id) VALUES(?,?)", (task_id, dependency_options[dependency]))
                    st.rerun()

    st.subheader("Pipeline")
    columns = [("upcoming", "Ready to start"), ("active", "In progress"), ("blocked", "Waiting on"), ("done", "Complete")]
    board_columns = st.columns(4)
    for column, (status, label) in zip(board_columns, columns):
        with column:
            st.markdown(f"**{label}**")
            in_column = [task for task in project_tasks if task["status"] == status]
            for task in in_column:
                with st.container(border=True):
                    st.markdown(f"**{task['title']}**")
                    st.caption(task["description"] or "No description yet")
                    if task["dependencies"]:
                        depends = ", ".join(task_by_id[item]["title"] for item in task["dependencies"])
                        st.caption(f":material/account_tree: Depends on {depends}")
                    action_left, action_right = st.columns(2)
                    with action_left:
                        st.button("Open", key=f"open_{task['id']}", on_click=select_task, args=(task["id"],), use_container_width=True)
                    with action_right:
                        if not task["is_complete"] and task["status"] != "active":
                            if st.button("Start", key=f"start_{task['id']}", type="primary", icon=":material/play_arrow:", use_container_width=True):
                                if ready(task, task_by_id):
                                    set_task_status(task["id"], "active")
                                    st.rerun()
                                else:
                                    st.warning("Complete the dependencies before starting this task.")
                        elif task["status"] == "active":
                            if st.button("Mark complete", key=f"done_{task['id']}", icon=":material/check_circle:", use_container_width=True):
                                set_task_status(task["id"], "done", completed=True)
                                for candidate in project_tasks:
                                    if candidate["status"] == "blocked" and ready(candidate, task_by_id):
                                        set_task_status(candidate["id"], "upcoming")
                                st.rerun()
                        else:
                            st.badge("Complete", color="green")
            if not in_column:
                st.caption("No tasks")


def task_workspace() -> None:
    if not project_tasks:
        st.info("Add or generate a task first.")
        return
    options = {f"{task['title']} · {task['status'].replace('_', ' ')}": task["id"] for task in project_tasks}
    current = st.session_state.selected_task_id if st.session_state.selected_task_id in task_by_id else project_tasks[0]["id"]
    label = next(name for name, identifier in options.items() if identifier == current)
    selected_label = st.selectbox("Task", list(options), index=list(options).index(label))
    task = task_by_id[options[selected_label]]
    st.title(task["title"])
    st.caption(task["description"])
    if task["status"] != "active" and not task["is_complete"]:
        if st.button("Move to in progress", type="primary", icon=":material/play_arrow:"):
            if ready(task, task_by_id):
                set_task_status(task["id"], "active")
                st.rerun()
            else:
                st.error("This task is waiting on an unfinished dependency.")

    chat_col, detail_col = st.columns([2, 1])
    with chat_col:
        with st.container(border=True):
            st.subheader("Task conversation")
            st.caption("Type `add task: prepare the simulation test plan` to add a task now. Other task-like messages become suggestions for you to review.")
            for message in messages(task["id"]):
                role = "assistant" if message["author"] in {"agent", "hr"} else "user"
                avatar = ":material/smart_toy:" if message["author"] == "agent" else ":material/person:"
                with st.chat_message(role, avatar=avatar):
                    st.caption(message["author"].title())
                    st.write(message["body"])

            relevant_suggestions = query_all(
                "SELECT * FROM chat_task_suggestions WHERE task_id=? ORDER BY id", (task["id"],)
            )
            if relevant_suggestions:
                st.caption("Suggested from this conversation")
            for suggestion in relevant_suggestions:
                with st.container(border=True):
                    st.markdown(f"**{suggestion['title']}**")
                    st.caption(suggestion["description"])
                    create_col, dismiss_col = st.columns(2)
                    if create_col.button("Create task", key=f"create_chat_task_{suggestion['id']}", type="primary", icon=":material/add_task:", use_container_width=True):
                        execute(
                            "INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)",
                            (project_id, suggestion["title"], suggestion["description"], "upcoming"),
                        )
                        execute(
                            "INSERT INTO messages(task_id,author,body) VALUES(?,?,?)",
                            (task["id"], "agent", f"I added **{suggestion['title']}** to the project pipeline as ready to start."),
                        )
                        execute("DELETE FROM chat_task_suggestions WHERE id=?", (suggestion["id"],))
                        st.rerun()
                    if dismiss_col.button("Dismiss", key=f"dismiss_chat_task_{suggestion['id']}", use_container_width=True):
                        execute("DELETE FROM chat_task_suggestions WHERE id=?", (suggestion["id"],))
                        st.rerun()

            prompt = st.chat_input("Message the team or ask the agent", key=f"chat_{task['id']}")
            if prompt:
                execute("INSERT INTO messages(task_id,author,body) VALUES(?,?,?)", (task["id"], "phd", prompt))
                suggestion = task_suggestion_from_chat(prompt)
                if suggestion and suggestion["direct"]:
                    execute(
                        "INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)",
                        (project_id, suggestion["title"], suggestion["description"], "upcoming"),
                    )
                    reply = f"I added **{suggestion['title']}** to the project pipeline as ready to start."
                elif suggestion:
                    execute(
                        "INSERT INTO chat_task_suggestions(task_id,title,description) VALUES(?,?,?)",
                        (task["id"], suggestion["title"], suggestion["description"]),
                    )
                    reply = "I found a possible follow-up task. Review the suggestion above and create it only if it fits the project plan."
                elif any(word in prompt.lower() for word in ("candidate", "hiwi", "hire", "assistant")):
                    reply = "I found suitable candidates below. Choose one to create an HR request."
                else:
                    reply = "I noted that. I can help clarify the task, suggest a follow-up task, search for candidates, or prepare the HR request."
                execute("INSERT INTO messages(task_id,author,body) VALUES(?,?,?)", (task["id"], "agent", reply))
                st.rerun()
    with detail_col:
        with st.container(border=True):
            st.subheader("Candidate search")
            st.caption("Use this when the task needs a student assistant.")
            if st.button("Find candidates", icon=":material/search:"):
                st.session_state.show_candidates = True
            if st.session_state.get("show_candidates"):
                candidates = query_all("SELECT * FROM candidates ORDER BY availability_hours DESC LIMIT 5")
                for candidate in candidates:
                    st.markdown(f"**{candidate['name']}**")
                    st.caption(f"{candidate['programme']} · {candidate['experience']}")
                    st.caption(f"{candidate['availability_hours']} h/week · {candidate['skills']}")
                    if st.button("Ask HR to proceed", key=f"hire_{task['id']}_{candidate['id']}", type="primary", use_container_width=True):
                        try:
                            execute("INSERT INTO hiring_requests(task_id,candidate_id) VALUES(?,?)", (task["id"], candidate["id"]))
                            execute("INSERT INTO messages(task_id,author,body) VALUES(?,?,?)", (task["id"], "agent", f"I sent {candidate['name']} to HR for review and outreach."))
                            st.success("Request sent to HR.")
                        except sqlite3.IntegrityError:
                            st.info("This candidate already has a request for this task.")


def hr_board() -> None:
    if st.session_state.user["role"] != "hr":
        st.error("The HR board is restricted to HR accounts.")
        st.stop()
    st.title("HR board")
    st.caption("Review approved hiring requests and record candidate outreach.")
    requests = query_all("""SELECT h.*, c.name, c.programme, c.experience, c.email, c.whatsapp, t.title AS task_title
                            FROM hiring_requests h JOIN candidates c ON c.id=h.candidate_id JOIN tasks t ON t.id=h.task_id
                            ORDER BY h.created_at DESC""")
    if not requests:
        st.info("No hiring requests yet. Choose a candidate from a task workspace.")
        return
    for request_item in requests:
        with st.container(border=True):
            left, right = st.columns([3, 2])
            with left:
                st.subheader(request_item["name"])
                st.write(f"**Task:** {request_item['task_title']}")
                st.caption(f"{request_item['programme']} · {request_item['experience']}")
                st.badge(request_item["status"].replace("_", " ").title(), color="green" if request_item["status"] == "contacted" else "orange")
            with right:
                if request_item["status"] == "pending":
                    approve, reject = st.columns(2)
                    if approve.button("Approve", key=f"approve_{request_item['id']}", type="primary"):
                        execute("UPDATE hiring_requests SET status='approved' WHERE id=?", (request_item["id"],))
                        st.rerun()
                    if reject.button("Reject", key=f"reject_{request_item['id']}"):
                        execute("UPDATE hiring_requests SET status='rejected' WHERE id=?", (request_item["id"],))
                        st.rerun()
                elif request_item["status"] == "approved":
                    channel = st.segmented_control("Outreach channel", ["Email", "WhatsApp"], key=f"channel_{request_item['id']}", default="Email")
                    target = request_item["email"] if channel == "Email" else request_item["whatsapp"]
                    with st.form(f"outreach_{request_item['id']}"):
                        text = st.text_area("Outreach draft", value=f"Hello {request_item['name']},\n\nWe would like to discuss a student-assistant role supporting {request_item['task_title']}. Are you available for a short conversation this week?\n\nBest,\nHR team")
                        if st.form_submit_button("Record outreach", type="primary", icon=":material/send:"):
                            execute("INSERT INTO outreach_logs(hiring_request_id,channel,message) VALUES(?,?,?)", (request_item["id"], channel.lower().replace(" ", ""), text))
                            execute("UPDATE hiring_requests SET status='contacted' WHERE id=?", (request_item["id"],))
                            st.success(f"Outreach recorded for {target}. No external message was sent.")
                            st.rerun()
                else:
                    st.caption("This request is closed.")


if st.session_state.view == "Project board":
    project_board()
elif st.session_state.view == "Task workspace":
    task_workspace()
else:
    hr_board()
