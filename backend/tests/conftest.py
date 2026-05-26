"""Test fixtures: override the DB to a transient SQLite so tests run without Postgres."""

import os

# Must be set before importing app.* so settings/database pick this up
os.environ.setdefault("DATABASE_URL", "sqlite:///./_test_ethics.db")
