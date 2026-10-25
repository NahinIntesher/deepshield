"""Retire moderator role and preserve payment deduplication after account deletion."""
import hashlib
import sqlalchemy as sa
from alembic import op
from app.product_models import PaymentReceipt

revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
 bind=op.get_bind()
 retired=[r[0] for r in bind.execute(sa.text("SELECT id FROM users WHERE role='moderator'"))]
 for uid in retired:
  bind.execute(sa.text('DELETE FROM auth_sessions WHERE user_id=:uid'),{'uid':uid})
  bind.execute(sa.text('DELETE FROM product_extension_tokens WHERE user_id=:uid'),{'uid':uid})
 bind.execute(sa.text("UPDATE users SET role='participant' WHERE role='moderator'"))
 PaymentReceipt.__table__.create(bind,checkfirst=True)
 existing={r[0] for r in bind.execute(sa.text('SELECT reference_hash FROM payment_receipts'))}
 for (reference,) in bind.execute(sa.text("SELECT reference FROM subscription_requests WHERE status='approved' AND reference<>''")):
  digest=hashlib.sha256(reference.strip().upper().encode()).hexdigest()
  if digest not in existing:
   bind.execute(PaymentReceipt.__table__.insert().values(reference_hash=digest));existing.add(digest)

def downgrade():
 # Retired privileges are never automatically restored.
 PaymentReceipt.__table__.drop(op.get_bind(),checkfirst=True)
