"""Exercise full snapshot transfer and refusal to overwrite existing hosted data."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
import sqlalchemy as sa

from host_database import transfer


def migrated(path):
    engine = sa.create_engine(sa.URL.create('sqlite', database=str(path)))
    subprocess.run([sys.executable, '-c', 'from app.migrate import upgrade; upgrade()'],
                   cwd=Path(__file__).resolve().parents[1],
                   env={**os.environ, 'DATABASE_URL': str(engine.url)},
                   check=True, capture_output=True)
    return engine


def test_copy_preserves_ids_unicode_flags_and_refuses_overwrite(tmp_path):
    source, target = migrated(tmp_path/'source.db'), migrated(tmp_path/'target.db')
    try:
        with source.begin() as conn:
            conn.execute(sa.text('INSERT INTO users(id,username,display_name,password_hash,role,qualified_for_research,created_at) '
                                 'VALUES(83,:u,:n,:h,:r,true,:d)'),
                         {'u':'owner','n':'বাংলা নাম','h':'fixture-hash','r':'admin','d':'2026-10-25 03:04:05.123456'})
            conn.execute(sa.text('INSERT INTO notifications(id,user_id,title,message,read) VALUES(91,83,:t,:m,true)'),
                         {'t':'বিজ্ঞপ্তি','m':'অক্ষত তথ্য'})
            conn.execute(sa.text("UPDATE lessons SET content_bn=:content WHERE id=1"),
                         {'content':'{"title":"পরিবর্তিত পাঠ"}'})
        report = transfer(source, target)
        assert report['users'] == report['notifications'] == 1
        assert report['lessons'] == 12
        with target.connect() as conn:
            assert conn.execute(sa.text('SELECT display_name,password_hash FROM users WHERE id=83')).one() == ('বাংলা নাম','fixture-hash')
            assert conn.execute(sa.text('SELECT content_bn FROM lessons WHERE id=1')).scalar() == '{"title":"পরিবর্তিত পাঠ"}'
        with pytest.raises(ValueError, match='Target contains data'):
            transfer(source, target)
        with target.connect() as conn:
            assert conn.execute(sa.text('SELECT COUNT(*) FROM notifications')).scalar() == 1
    finally:
        source.dispose()
        target.dispose()


def test_changed_destination_lessons_are_not_replaced(tmp_path):
    source, target = migrated(tmp_path/'source.db'), migrated(tmp_path/'target.db')
    try:
        with target.begin() as conn:
            conn.execute(sa.text("UPDATE lessons SET correct_choice=99 WHERE id=1"))
        with pytest.raises(ValueError, match='Target lessons were edited'):
            transfer(source, target)
        with target.connect() as conn:
            assert conn.execute(sa.text('SELECT correct_choice FROM lessons WHERE id=1')).scalar() == 99
    finally:
        source.dispose()
        target.dispose()
