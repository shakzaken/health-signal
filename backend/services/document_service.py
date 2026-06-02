import uuid
from datetime import date
from pathlib import Path

import httpx
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from models.document import Document, DocumentType, ProcessingStatus
from models.lab_result import LabMarker, LabResult, MarkerStatus
from repositories.document_repository import DocumentRepository
from repositories.lab_result_repository import LabResultRepository

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DocumentRepository(session)
        self.lab_repo = LabResultRepository(session)

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
                logger.info(f"Ingestion response — status={response.status_code}")
                result = response.json()

                new_status = ProcessingStatus.completed if result.get("success") else ProcessingStatus.failed
                await self.repo.update_status(document.id, new_status)
                logger.info(f"Document status updated — id={document.id} status={new_status}")

                # Save structured lab markers if the ai-agent extracted them
                if result.get("lab_result") and result["lab_result"].get("markers"):
                    await self._save_lab_result(document, result["lab_result"])

        except Exception as e:
            logger.error(f"Ingestion trigger failed — {e}")
            await self.repo.update_status(document.id, ProcessingStatus.failed)

    async def _save_lab_result(self, document: Document, lab_data: dict) -> None:
        """Persist structured lab markers extracted by the ai-agent to PostgreSQL."""
        try:
            # Resolve test_date: use extracted date, fall back to document source_date, then today
            test_date = None
            if lab_data.get("test_date"):
                from datetime import date as date_type
                try:
                    test_date = date_type.fromisoformat(lab_data["test_date"])
                except ValueError:
                    pass
            if test_date is None:
                test_date = document.source_date or date.today()

            lab_result = LabResult(
                document_id=document.id,
                test_date=test_date,
                lab_name=lab_data.get("lab_name"),
            )
            lab_result = await self.lab_repo.create_result(lab_result)

            markers = [
                LabMarker(
                    lab_result_id=lab_result.id,
                    name=m["name"],
                    value=m["value"],
                    unit=m["unit"],
                    reference_low=m.get("reference_low"),
                    reference_high=m.get("reference_high"),
                    status=MarkerStatus(m["status"]) if m.get("status") in MarkerStatus._value2member_map_ else None,
                )
                for m in lab_data["markers"]
            ]
            await self.lab_repo.create_markers(markers)
            logger.info(f"Lab result saved — document_id={document.id} markers={len(markers)}")

        except Exception as e:
            logger.error(f"Failed to save lab result — document_id={document.id} error={e}")
