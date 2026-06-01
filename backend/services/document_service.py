import uuid
from datetime import date
from pathlib import Path

import httpx
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.document import Document, DocumentType, ProcessingStatus
from repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DocumentRepository(session)

    async def upload(
        self,
        file: UploadFile,
        document_type: DocumentType,
        source_date: date | None = None,
    ) -> Document:
        # Save file to local filesystem
        storage_path = Path(settings.file_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = storage_path / unique_filename

        content = await file.read()
        file_path.write_bytes(content)

        # Create DB record
        document = Document(
            filename=file.filename,
            file_path=str(file_path),
            document_type=document_type,
            source_date=source_date,
            processing_status=ProcessingStatus.pending,
        )
        document = await self.repo.create(document)

        # Trigger ingestion in ai-agent (fire and forget errors are caught)
        await self._trigger_ingestion(document)

        return document

    async def _trigger_ingestion(self, document: Document) -> None:
        payload = {
            "document_id": str(document.id),
            "file_path": document.file_path,
            "document_type": document.document_type.value,
            "source_date": document.source_date.isoformat() if document.source_date else None,
        }
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                await client.post(f"{settings.ai_agent_url}/ingest", json=payload)
        except Exception:
            # Ingestion is async — status will reflect failure via ai-agent callback
            pass
