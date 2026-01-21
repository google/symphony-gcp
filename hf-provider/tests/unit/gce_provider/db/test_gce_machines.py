import os
import stat
import sqlite3
import textwrap
import pytest
from typing import Optional
from unittest.mock import MagicMock, patch

from gce_provider.db.machines import MachineDao

class _DummyConfig:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = MagicMock()  # Mock logger for testing

def _make_db(db_path: str, schema_sql: Optional[str]):
    """Create (or touch) a SQLite DB with optional schema."""
    # Ensure parent exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        if schema_sql:
            conn.executescript(schema_sql)

def test_quick_check_ok_autoinc_table(tmp_path):
    """
    machines table allows INSERT DEFAULT VALUES because it has only an autoincrement PK.
    Expect: ok=True, insert_ok=True, delete_ok=True, needs_required_values=False
    """
    db_path = tmp_path / "ok_autoinc.db"
    _make_db(
        str(db_path),
        textwrap.dedent(
            """
            CREATE TABLE machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );
            """
        ),
    )

    dao = MachineDao(_DummyConfig(str(db_path)))
    ok, details = dao._quick_check()
    assert ok is True
    assert details["table_exists"] is True
    assert details["writable"] is True
    assert details["integrity"] == "ok"
    assert details["insert_ok"] is True
    assert details["delete_ok"] is True
    assert details["needs_required_values"] is False


def test_check_ok_but_needs_required_values(tmp_path):
    """
    machines has a NOT NULL column without a default, so INSERT DEFAULT VALUES fails.
    Permissions and integrity are fine.
    Expect: ok=True, needs_required_values=True, insert_ok=False, delete_ok=False
    """
    db_path = tmp_path / "needs_values.db"
    _make_db(
        str(db_path),
        textwrap.dedent(
            """
            CREATE TABLE machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                req TEXT NOT NULL
            );
            """
        ),
    )

    dao = MachineDao(_DummyConfig(str(db_path)))
    ok, details = dao._quick_check()
    assert ok is True
    assert details["table_exists"] is True
    assert details["writable"] is True
    assert details["integrity"] == "ok"
    assert details["needs_required_values"] is True
    # Since INSERT DEFAULT VALUES failed, these should remain False
    assert details["insert_ok"] is False
    assert details["delete_ok"] is False


def test_check_missing_table(tmp_path):
    """
    DB exists but machines table is missing.
    Expect: ok=False, table_exists=False
    """
    db_path = tmp_path / "missing_table.db"
    _make_db(str(db_path), schema_sql=None)

    dao = MachineDao(_DummyConfig(str(db_path)))
    ok, details = dao._quick_check()
    assert ok is False
    assert details["table_exists"] is False
    assert details["integrity"] != "ok"

@patch("gce_provider.db.machines.sqlite3")
def test_check_readonly_db(mock_sqlite, tmp_path):
    """
    Simulate a read-only DB by forcing an OperationalError during BEGIN IMMEDIATE.
    """
    db_path = tmp_path / "readonly.db"
    # Create the DB first so it passes existence check
    _make_db(str(db_path), "CREATE TABLE machines (id INTEGER PRIMARY KEY);")
    
    # 1. Preserve original exception classes so try/except works
    mock_sqlite.Error = sqlite3.Error
    mock_sqlite.OperationalError = sqlite3.OperationalError
    mock_sqlite.DatabaseError = sqlite3.DatabaseError
    mock_sqlite.IntegrityError = sqlite3.IntegrityError
    
    # 2. Setup mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite.connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # 3. Create a side effect to raise error only on BEGIN IMMEDIATE
    def side_effect(query, *args):
        if "BEGIN IMMEDIATE" in query:
             raise sqlite3.OperationalError("attempt to write a readonly database")
        return MagicMock()  # Return mock for other queries
        
    mock_cursor.execute.side_effect = side_effect

    # Run the check
    dao = MachineDao(_DummyConfig(str(db_path)))
    ok, details = dao._quick_check()

    assert ok is False
    assert details["writable"] is False
    assert "Not Writable" in details["integrity"]

def test_check_raises_wrapper(tmp_path):
    """
    check_or_raise() should raise RuntimeError when a critical issue exists.
    Use a DB with no machines table.
    """
    db_path = tmp_path / "no_table.db"
    _make_db(str(db_path), schema_sql=None)

    dao = MachineDao(_DummyConfig(str(db_path)))
    with pytest.raises(RuntimeError):
        dao.check_or_raise()