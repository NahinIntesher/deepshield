from alembic import op
from app.product_models import Scan,Charge,Membership,Subscription,ExtensionToken,Ticket,Notice,Assessment
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None
MODELS=[Scan,Charge,Membership,Subscription,ExtensionToken,Ticket,Notice,Assessment]
def upgrade():
 for model in MODELS:model.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
 for model in reversed(MODELS):model.__table__.drop(op.get_bind(),checkfirst=True)
