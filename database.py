"""SQLite connection helper for local prototype data."""

import sqlite3
from pathlib import Path


def connect_database(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite database at the given path (or use ``:memory:``)."""
    return sqlite3.connect(database_path)
