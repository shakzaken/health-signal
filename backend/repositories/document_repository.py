import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, ProcessingStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Document]:
        result = await self.session.execute(
            select(Document).order_by(Document.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: ProcessingStatus,
        raw_text: Optional[str] = None,
    ) -> Optional[Document]:
        document = await self.get_by_id(document_id)
        if not document:
            return None
        document.processing_status = status
        if raw_text is not None:
            document.raw_text = raw_text
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document
