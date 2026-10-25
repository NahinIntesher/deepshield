"""Copy a stopped application's SQLite snapshot to a new, empty PostgreSQL database.

Read DATABASE_URL from the backend environment. Never print credentials or row data.
The existing SQLite file remains untouched. Run app.migrate.upgrade on the target first.
"""
import argparse
import hashlib
import json
from pathlib import Path

import sqlalchemy as sa


def digest(rows):
    encoded = sorted(json.dumps(dict(row), sort_keys=True, default=str, ensure_ascii=False)
                     for row in rows)
    return hashlib.sha256('\n'.join(encoded).encode('utf-8')).hexdigest()


def transfer(source_engine, target_engine):
    source_meta, target_meta = sa.MetaData(), sa.MetaData()
    source_meta.reflect(source_engine)
    target_meta.reflect(target_engine)
    names = set(source_meta.tables) - {'alembic_version'}
    if names - set(target_meta.tables):
        raise ValueError('Target schema is missing source tables; run migrations first.')
    with source_engine.connect() as src, target_engine.begin() as dst:
        if src.dialect.name == 'sqlite':
            if src.exec_driver_sql('PRAGMA integrity_check').scalar() != 'ok':
                raise ValueError('Source integrity check failed.')
            if src.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Source has invalid foreign keys; nothing copied.')
        source_version = src.execute(sa.text('SELECT version_num FROM alembic_version')).scalar()
        target_version = dst.execute(sa.text('SELECT version_num FROM alembic_version')).scalar()
        if source_version != target_version:
            raise ValueError('Source and target migration versions must match.')
        # A fresh migration seeds the lessons. No existing accounts/history may be replaced.
        for table in target_meta.sorted_tables:
            if table.name in ('alembic_version', 'lessons'):
                continue
            if dst.execute(sa.select(sa.func.count()).select_from(table)).scalar():
                raise ValueError('Target contains data. Choose a NEW empty database.')
        lesson_table = target_meta.tables.get('lessons')
        if lesson_table is not None:
            seeded = dst.execute(sa.select(lesson_table)).mappings().all()
            # Only migration seeds (the same initial IDs) may exist at the destination.
            if seeded:
                seed_path = Path(__file__).parent / 'app/data/lessons.json'
                seed_rows = json.loads(seed_path.read_text(encoding='utf-8'))
                seed_ids = {row['id'] for row in seed_rows}
                if {row['id'] for row in seeded} != seed_ids:
                    raise ValueError('Target lessons are not a fresh migration seed.')
                for row in seeded:
                    seed = next(r for r in seed_rows if r['id'] == row['id'])
                    if (json.loads(row['content_en']) != seed['en'] or
                        json.loads(row['content_bn']) != seed['bn'] or
                        row['correct_choice'] != seed['answer'] or row['archived']):
                        raise ValueError('Target lessons were edited; refusing replacement.')
                dst.execute(lesson_table.delete())
        report = {}
        for table in target_meta.sorted_tables:
            if table.name not in names:
                continue
            source_table = source_meta.tables[table.name]
            if set(source_table.columns.keys()) != set(table.columns.keys()):
                raise ValueError('Column mismatch in ' + table.name)
            rows = src.execute(sa.select(source_table)).mappings().all()
            for start in range(0, len(rows), 500):
                dst.execute(table.insert(), [dict(row) for row in rows[start:start+500]])
            copied = dst.execute(sa.select(table)).mappings().all()
            if digest(rows) != digest(copied):
                raise ValueError('Data verification failed in ' + table.name)
            if dst.dialect.name == 'postgresql':
                for column in table.primary_key.columns:
                    if isinstance(column.type, sa.Integer):
                        # Explicit source IDs require resetting PostgreSQL sequences.
                        seq = dst.execute(sa.text('SELECT pg_get_serial_sequence(:t,:c)'),
                                          {'t': table.name, 'c': column.name}).scalar()
                        if seq:
                            maximum = dst.execute(sa.select(sa.func.max(column))).scalar()
                            dst.execute(sa.text('SELECT setval(CAST(:s AS regclass),:n,:used)'),
                                        {'s': seq, 'n': max(1, maximum or 1), 'used': maximum is not None})
            report[table.name] = len(copied)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error('A verified SQLite snapshot is required.')
    from app.database import engine
    if engine.dialect.name != 'postgresql':
        parser.error('DATABASE_URL must select the new PostgreSQL destination.')
    source = sa.create_engine(sa.URL.create('sqlite', database=str(args.source.resolve())))
    try:
        report = transfer(source, engine)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('Committed and verified', len(report), 'tables;', sum(report.values()), 'rows.')
    except Exception as exc:
        # Driver exceptions can contain sensitive query parameters; do not print them.
        print('Migration not completed:', type(exc).__name__)
        raise SystemExit(1) from None
    finally:
        source.dispose()
        engine.dispose()


if __name__ == '__main__':
    main()
