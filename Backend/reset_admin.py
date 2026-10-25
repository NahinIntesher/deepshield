"""Create/rotate the local administrator password without storing it in shell history.

Run from the backend folder: python reset_admin.py
"""
import getpass
import sys
from app.database import SessionLocal
from app.models.db_models import User
from app.routers.auth import _hash_password


def main():
    username=input('Admin username [admin]: ').strip().lower() or 'admin'
    password=getpass.getpass('New administrator password (at least 12 characters): ')
    repeat=getpass.getpass('Repeat password: ')
    if len(password)<12 or password!=repeat:
        sys.exit('Password mismatch or fewer than 12 characters; no changes made.')
    from app.migrate import upgrade
    upgrade()
    with SessionLocal() as db:
        existing=db.query(User).filter_by(username=username).first()
        if existing and existing.role!='admin':sys.exit('That username belongs to a non-administrator.')
        if not existing:
            if db.query(User).filter_by(role='admin').first():
                sys.exit('An administrator already exists. Enter that administrator username; a second administrator cannot be created.')
            existing=User(username=username,display_name='DeepShield Admin',role='admin')
            db.add(existing)
        existing.password_hash=_hash_password(password)
        from app.models.db_models import AuthSession
        from app.product_models import ExtensionToken
        db.flush()
        db.query(AuthSession).filter_by(user_id=existing.id).delete()
        db.query(ExtensionToken).filter_by(user_id=existing.id).delete()
        db.commit()
    print('Administrator credentials rotated. Existing sessions and extension tokens revoked.')

if __name__=='__main__':main()
