"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import sqlite3
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# SQLite database path
DB_PATH = current_dir / "activities.db"

# Initial data used to seed the database on first run
INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY (activity_name) REFERENCES activities (name) ON DELETE CASCADE
            )
            """
        )
        conn.commit()


def seed_db_if_empty() -> None:
    with get_connection() as conn:
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM activities"
        ).fetchone()[0]
        if existing_count > 0:
            return

        for name, activity in INITIAL_ACTIVITIES.items():
            conn.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    activity["description"],
                    activity["schedule"],
                    activity["max_participants"],
                ),
            )

            for email in activity["participants"]:
                conn.execute(
                    """
                    INSERT INTO registrations (activity_name, email)
                    VALUES (?, ?)
                    """,
                    (name, email),
                )

        conn.commit()


def activity_exists(conn: sqlite3.Connection, activity_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM activities WHERE name = ?",
        (activity_name,),
    ).fetchone()
    return row is not None


def load_activities_from_db() -> dict:
    with get_connection() as conn:
        activity_rows = conn.execute(
            """
            SELECT name, description, schedule, max_participants
            FROM activities
            ORDER BY name
            """
        ).fetchall()

        registrations_by_activity = {}
        for registration_row in conn.execute(
            """
            SELECT activity_name, email
            FROM registrations
            ORDER BY activity_name, email
            """
        ).fetchall():
            registrations_by_activity.setdefault(
                registration_row["activity_name"], []
            ).append(registration_row["email"])

    activities = {}
    for row in activity_rows:
        name = row["name"]
        activities[name] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": registrations_by_activity.get(name, []),
        }

    return activities


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_db_if_empty()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities_from_db()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as conn:
        # Validate activity exists
        if not activity_exists(conn, activity_name):
            raise HTTPException(status_code=404, detail="Activity not found")

        # Validate student is not already signed up
        existing = conn.execute(
            """
            SELECT 1
            FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        conn.execute(
            """
            INSERT INTO registrations (activity_name, email)
            VALUES (?, ?)
            """,
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as conn:
        # Validate activity exists
        if not activity_exists(conn, activity_name):
            raise HTTPException(status_code=404, detail="Activity not found")

        # Validate student is signed up
        existing = conn.execute(
            """
            SELECT 1
            FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        ).fetchone()
        if existing is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        conn.execute(
            """
            DELETE FROM registrations
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
