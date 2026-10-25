from sqlalchemy import create_engine,event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

# Neon supplies postgresql:// URLs; use the supported psycopg 3 driver.
database_url = make_url(DATABASE_URL)
if database_url.drivername in ('postgres', 'postgresql'):
    database_url = database_url.set(drivername='postgresql+psycopg')
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if database_url.get_backend_name() == 'sqlite' else {}
)

if engine.dialect.name=='sqlite':
    @event.listens_for(engine,'connect')
    def sqlite_constraints(connection,_record):
        cursor=connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=5000')
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
