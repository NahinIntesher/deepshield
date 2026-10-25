"""SQLite snapshots and non-overwriting restore. Stop the API before a full media backup."""
import argparse
import datetime as dt
import sqlite3
from pathlib import Path


def verify(path: Path):
    if not path.is_file():
        raise ValueError('Database file not found')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')


def snapshot(source: Path, destination: Path):
    source, destination = source.resolve(), destination.resolve()
    verify(source)
    if source == destination or destination.exists():
        raise ValueError('Choose a new destination. Existing databases are never overwritten.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of an existing backup.
    with destination.open('xb'):
        pass
    try:
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        verify(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['backup', 'verify', 'restore'])
    parser.add_argument('--source', type=Path)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source = args.source or root.parent / 'Database' / 'swin_research.db'
    if args.command == 'verify':
        verify(source)
        print('SQLite integrity: ok')
    else:
        if args.command == 'restore' and not args.destination:
            parser.error('Restore requires --destination pointing to a new file. Stop the API before switching databases.')
        target = args.destination or root.parent / 'Database' / 'backups' / ('snapshot-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.db')
        print(snapshot(source, target))
