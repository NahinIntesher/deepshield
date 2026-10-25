# Database

Production uses Neon PostgreSQL. Configure DATABASE_URL in Backend server secrets.
Alembic migrations live in ../Backend/migrations and run at API startup.
A local SQLite database is created automatically when DATABASE_URL is absent.

Backup/restore tooling: ../Backend/backup.py (SQLite snapshots), and Neon managed recovery for PostgreSQL.
Migration transfer tooling: ../Backend/host_database.py.
Curated replay-memory format: continual/replay_manifest.example.json.

Database contents, private uploads, backups, generated candidates and logs are runtime data.
They remain outside source control. The private media bucket persists videos and scan sources across server restarts.
