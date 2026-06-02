import uuid
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

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
        result = await self.session.exec(
            select(Document).where(Document.id == document_id)
        )
        return result.first()

    async def list_all(self) -> list[Document]:
        result = await self.session.exec(select(Document).order_by(Document.uploaded_at.desc()))
        return list(result.all())

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
