"""Exercise legacy adoption and repeat startup against disposable databases."""
import os, subprocess, sys
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.orm import Session
from migrations.baseline import Base, User

ROOT=Path(__file__).resolve().parents[1]

def test_legacy_database_upgrade_preserves_accounts(tmp_path):
    path=tmp_path/'legacy.db';url='sqlite:///'+str(path)
    engine=sa.create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(username='legacy',display_name='Existing member',score=7400,total_rounds_played=100,total_correct=95,role='participant',password_hash='preserved-hash'));db.commit()
    # Simulate older source releases without these columns.
    with engine.begin() as conn:
        conn.execute(sa.text('ALTER TABLE rooms DROP COLUMN deadline'))
        conn.execute(sa.text('ALTER TABLE research_submissions DROP COLUMN model_name'))
    env={**os.environ,'DATABASE_URL':url}
    for _ in range(2):
        subprocess.run([sys.executable,'-c','from app.migrate import upgrade; upgrade()'],cwd=ROOT,env=env,check=True,capture_output=True)
    with engine.connect() as conn:
        row=conn.execute(sa.text('SELECT score,total_correct,total_rounds_played,password_hash FROM users WHERE username=:u'),{'u':'legacy'}).one()
        assert tuple(row)==(7400,95,100,'preserved-hash')
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar()=='0008'
        assert conn.execute(sa.text('SELECT COUNT(*) FROM game_round_records')).scalar()==0
    assert 'deadline' in {c['name'] for c in sa.inspect(engine).get_columns('rooms')}
    assert 'model_name' in {c['name'] for c in sa.inspect(engine).get_columns('research_submissions')}
