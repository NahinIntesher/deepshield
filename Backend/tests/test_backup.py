import sqlite3

import pytest

from backup import snapshot, verify


def test_backup_restore_preserves_rows_and_refuses_overwrite(tmp_path):
    source, saved, restored = (tmp_path / name for name in ('source.db', 'snapshot.db', 'restored.db'))
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT)')
        db.execute('INSERT INTO accounts(name) VALUES (?)', ('Existing member',))
    snapshot(source, saved)
    snapshot(saved, restored)
    verify(restored)
    with sqlite3.connect(restored) as db:
        assert db.execute('SELECT name FROM accounts').fetchone()[0] == 'Existing member'
    with pytest.raises(ValueError):
        snapshot(saved, source)
    with pytest.raises(ValueError):
        snapshot(source, source)
