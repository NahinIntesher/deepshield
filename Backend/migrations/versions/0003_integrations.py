"""Add opt-in browser extension credentials and subscription lifecycle."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('subscriptions',
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('plan',sa.String(16),nullable=False),
        sa.Column('status',sa.String(16),nullable=False),
        sa.Column('requested_at',sa.DateTime()),
        sa.Column('activated_at',sa.DateTime()),
        sa.Column('expires_at',sa.DateTime()),
        sa.Column('updated_at',sa.DateTime()))
    op.create_table('extension_tokens',
        sa.Column('token_hash',sa.String(64),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime()),
        sa.Column('expires_at',sa.DateTime(),nullable=False),
        sa.Column('revoked_at',sa.DateTime()))
    op.create_index('ix_extension_tokens_user_id','extension_tokens',['user_id'])

def downgrade():
    op.drop_index('ix_extension_tokens_user_id',table_name='extension_tokens')
    op.drop_table('extension_tokens')
    op.drop_table('subscriptions')
