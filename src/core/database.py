"""
database.py — SQLite persistence layer for Semantic Extraction Arena.

Tables:
  runs — stores each comparison run with answers, metrics, and winner.
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from src.config import DB_PATH
from src.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT,
    prompt       TEXT,
    timestamp    TEXT,
    model        TEXT,
    sg_answer    TEXT,
    fc_answer    TEXT,
    judge_result TEXT,
    sg_metrics   TEXT,
    fc_metrics   TEXT,
    sg_data      TEXT,
    fc_data      TEXT,
    winner       TEXT
)
"""


def init_db() -> None:
    """Create the database and runs table if they do not exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def save_run(
    url: str,
    prompt: str,
    model: str,
    sg_answer: str,
    fc_answer: str,
    judge_result: str,
    sg_metrics: Dict[str, Any],
    fc_metrics: Dict[str, Any],
    sg_data: Any,
    fc_data: Any,
) -> int:
    """Insert a new run and return its auto-generated ID."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs
                  (url, prompt, timestamp, model, sg_answer, fc_answer,
                   judge_result, sg_metrics, fc_metrics, sg_data, fc_data, winner)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    url,
                    prompt,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    model,
                    sg_answer,
                    fc_answer,
                    judge_result,
                    json.dumps(sg_metrics, default=str),
                    json.dumps(fc_metrics, default=str),
                    json.dumps(sg_data, default=str),
                    json.dumps(fc_data, default=str),
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Failed to save run to database: {e}")
        return -1


def set_winner(run_id: int, winner: Optional[str]) -> None:
    """Set or clear the winner for a run. winner: 'scrapegraph' | 'firecrawl' | None."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE runs SET winner = ? WHERE id = ?", (winner, run_id))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to set winner: {e}")


def delete_run(run_id: int) -> None:
    """Permanently delete a run by ID."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to delete run: {e}")


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_history(limit: int = 30) -> List[Tuple]:
    """Return recent runs as (id, url, prompt, timestamp, model, winner) tuples."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(
                "SELECT id, url, prompt, timestamp, model, winner "
                "FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except sqlite3.Error as e:
        logger.error(f"Failed to get history: {e}")
        return []


def get_run_by_id(run_id: int) -> Optional[Dict[str, Any]]:
    """Return a fully hydrated run dict, or None if not found."""
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()

        if not row:
            return None

        return {
            "id":           row[0],
            "url":          row[1],
            "prompt":       row[2],
            "timestamp":    row[3],
            "model":        row[4],
            "sg_answer":    row[5],
            "fc_answer":    row[6],
            "judge_result": row[7],
            "sg_metrics":   json.loads(row[8]),
            "fc_metrics":   json.loads(row[9]),
            "sg_data":      json.loads(row[10]),
            "fc_data":      json.loads(row[11]),
            "winner":       row[12],
        }
    except (sqlite3.Error, json.JSONDecodeError) as e:
        logger.error(f"Failed to get run by id: {e}")
        return None


def get_all_runs() -> List[Tuple]:
    """
    Return all runs for analytics.
    Columns: id, url, prompt, timestamp, model, winner, sg_metrics, fc_metrics.
    """
    init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(
                "SELECT id, url, prompt, timestamp, model, winner, sg_metrics, fc_metrics "
                "FROM runs ORDER BY id DESC"
            ).fetchall()
    except sqlite3.Error as e:
        logger.error(f"Failed to get all runs: {e}")
        return []
