import os # Added for path manipulation
import logging # Added for logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from matosinhosgrocery.config import settings

logger = logging.getLogger(__name__) # Added logger instance

# Log the database URL and resolved path
logger.info(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
logger.info(f"Application Current Working Directory (CWD): {os.getcwd()}")

db_path_part = settings.DATABASE_URL.split("///", 1)[-1]
if not os.path.isabs(db_path_part):
    # Ensure correct joining if db_path_part starts with ./ or not
    if db_path_part.startswith('./'):
        db_path_part = db_path_part[2:] # remove ./ for os.path.join
    absolute_db_path = os.path.abspath(os.path.join(os.getcwd(), db_path_part))
else:
    absolute_db_path = db_path_part
logger.info(f"Absolute path for DB file resolved by application: {absolute_db_path}")

# Create an asynchronous engine
# The URL is taken from our settings object
async_engine = create_async_engine(
    settings.DATABASE_URL,
    # echo=settings.DEBUG,  # Log SQL queries when DEBUG is True, useful for development
    future=True # Enables 2.0 style usage
)

# Create an asynchronous session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False, # Good default for async context managers
    future=True
)

# Base class for our ORM models
Base = declarative_base()

async def get_async_db_session() -> AsyncSession:
    """Dependency to get an async database session."""
    async_session = AsyncSessionLocal()
    try:
        yield async_session
        await async_session.commit() # Commit if all operations within the 'try' were successful
    except Exception:
        await async_session.rollback() # Rollback on any exception
        raise
    finally:
        await async_session.close()

async def create_db_and_tables():
    """This function is for initial setup or testing without Alembic.
    For production, Alembic should manage schema creation and migrations.
    """
    async with async_engine.begin() as conn:
        # In a real app, you might create specific tables if they don't exist,
        # but Base.metadata.create_all is useful for quick setup.
        # await conn.run_sync(Base.metadata.drop_all) # Optional: drop tables first
        await conn.run_sync(Base.metadata.create_all) 