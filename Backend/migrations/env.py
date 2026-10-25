from alembic import context
from app.database import engine, Base
from app.models import db_models
config=context.config

def run(connection):
    context.configure(connection=connection,target_metadata=Base.metadata,render_as_batch=connection.dialect.name=='sqlite',compare_type=True)
    with context.begin_transaction(): context.run_migrations()
if context.is_offline_mode():
    from app.config import DATABASE_URL
    context.configure(url=DATABASE_URL,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction(): context.run_migrations()
else:
    supplied=config.attributes.get('connection')
    if supplied is not None: run(supplied)
    else:
        with engine.connect() as connection: run(connection)
