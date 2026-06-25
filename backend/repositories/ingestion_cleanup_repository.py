import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.lab_result import LabMarker, LabResult
from models.supplement import SupplementEntry
from models.symptom import SymptomEntry


class IngestionCleanupRepository:
    """
    Removes a document and all its derived data from the database.

    THIS IS THE ONLY LEGITIMATE USE OF DOCUMENT DELETION IN THIS CODEBASE.

    Purpose: when a document upload fails during ingestion and the user
    re-uploads the same file, the stale failed record must be wiped before
    the new ingestion run begins. This prevents duplicate records and allows
    the pipeline to start clean.

    Do NOT use this for user-initiated deletion — users cannot delete documents.
    Do NOT use this for any purpose other than replacing a failed ingestion record.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def cleanup_failed(self, document_id: uuid.UUID) -> None:
        """Delete a failed document record and all its partially-ingested child rows."""
        document = (
            await self._session.execute(
                select(Document).where(Document.id == document_id)
            )
        ).scalar_one_or_none()

        if not document:
            return

        lab_result_ids = (
            await self._session.execute(
                select(LabResult.id).where(LabResult.document_id == document_id)
            )
        ).scalars().all()

        if lab_result_ids:
            await self._session.execute(
                sa_delete(LabMarker).where(LabMarker.lab_result_id.in_(lab_result_ids))
            )
        await self._session.execute(
            sa_delete(LabResult).where(LabResult.document_id == document_id)
        )
        await self._session.execute(
            sa_delete(SymptomEntry).where(SymptomEntry.document_id == document_id)
        )
        await self._session.execute(
            sa_delete(SupplementEntry).where(SupplementEntry.document_id == document_id)
        )
        await self._session.delete(document)
        await self._session.commit()
