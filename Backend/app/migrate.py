from pathlib import Path
from alembic import command
from alembic.config import Config
from .database import engine

def upgrade():
    config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection']=connection
        command.upgrade(config,'head')
