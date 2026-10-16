
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "hirelens.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                match_score REAL NOT NULL,
                skill_score REAL NOT NULL,
                text_similarity REAL NOT NULL,
                matched_skills TEXT NOT NULL,
                missing_skills TEXT NOT NULL,
                ai_recommendation TEXT NOT NULL,
                hr_decision TEXT,
                hr_feedback TEXT,
                published INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_analysis(candidate_id, job_title, result):
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO candidates (
                candidate_id,
                job_title,
                match_score,
                skill_score,
                text_similarity,
                matched_skills,
                missing_skills,
                ai_recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            job_title,
            result["match_score"],
            result["skill_score"],
            result["text_similarity"],
            ", ".join(result["matched_skills"]),
            ", ".join(result["missing_skills"]),
            result["recommendation"],
        ))

        return cursor.lastrowid


def record_hr_decision(record_id, decision, feedback=""):
    allowed_decisions = {"Shortlist", "Reject", "Hold"}

    if decision not in allowed_decisions:
        raise ValueError("Invalid HR decision.")

    initialize_database()

    with get_connection() as connection:
        connection.execute("""
            UPDATE candidates
            SET hr_decision = ?,
                hr_feedback = ?,
                published = 0
            WHERE id = ?
        """, (decision, feedback, record_id))


def publish_decision(record_id):
    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE candidates
            SET published = 1
            WHERE id = ? AND hr_decision IS NOT NULL
        """, (record_id,))

        if cursor.rowcount == 0:
            raise ValueError(
                "Record not found or HR has not made a decision."
            )


def get_published_decision(candidate_id):
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT candidate_id, job_title, hr_decision, hr_feedback
            FROM candidates
            WHERE candidate_id = ? AND published = 1
            ORDER BY id DESC
        """, (candidate_id,)).fetchall()

        return [dict(row) for row in rows]
