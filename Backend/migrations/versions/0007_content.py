"""Bilingual lesson content and library archives."""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from app.product_models import Lesson

revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

def upgrade():
 bind=op.get_bind()
 if 'archived' not in {c['name'] for c in sa.inspect(bind).get_columns('research_challenge_items')}:
  op.add_column('research_challenge_items',sa.Column('archived',sa.Boolean(),nullable=False,server_default=sa.false()))
 if 'admin_note' not in {c['name'] for c in sa.inspect(bind).get_columns('research_submissions')}:
  op.add_column('research_submissions',sa.Column('admin_note',sa.Text(),nullable=False,server_default=''))
 Lesson.__table__.create(bind,checkfirst=True)
 if not bind.execute(sa.select(sa.func.count()).select_from(Lesson.__table__)).scalar():
  source=Path(__file__).resolve().parents[2]/'app'/'data'/'lessons.json'
  for row in json.loads(source.read_text(encoding='utf8')):
   bind.execute(Lesson.__table__.insert().values(id=row['id'],content_en=json.dumps(row['en'],ensure_ascii=False),content_bn=json.dumps(row['bn'],ensure_ascii=False),correct_choice=row['answer'],archived=False))

def downgrade():
 Lesson.__table__.drop(op.get_bind(),checkfirst=True)
 with op.batch_alter_table('research_challenge_items') as batch:batch.drop_column('archived')
 with op.batch_alter_table('research_submissions') as batch:batch.drop_column('admin_note')
