import os
import stat
import sqlite3
import textwrap
import pytest

from gce_provider.db.machines import MachineDao

class _DummyConfig:
    def __init__(self, db_path: str):
        self.db_path = db_path

def _make_db(db_path: str, schema_sql: str | None):
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


def test_check_readonly_db(tmp_path):
    """
    DB file is read-only, BEGIN IMMEDIATE should fail to acquire a write lock.
    Expect: ok=False, writable=False
    """
    db_path = tmp_path / "readonly.db"
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
    # Make file read-only for owner/group/others
    os.chmod(str(db_path), stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

    dao = MachineDao(_DummyConfig(str(db_path)))
    ok, details = dao._quick_check()

    # Restore perms so tmp cleanup doesn't choke on some systems
    os.chmod(str(db_path), stat.S_IWRITE | stat.S_IREAD)

    assert ok is False
    assert details["table_exists"] is True
    assert details["writable"] is False
    assert "not writable" in str(details.get("integrity", "")).lower()

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
