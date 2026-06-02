import uuid
from datetime import date
from pathlib import Path

import httpx
from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings
from core.logger import get_logger
from models.document import Document, DocumentType, ProcessingStatus
from repositories.document_repository import DocumentRepository

logger = get_logger(__name__)


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
        file_path = storage_path.resolve() / unique_filename  # absolute path so ai-agent can locate it

        content = await file.read()
        file_path.write_bytes(content)
        logger.info(f"File saved — path={file_path} size={len(content)} bytes")

        # Create DB record
        document = Document(
            filename=file.filename,
            file_path=str(file_path),
            document_type=document_type,
            source_date=source_date,
            processing_status=ProcessingStatus.pending,
        )
        document = await self.repo.create(document)
        logger.info(f"Document record created — id={document.id}")

        # Trigger ingestion in ai-agent
        await self._trigger_ingestion(document)

        return document

    async def _trigger_ingestion(self, document: Document) -> None:
        payload = {
            "document_id": str(document.id),
            "file_path": document.file_path,
            "document_type": document.document_type.value,
            "source_date": document.source_date.isoformat() if document.source_date else None,
            "filename": document.filename,
        }
        logger.info(f"Triggering ingestion — document_id={document.id} ai_agent_url={settings.ai_agent_url}")
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(f"{settings.ai_agent_url}/ingest", json=payload)
                logger.info(f"Ingestion response — status={response.status_code} body={response.text}")
                result = response.json()
                new_status = ProcessingStatus.completed if result.get("success") else ProcessingStatus.failed
                await self.repo.update_status(document.id, new_status)
                logger.info(f"Document status updated — id={document.id} status={new_status}")
        except Exception as e:
            logger.error(f"Ingestion trigger failed — {e}")
            await self.repo.update_status(document.id, ProcessingStatus.failed)
