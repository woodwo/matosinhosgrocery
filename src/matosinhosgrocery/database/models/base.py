from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import as_declarative, declared_attr

from matosinhosgrocery.database.connection import Base # Re-export Base

# You could also define a new Base here if you prefer, e.g.:
# @as_declarative()
# class Base:
#     id: Any
#     __name__: str
#     # Generate __tablename__ automatically
#     @declared_attr
#     def __tablename__(cls) -> str:
#         return cls.__name__.lower()

class TimestampMixin:
    """Mixin to add created_at and updated_at timestamp columns to models."""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

# If you want all your models to have an integer primary key named 'id' by default:
# class ModelWithID(Base):
#     __abstract__ = True # Ensures this class itself doesn't create a table
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)

# For now, we'll just re-export the Base from connection.py and provide the TimestampMixin.
# Individual models will define their own 'id' columns. 