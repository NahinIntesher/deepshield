import getpass,argparse
from app.migrate import upgrade
from app.database import SessionLocal
from app.models.db_models import User
from app.routers.auth import _hash_password
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['create-admin']);p.add_argument('--username',default='admin');a=p.parse_args();password=getpass.getpass('Administrator password (12+ characters): ')
 if len(password)<12 or password!=getpass.getpass('Confirm password: '):raise SystemExit('Use matching passwords of at least 12 characters.')
 upgrade()
 with SessionLocal() as db:
  if db.query(User).filter_by(role='admin').first():raise SystemExit('An administrator already exists. Only one owner administrator is allowed.')
  if db.query(User).filter_by(username=a.username.lower()).first():raise SystemExit('Username already exists; nothing changed.')
  db.add(User(username=a.username.lower(),display_name='Administrator',role='admin',password_hash=_hash_password(password)));db.commit()
 print('Administrator created. Open /admin/login.')
