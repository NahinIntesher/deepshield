"""Add activity, course progress, audit and durable training-job history."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('game_round_records',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('event_key',sa.String(128),nullable=False,unique=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('item_id',sa.Integer(),sa.ForeignKey('research_challenge_items.id'),nullable=False),sa.Column('mode',sa.String(16),nullable=False),sa.Column('prediction',sa.String(16),nullable=False),sa.Column('ground_truth',sa.String(16),nullable=False),sa.Column('correct',sa.Boolean(),nullable=False),sa.Column('points',sa.Integer(),nullable=False),sa.Column('response_ms',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime()))
    op.create_table('detection_records',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('source_name',sa.String(256),nullable=False),sa.Column('verdict',sa.String(16),nullable=False),sa.Column('confidence',sa.Float(),nullable=False),sa.Column('model_id',sa.String(64)),sa.Column('result_json',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime()))
    op.create_table('course_progress',sa.Column('key',sa.String(128),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('lesson_id',sa.Integer(),nullable=False),sa.Column('attempts',sa.Integer()),sa.Column('last_choice',sa.Integer(),nullable=False),sa.Column('completed',sa.Boolean()),sa.Column('updated_at',sa.DateTime()))
    op.create_table('audit_logs',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id')),sa.Column('action',sa.String(64),nullable=False),sa.Column('target',sa.String(128),nullable=False),sa.Column('detail',sa.Text()),sa.Column('created_at',sa.DateTime()))
    op.create_table('training_jobs',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id')),sa.Column('status',sa.String(32),nullable=False),sa.Column('message',sa.Text()),sa.Column('report_json',sa.Text()),sa.Column('created_at',sa.DateTime()),sa.Column('finished_at',sa.DateTime()))
    for table in ('game_round_records','detection_records','audit_logs','training_jobs'):
        op.create_index('ix_'+table+'_created_at',table,['created_at'])
    for table in ('game_round_records','detection_records','course_progress'):
        op.create_index('ix_'+table+'_user_id',table,['user_id'])
    # Recompute saved flags at authentication. Do not invent historical events.
    op.execute(sa.text('UPDATE users SET qualified_for_research = false'))

def downgrade():
    for table in ('training_jobs','audit_logs','course_progress','detection_records','game_round_records'):op.drop_table(table)
