"""Shared test configuration, applied before any test module imports the API.

A file-backed SQLite database is used because in-memory SQLite gives every pooled connection its
own empty database, which hides tables created at startup.
"""

import os
import tempfile
from pathlib import Path

_database = Path(tempfile.mkdtemp(prefix="batterymind-tests-")) / "api.sqlite3"
os.environ.setdefault("BATTERYMIND_PROCESSED_DATA_DIR", "data/processed")
os.environ["BATTERYMIND_DATABASE_URL"] = f"sqlite:///{_database}"
