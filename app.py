"""Objection: a local research-project and hiring workflow application.

Run with: python app.py
Then visit: http://127.0.0.1:5000
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "objection.db"
app = Flask(__name__, static_folder=str(ROOT), static_url_path="")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def one(cursor: sqlite3.Cursor) -> dict[str, Any]:
    record = cursor.fetchone()
    if not record:
        abort(404, description="Record not found")
    return dict(record)


def payload(*fields: str) -> dict[str, Any]:
    data = request.get_json(silent=True) or {}
    missing = [field for field in fields if not str(data.get(field, "")).strip()]
    if missing:
        abort(400, description=f"Required field missing: {', '.join(missing)}")
    return data


def initialise_database() -> None:
    with closing(db()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'upcoming' CHECK(status IN ('upcoming', 'active', 'blocked', 'done')),
                is_complete INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                depends_on_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                PRIMARY KEY(task_id, depends_on_id),
                CHECK(task_id <> depends_on_id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                author TEXT NOT NULL CHECK(author IN ('professor', 'phd', 'agent', 'hr')),
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                programme TEXT NOT NULL,
                experience TEXT NOT NULL,
                skills TEXT NOT NULL,
                availability_hours INTEGER NOT NULL,
                email TEXT NOT NULL,
                whatsapp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hiring_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                candidate_id INTEGER NOT NULL REFERENCES candidates(id),
                requested_by TEXT NOT NULL DEFAULT 'Arjun Shah',
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'contacted')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, candidate_id)
            );
            CREATE TABLE IF NOT EXISTS outreach_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hiring_request_id INTEGER NOT NULL REFERENCES hiring_requests(id) ON DELETE CASCADE,
                channel TEXT NOT NULL CHECK(channel IN ('email', 'whatsapp')),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
            connection.execute(
                "INSERT INTO projects(name, description) VALUES (?, ?)",
                ("Vision benchmark evaluation", "Prepare, evaluate, and report on the new vision benchmark."),
            )
            project_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
            tasks = [
                ("Define evaluation protocol", "Metrics, baselines & acceptance criteria", "done", 1),
                ("Data collection", "Collect and validate benchmark data", "active", 0),
                ("Hire student assistant", "Find a HiWi for dataset preparation", "active", 0),
                ("Implement evaluation pipeline", "PyTorch benchmark implementation", "blocked", 0),
                ("Run benchmark & report", "Results, error analysis, and summary", "upcoming", 0),
            ]
            ids = []
            for title, description, status, complete in tasks:
                cursor = connection.execute(
                    "INSERT INTO tasks(project_id,title,description,status,is_complete) VALUES(?,?,?,?,?)",
                    (project_id, title, description, status, complete),
                )
                ids.append(cursor.lastrowid)
            connection.executemany(
                "INSERT INTO task_dependencies(task_id, depends_on_id) VALUES (?,?)",
                [(ids[1], ids[0]), (ids[2], ids[0]), (ids[3], ids[1]), (ids[3], ids[2]), (ids[4], ids[3])],
            )
            connection.executemany(
                "INSERT INTO messages(task_id,author,body) VALUES (?,?,?)",
                [
                    (ids[1], "professor", "For data collection, we need someone to prepare and validate the benchmark inputs. Can you organize support?"),
                    (ids[1], "phd", "I’ll coordinate it. This is a good fit for a HiWi with Python and computer-vision experience."),
                    (ids[1], "agent", "I can search the student pool. I’ll prioritize availability, Python/PyTorch fluency, and relevant computer-vision work."),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO candidates(name,programme,experience,skills,availability_hours,email,whatsapp) VALUES(?,?,?,?,?,?,?)",
                [
                    ("Mira Patel", "MSc Computer Science", "Computer-vision lab project", "Python, PyTorch, OpenCV", 10, "mira.patel@example.edu", "+49 151 000001"),
                    ("Leon Fischer", "MSc Data Science", "PyTorch and MLOps", "Python, PyTorch, MLflow", 8, "leon.fischer@example.edu", "+49 151 000002"),
                    ("Sofia Romano", "MSc Robotics", "Image segmentation", "Python, CV, ROS", 12, "sofia.romano@example.edu", "+49 151 000003"),
                    ("David Chen", "MSc AI", "Evaluation tooling", "Python, testing, data pipelines", 8, "david.chen@example.edu", "+49 151 000004"),
                    ("Nora Williams", "MSc Informatics", "Visual learning", "Python, PyTorch, research", 9, "nora.williams@example.edu", "+49 151 000005"),
                ],
            )
        connection.commit()


def task_record(connection: sqlite3.Connection, task_id: int) -> dict[str, Any]:
    task = one(connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)))
    task["is_complete"] = bool(task["is_complete"])
    task["dependencies"] = [row["depends_on_id"] for row in connection.execute(
        "SELECT depends_on_id FROM task_dependencies WHERE task_id=?", (task_id,)
    )]
    return task


@app.get("/")
def home():
    return send_from_directory(ROOT, "platform.html")


@app.get("/api/projects")
def list_projects():
    with closing(db()) as connection:
        return jsonify(rows(connection.execute(
            "SELECT p.*, COUNT(t.id) AS task_count FROM projects p LEFT JOIN tasks t ON t.project_id=p.id GROUP BY p.id ORDER BY p.created_at DESC"
        )))


@app.post("/api/projects")
def create_project():
    data = payload("name")
    with closing(db()) as connection:
        cursor = connection.execute("INSERT INTO projects(name,description) VALUES(?,?)", (data["name"].strip(), data.get("description", "").strip()))
        connection.commit()
        return jsonify(one(connection.execute("SELECT * FROM projects WHERE id=?", (cursor.lastrowid,)))), 201


@app.delete("/api/projects/<int:project_id>")
def delete_project(project_id: int):
    with closing(db()) as connection:
        if not connection.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            abort(404)
        connection.execute("DELETE FROM projects WHERE id=?", (project_id,))
        connection.commit()
    return "", 204


@app.get("/api/projects/<int:project_id>/tasks")
def list_tasks(project_id: int):
    with closing(db()) as connection:
        one(connection.execute("SELECT id FROM projects WHERE id=?", (project_id,)))
        task_ids = [row["id"] for row in connection.execute("SELECT id FROM tasks WHERE project_id=? ORDER BY id", (project_id,))]
        return jsonify([task_record(connection, task_id) for task_id in task_ids])


@app.post("/api/projects/<int:project_id>/tasks")
def create_task(project_id: int):
    data = payload("title")
    with closing(db()) as connection:
        one(connection.execute("SELECT id FROM projects WHERE id=?", (project_id,)))
        status = data.get("status", "upcoming")
        if status not in {"upcoming", "active", "blocked", "done"}:
            abort(400, description="Invalid status")
        cursor = connection.execute(
            "INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)",
            (project_id, data["title"].strip(), data.get("description", "").strip(), status),
        )
        task_id = cursor.lastrowid
        for dependency_id in data.get("dependencies", []):
            dependency = one(connection.execute("SELECT project_id FROM tasks WHERE id=?", (dependency_id,)))
            if dependency["project_id"] != project_id:
                abort(400, description="Dependencies must belong to the same project")
            connection.execute("INSERT INTO task_dependencies(task_id,depends_on_id) VALUES(?,?)", (task_id, dependency_id))
        connection.commit()
        return jsonify(task_record(connection, task_id)), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id: int):
    data = request.get_json(silent=True) or {}
    allowed = {"title", "description", "status", "is_complete"}
    values = {key: value for key, value in data.items() if key in allowed}
    if not values:
        abort(400, description="No supported fields supplied")
    if values.get("status") not in {None, "upcoming", "active", "blocked", "done"}:
        abort(400, description="Invalid status")
    with closing(db()) as connection:
        task_record(connection, task_id)
        sets = ", ".join(f"{key}=?" for key in values)
        normalized = [int(value) if key == "is_complete" else value for key, value in values.items()]
        connection.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*normalized, task_id))
        connection.commit()
        return jsonify(task_record(connection, task_id))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    with closing(db()) as connection:
        task_record(connection, task_id)
        connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        connection.commit()
    return "", 204


@app.get("/api/tasks/<int:task_id>/messages")
def list_messages(task_id: int):
    with closing(db()) as connection:
        task_record(connection, task_id)
        return jsonify(rows(connection.execute("SELECT * FROM messages WHERE task_id=? ORDER BY id", (task_id,))))


@app.post("/api/tasks/<int:task_id>/messages")
def create_message(task_id: int):
    data = payload("body")
    author = data.get("author", "phd")
    if author not in {"professor", "phd", "agent", "hr"}:
        abort(400, description="Invalid author")
    with closing(db()) as connection:
        task_record(connection, task_id)
        cursor = connection.execute("INSERT INTO messages(task_id,author,body) VALUES(?,?,?)", (task_id, author, data["body"].strip()))
        connection.commit()
        return jsonify(one(connection.execute("SELECT * FROM messages WHERE id=?", (cursor.lastrowid,)))), 201


@app.post("/api/tasks/<int:task_id>/candidates/search")
def search_candidates(task_id: int):
    with closing(db()) as connection:
        task_record(connection, task_id)
        return jsonify(rows(connection.execute("SELECT * FROM candidates ORDER BY availability_hours DESC, name LIMIT 5")))


@app.post("/api/tasks/<int:task_id>/hiring-requests")
def create_hiring_request(task_id: int):
    data = payload("candidate_id")
    with closing(db()) as connection:
        task_record(connection, task_id)
        one(connection.execute("SELECT id FROM candidates WHERE id=?", (data["candidate_id"],)))
        try:
            cursor = connection.execute("INSERT INTO hiring_requests(task_id,candidate_id) VALUES(?,?)", (task_id, data["candidate_id"]))
        except sqlite3.IntegrityError:
            abort(409, description="This candidate already has a request for this task")
        connection.execute("INSERT INTO messages(task_id,author,body) VALUES(?,?,?)", (task_id, "agent", "I created the HR request. The HR team can now review and contact the candidate."))
        connection.commit()
        return jsonify(one(connection.execute("SELECT * FROM hiring_requests WHERE id=?", (cursor.lastrowid,)))), 201


@app.get("/api/hiring-requests")
def list_hiring_requests():
    with closing(db()) as connection:
        return jsonify(rows(connection.execute(
            """SELECT h.*, c.name AS candidate_name, c.programme, c.experience, c.email, c.whatsapp,
                      t.title AS task_title, p.name AS project_name,
                      (SELECT COUNT(*) FROM outreach_logs o WHERE o.hiring_request_id=h.id) AS outreach_count,
                      (SELECT channel FROM outreach_logs o WHERE o.hiring_request_id=h.id ORDER BY o.id DESC LIMIT 1) AS last_channel
               FROM hiring_requests h JOIN candidates c ON c.id=h.candidate_id JOIN tasks t ON t.id=h.task_id
               JOIN projects p ON p.id=t.project_id ORDER BY h.created_at DESC"""
        )))


@app.patch("/api/hiring-requests/<int:request_id>")
def update_hiring_request(request_id: int):
    data = payload("status")
    if data["status"] not in {"pending", "approved", "rejected", "contacted"}:
        abort(400, description="Invalid hiring-request status")
    with closing(db()) as connection:
        one(connection.execute("SELECT id FROM hiring_requests WHERE id=?", (request_id,)))
        connection.execute("UPDATE hiring_requests SET status=? WHERE id=?", (data["status"], request_id))
        connection.commit()
    return jsonify({"id": request_id, "status": data["status"]})


@app.post("/api/hiring-requests/<int:request_id>/outreach")
def log_outreach(request_id: int):
    data = payload("channel", "message")
    if data["channel"] not in {"email", "whatsapp"}:
        abort(400, description="Channel must be email or whatsapp")
    with closing(db()) as connection:
        one(connection.execute("SELECT id FROM hiring_requests WHERE id=?", (request_id,)))
        cursor = connection.execute("INSERT INTO outreach_logs(hiring_request_id,channel,message) VALUES(?,?,?)", (request_id, data["channel"], data["message"].strip()))
        connection.execute("UPDATE hiring_requests SET status='contacted' WHERE id=?", (request_id,))
        connection.commit()
        return jsonify(one(connection.execute("SELECT * FROM outreach_logs WHERE id=?", (cursor.lastrowid,)))), 201


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "database": str(DATABASE)})


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(409)
def client_error(error):
    return jsonify({"error": error.description}), error.code


if __name__ == "__main__":
    initialise_database()
    app.run(debug=True, host="127.0.0.1", port=5000)
