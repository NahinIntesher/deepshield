"""Google subject bindings and exactly one owner administrator."""
from alembic import op
import sqlalchemy as sa
from app.product_models import GoogleIdentity

revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
 bind=op.get_bind()
 if bind.execute(sa.text("SELECT COUNT(*) FROM users WHERE role='admin'")).scalar()>1:
  raise RuntimeError('Choose one owner administrator before upgrading; do not automatically demote existing administrators.')
 GoogleIdentity.__table__.create(bind,checkfirst=True)
 if 'uq_single_owner_admin' not in {i['name'] for i in sa.inspect(bind).get_indexes('users')}:
  op.create_index('uq_single_owner_admin','users',['role'],unique=True,sqlite_where=sa.text("role='admin'"),postgresql_where=sa.text("role='admin'"))

def downgrade():
 op.drop_index('uq_single_owner_admin',table_name='users')
 GoogleIdentity.__table__.drop(op.get_bind(),checkfirst=True)
