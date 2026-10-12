"""Connections must close and failed writes must not escape their transaction."""
import sqlite3
from pathlib import Path

import pytest

from apps.api.storage import PilotStore


def test_connection_closes_after_success(tmp_path: Path) -> None:
    store = PilotStore(tmp_path)
    with store.connection() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_connection_rolls_back_and_closes_after_exception(tmp_path: Path) -> None:
    store = PilotStore(tmp_path)
    store.put("report", "existing", {"status": "ready"})
    with pytest.raises(RuntimeError, match="interrupted"), store.connection() as connection:
        connection.execute("INSERT INTO records VALUES ('report', 'new', '{}', 'now')")
        raise RuntimeError("interrupted")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
    assert store.get("report", "new") is None
    assert store.get("report", "existing") == {"status": "ready"}
