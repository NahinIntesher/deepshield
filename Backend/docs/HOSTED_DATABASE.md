# Hosted database

DeepShield's database was migrated to Neon Free on 25 October 2026.

- Project: `DeepShield` (`autumn-glade-03633170`).
- Region: AWS Singapore.
- Branch: `production`; database: `deepshield`; PostgreSQL 18.
- Console: https://console.neon.tech/app/projects/autumn-glade-03633170/branches/br-bold-forest-azpli1si
- The connection URL is stored only in the ignored `Backend/.env`. Do not copy it into frontend code, documentation or chat.
- SQLAlchemy uses psycopg 3 and pool pre-ping to recover stale idle connections.

## Migration verification

The API was stopped before taking the final SQLite snapshot. The destination was migrated to revision `0007`; data was copied in one transaction, in foreign-key dependency order. Each table's typed rows were compared using a deterministic digest before commit. Integer sequences were reset after preserving source IDs.

28 tables and 173 rows were copied. The migration-time counts are in `review/neon-migration-counts.json`. Verification confirmed 7 accounts, exactly one owner Admin, 12 bilingual lessons and 8 research submissions. A rolled-back insert confirmed new user IDs advance beyond imported IDs. Client-side TLS was confirmed using the driver's SSL status. Neon's internal `pg_stat_ssl` can reflect its proxy-to-Postgres hop and is not the client connection's TLS status.

The original local database remains at `Database/swin_research.db`. The final pre-migration snapshot is `Database/backups/snapshot-20261025-073047-322584.db`. The hosted database becomes authoritative once the API restarts; later hosted changes are not written back to the old SQLite file.

29 regression tests passed, including copy preservation and refusal to overwrite destination data. The API restarted against PostgreSQL, returned HTTP 200, and the original Admin credentials opened the dashboard in the browser. New session creation and account/analytics reads therefore worked against the hosted database. Proof screenshots are `review/neon-hosted-overview.jpg` and `review/neon-connected-admin.jpg`.

The transfer utility is `Backend/host_database.py`; it refuses an existing non-empty destination and does not print credentials or row values on errors.

## Scope and operations

Only the database is hosted. The API, frontend, checkpoint and uploaded media still run or live locally. Upload/model files are not stored inside PostgreSQL.

For future backend hosting, set the same private `DATABASE_URL` as a server environment secret and install `Backend/requirements.txt`. Do not upload the `.env` file publicly. Direct connections are currently used; review connection pooling when deploying multiple workers.

Neon Free includes limited compute/storage and autosuspension. The console currently shows six hours of history retention. Before public release, arrange an off-provider PostgreSQL backup and test restoration. `Backend/backup.py` is a SQLite backup tool; it does not back up the live Neon database.

To roll back to SQLite, first stop the API and decide how to preserve changes made on Neon since migration. Remove `DATABASE_URL` only after that decision. Restarting without it selects the old local database, which is no longer synchronized.
