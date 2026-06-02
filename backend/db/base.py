from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared SQLAlchemy declarative base.
    All ORM models inherit from this class.
    """
    pass
