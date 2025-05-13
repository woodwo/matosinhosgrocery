import os
import sys
from logging.config import fileConfig
import sqlite3 # Import sqlite3 for direct DB inspection

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# This line makes the src directory available for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import your Base and settings
from matosinhosgrocery.database.models import Base # Adjusted import for your models
from matosinhosgrocery.config import settings as app_settings # Your application settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata # Use your imported Base

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def list_tables_in_db(db_url_str: str):
    """Connects to the SQLite DB using sqlite3 and lists tables."""
    print(f"[DEBUG HOOK] Attempting to list tables for DB URL: {db_url_str}")
    if not db_url_str.startswith("sqlite:///"):
        print(f"[DEBUG HOOK] DB URL '{db_url_str}' is not a recognized SQLite URL for direct connection. Skipping table list.")
        return

    # Derive path from sqlite:///./file.db or sqlite:///absolute/path/file.db
    db_path = db_url_str[len("sqlite:///"):]
    if db_path.startswith("./"):
        # Resolve relative path from the directory of alembic.ini (project root)
        # This assumes alembic commands are run from the project root where alembic.ini is.
        project_root = os.path.dirname(config.config_file_name) if config.config_file_name else os.getcwd()
        db_path = os.path.abspath(os.path.join(project_root, db_path[2:]))
    
    print(f"[DEBUG HOOK] Resolved DB path for sqlite3: {db_path}")

    if not os.path.exists(db_path):
        print(f"[DEBUG HOOK] Database file {db_path} does not exist before connecting.")
        # This is expected if Alembic is creating it for the first time.

    conn = None
    try:
        conn = sqlite3.connect(db_path) # Use the resolved path
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            print(f"[DEBUG HOOK] Tables found in {db_path}: {tables}")
        else:
            print(f"[DEBUG HOOK] No tables found in {db_path} (it might be empty or new).")
    except sqlite3.Error as e:
        print(f"[DEBUG HOOK] SQLite error while trying to list tables in {db_path}: {e}")
    finally:
        if conn:
            conn.close()

def get_url():
    """Return the database URL.
    If -x url=... is passed to alembic, that is used.
    Otherwise, it falls back to app_settings.DATABASE_URL.
    """
    # Get URL from -x url= argument if present
    cmd_line_url = context.get_x_argument(as_dictionary=True).get('url')
    if cmd_line_url:
        print(f"[DEBUG HOOK] Using URL from command line: {cmd_line_url}")
        # If it's an async URL, convert it for sync Alembic operations
        if cmd_line_url.startswith("sqlite+aiosqlite"):
            return cmd_line_url.replace("sqlite+aiosqlite", "sqlite")
        return cmd_line_url

    # Fallback to application settings if no command-line URL
    db_url = app_settings.DATABASE_URL
    print(f"[DEBUG HOOK] Using URL from app_settings: {db_url}")
    if db_url.startswith("sqlite+aiosqlite"):
        return db_url.replace("sqlite+aiosqlite", "sqlite")
    return db_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    # Call the debug hook here as well for completeness, though offline is less common for this issue
    list_tables_in_db(url) 
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable_url = get_url()
    
    # List tables before connecting with SQLAlchemy engine
    list_tables_in_db(connectable_url)

    # Create engine configuration based on this URL
    # We pass it as a dict to engine_from_config to avoid issues if it contains % chars
    # that might be misinterpreted by configparser if read directly from alembic.ini
    # by engine_from_config.
    conf = config.get_section(config.config_ini_section, {})
    conf['sqlalchemy.url'] = connectable_url

    connectable = engine_from_config(
        conf, # Use our dynamically configured section
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
