"""Verified email registration and mandatory Google profile completion."""
from alembic import op
import sqlalchemy as sa
from app.product_models import PendingRegistration

revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None

def upgrade():
 bind=op.get_bind()
 names={c['name'] for c in sa.inspect(bind).get_columns('users')}
 for column in [sa.Column('email',sa.String(254),nullable=True),sa.Column('email_verified_at',sa.DateTime(),nullable=True),sa.Column('needs_profile',sa.Boolean(),nullable=False,server_default=sa.false())]:
  if column.name not in names:op.add_column('users',column)
 op.create_index('uq_users_email','users',['email'],unique=True)
 PendingRegistration.__table__.create(bind,checkfirst=True)
 bind.execute(sa.text("UPDATE users SET needs_profile=:value WHERE username LIKE 'google_%' AND id IN (SELECT user_id FROM google_identities)"),{'value':True})

def downgrade():
 PendingRegistration.__table__.drop(op.get_bind(),checkfirst=True)
 op.drop_index('uq_users_email',table_name='users')
 with op.batch_alter_table('users') as batch:
  for name in ['needs_profile','email_verified_at','email']:batch.drop_column(name)
