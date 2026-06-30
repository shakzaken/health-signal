from pathlib import Path

from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.qdrant_client import COLLECTION_NAME, get_qdrant_client
from models.conversation import ConversationMessage, ConversationSession
from models.document import Document
from models.lab_result import LabMarker, LabResult
from models.supplement import SupplementEntry
from models.symptom import SymptomEntry
from models.timeline import TimelineEvent
from models.usage_event import UsageEvent
from models.user import User

logger = get_logger(__name__)


class UserDeletionService:
    """
    Permanently deletes a user and all their data — documents, lab results,
    symptoms, supplements, timeline events, conversations, usage events,
    uploaded files on disk, and Qdrant vectors.

    Irreversible. Callers must enforce their own confirmation step before
    invoking this (see admin route).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete(self, user: User) -> None:
        user_id = str(user.id)
        logger.info(f"Deleting user — user_id={user.id} email={user.email}")

        documents = (await self.session.execute(
            select(Document).where(Document.user_id == user_id)
        )).scalars().all()
        document_ids = [d.id for d in documents]

        lab_result_ids, symptom_ids, supplement_ids = [], [], []
        if document_ids:
            lab_result_ids = (await self.session.execute(
                select(LabResult.id).where(LabResult.document_id.in_(document_ids))
            )).scalars().all()
            symptom_ids = (await self.session.execute(
                select(SymptomEntry.id).where(SymptomEntry.document_id.in_(document_ids))
            )).scalars().all()
            supplement_ids = (await self.session.execute(
                select(SupplementEntry.id).where(SupplementEntry.document_id.in_(document_ids))
            )).scalars().all()

        if lab_result_ids:
            await self.session.execute(sa_delete(TimelineEvent).where(
                TimelineEvent.reference_table == "lab_results", TimelineEvent.reference_id.in_(lab_result_ids)
            ))
            await self.session.execute(sa_delete(LabMarker).where(LabMarker.lab_result_id.in_(lab_result_ids)))
            await self.session.execute(sa_delete(LabResult).where(LabResult.id.in_(lab_result_ids)))

        if symptom_ids:
            await self.session.execute(sa_delete(TimelineEvent).where(
                TimelineEvent.reference_table == "symptom_entries", TimelineEvent.reference_id.in_(symptom_ids)
            ))
            await self.session.execute(sa_delete(SymptomEntry).where(SymptomEntry.id.in_(symptom_ids)))

        if supplement_ids:
            await self.session.execute(sa_delete(TimelineEvent).where(
                TimelineEvent.reference_table == "supplement_entries", TimelineEvent.reference_id.in_(supplement_ids)
            ))
            await self.session.execute(sa_delete(SupplementEntry).where(SupplementEntry.id.in_(supplement_ids)))

        sessions = (await self.session.execute(
            select(ConversationSession).where(ConversationSession.user_id == user_id)
        )).scalars().all()
        session_ids = [s.session_id for s in sessions]
        if session_ids:
            await self.session.execute(sa_delete(ConversationMessage).where(ConversationMessage.session_id.in_(session_ids)))
            await self.session.execute(sa_delete(ConversationSession).where(ConversationSession.session_id.in_(session_ids)))

        await self.session.execute(sa_delete(UsageEvent).where(UsageEvent.user_id == user.id))

        for doc in documents:
            try:
                Path(doc.file_path).unlink(missing_ok=True)
            except OSError as e:
                logger.warning(f"Could not delete file {doc.file_path} — {e}")
        if document_ids:
            await self.session.execute(sa_delete(Document).where(Document.id.in_(document_ids)))

        await self.session.delete(user)
        await self.session.commit()

        self._delete_vectors(user_id)
        logger.info(f"User deleted — user_id={user_id} documents={len(documents)}")

    def _delete_vectors(self, user_id: str) -> None:
        try:
            client = get_qdrant_client()
            user_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
            count = client.count(collection_name=COLLECTION_NAME, count_filter=user_filter).count
            client.delete(collection_name=COLLECTION_NAME, points_selector=user_filter)
            logger.info(f"Deleted Qdrant vectors — user_id={user_id} count={count}")
        except Exception as e:
            logger.error(f"Failed to delete Qdrant vectors for user_id={user_id} — {e}")
