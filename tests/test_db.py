import os
import tempfile
from unittest.mock import Mock

import psycopg
import pytest
from psycopg.rows import dict_row

import db


def setup_module():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ.pop("DATABASE_URL", None)
    os.environ["SQLITE_PATH"] = path
    setup_module.path = path
    db.init_db()


def teardown_module():
    try:
        os.remove(setup_module.path)
    except FileNotFoundError:
        pass


def test_database_mode_is_sqlite_without_database_url():
    assert db.database_mode() == "SQLite"


def test_create_and_list_ticket():
    db.create_ticket("Projector issue", "Hardware", "High", "Projector will not power on.")
    tickets = db.list_tickets()
    assert any(t["title"] == "Projector issue" for t in tickets)


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_list_tickets_uses_dictionary_rows_for_postgresql(monkeypatch, scheme):
    url = f"{scheme}://localhost/helpdesk"
    monkeypatch.setenv("DATABASE_URL", url)
    ticket = {
        "id": 1,
        "title": "Projector issue",
        "category": "Hardware",
        "priority": "High",
        "status": "Open",
        "description": "Projector will not power on.",
        "created_at": "2026-01-01",
    }
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = [ticket]
    connect = Mock(return_value=conn)
    monkeypatch.setattr(psycopg, "connect", connect)

    assert db.database_mode() == "PostgreSQL"
    assert db.list_tickets() == [ticket]
    connect.assert_called_once_with(url, row_factory=dict_row)
    conn.close.assert_called_once()


def test_update_status():
    tickets = db.list_tickets()
    ticket_id = tickets[0]["id"]
    db.update_status(ticket_id, "Closed")
    updated = {t["id"]: t for t in db.list_tickets()}
    assert updated[ticket_id]["status"] == "Closed"


def test_rejects_blank_title():
    try:
        db.create_ticket("", "Hardware", "Low", "Description")
    except ValueError as exc:
        assert "Title" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
