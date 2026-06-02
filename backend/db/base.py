from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared SQLAlchemy declarative base.
    All ORM models inherit from this class.
    Import this module (and all model modules) in alembic/env.py
    so Alembic can detect table changes during autogenerate.
    """
    pass


# Import all models here so Alembic can see them during autogenerate.
# Keep this at the bottom to avoid circular imports.
from models.document import Document  # noqa: F401, E402
from models.lab_result import LabMarker, LabResult  # noqa: F401, E402
from models.supplement import SupplementEntry  # noqa: F401, E402
from models.symptom import SymptomEntry  # noqa: F401, E402
from models.timeline import TimelineEvent  # noqa: F401, E402
