"""Create the frozen legacy schema, or adopt an existing local database without deleting rows."""
from alembic import op
import sqlalchemy as sa
from migrations.baseline import Base
revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    Base.metadata.create_all(bind=bind,checkfirst=True)
    additions={'users':{'password_hash':sa.String(255)},'rooms':{'deadline':sa.Float()},'research_submissions':{'model_id':sa.String(64),'model_name':sa.String(128),'checkpoint_epoch':sa.Integer(),'inference_metadata':sa.Text()}}
    for table,cols in additions.items():
        present={c['name'] for c in sa.inspect(bind).get_columns(table)}
        for name,kind in cols.items():
            if name not in present:op.add_column(table,sa.Column(name,kind,nullable=True))

def downgrade():
    raise RuntimeError('Legacy adoption is intentionally non-destructive. Restore your backup to return to the pre-migration database.')
