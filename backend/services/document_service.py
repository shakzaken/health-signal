import hashlib
import uuid
from datetime import date
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from models.document import Document, DocumentType, ProcessingStatus
from models.lab_result import LabMarker, LabResult, MarkerStatus
from models.supplement import SupplementEntry
from models.symptom import SymptomEntry, SymptomSeverity
from models.timeline import EventType
from models.usage_event import UsageEventType
from repositories.document_repository import DocumentRepository
from repositories.ingestion_cleanup_repository import IngestionCleanupRepository
from repositories.lab_result_repository import LabResultRepository
from repositories.supplement_repository import SupplementRepository
from repositories.symptom_repository import SymptomRepository
from repositories.usage_event_repository import UsageEventRepository
from services.timeline_service import TimelineService

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DocumentRepository(session)
        self.ingestion_cleanup = IngestionCleanupRepository(session)
        self.lab_repo = LabResultRepository(session)
        self.symptom_repo = SymptomRepository(session)
        self.supplement_repo = SupplementRepository(session)
        self.timeline_service = TimelineService(session)
        self.usage_event_repo = UsageEventRepository(session)

    async def upload(
        self,
        file: UploadFile,
        document_type: DocumentType,
        source_date: date | None = None,
        user_id: str | None = None,
    ) -> Document:
        content = await file.read()
        content_hash = hashlib.sha256(content).hexdigest()

        # Reject duplicate uploads only if the existing document completed successfully.
        # If it failed or is still pending, delete the stale record and allow re-upload.
        existing = await self.repo.find_by_hash(content_hash, user_id=user_id)
        if existing:
            if existing.processing_status == ProcessingStatus.completed:
                logger.warning(f"Duplicate upload rejected — hash={content_hash} existing_id={existing.id}")
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "duplicate_document",
                        "existing_document_id": str(existing.id),
                        "message": "This file has already been uploaded.",
                    },
                )
            logger.info(f"Replacing stale document — id={existing.id} status={existing.processing_status}")
            await self.ingestion_cleanup.cleanup_failed(existing.id)

        # Save file to local filesystem
        storage_path = Path(settings.file_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = storage_path.resolve() / unique_filename  # absolute path so ai-agent can locate it

        file_path.write_bytes(content)
        logger.info(f"File saved — path={file_path} size={len(content)} bytes")

        # Create DB record
        document = Document(
            user_id=user_id,
            filename=file.filename,
            file_path=str(file_path),
            document_type=document_type,
            source_date=source_date,
            processing_status=ProcessingStatus.pending,
            content_hash=content_hash,
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
            "document_type": document.document_type.value if document.document_type else None,
            "source_date": document.source_date.isoformat() if document.source_date else None,
            "filename": document.filename,
            "user_id": str(document.user_id) if document.user_id else None,
        }
        logger.info(f"Triggering ingestion — document_id={document.id} ai_agent_url={settings.ai_agent_url}")
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(f"{settings.ai_agent_url}/ingest", json=payload)
                logger.info(f"Ingestion response — status={response.status_code}")
                result = response.json()

                new_status = ProcessingStatus.completed if result.get("success") else ProcessingStatus.failed
                detected_type = result.get("detected_document_type")
                await self.repo.update_status(document.id, new_status, detected_document_type=detected_type)
                if detected_type:
                    logger.info(f"Document type auto-detected — id={document.id} type={detected_type}")
                logger.info(f"Document status updated — id={document.id} status={new_status}")

                if new_status == ProcessingStatus.completed and document.user_id:
                    await self.usage_event_repo.record(uuid.UUID(str(document.user_id)), UsageEventType.ingestion)

                # Save structured data if the ai-agent extracted it
                if result.get("lab_result") and result["lab_result"].get("markers"):
                    await self._save_lab_result(document, result["lab_result"])
                if result.get("symptom_data") and result["symptom_data"].get("entries"):
                    await self._save_symptoms(document, result["symptom_data"])
                if result.get("supplement_data") and result["supplement_data"].get("entries"):
                    await self._save_supplements(document, result["supplement_data"])

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

            lab_name_part = f" ({lab_data['lab_name']})" if lab_data.get("lab_name") else ""
            await self.timeline_service.create_event(
                event_type=EventType.lab_result,
                reference_id=lab_result.id,
                reference_table="lab_results",
                event_date=test_date,
                summary=f"Blood test{lab_name_part}: {len(markers)} markers recorded",
            )

        except Exception as e:
            logger.error(f"Failed to save lab result — document_id={document.id} error={e}")

    async def _save_symptoms(self, document: Document, symptom_data: dict) -> None:
        """Persist symptom entries extracted by the ai-agent to PostgreSQL."""
        try:
            entries = []
            for s in symptom_data["entries"]:
                try:
                    occurred_at = date.fromisoformat(s["occurred_at"])
                except (ValueError, KeyError, TypeError):
                    occurred_at = document.source_date or date.today()

                severity = None
                if s.get("severity") in SymptomSeverity._value2member_map_:
                    severity = SymptomSeverity(s["severity"])

                entry = SymptomEntry(
                    document_id=document.id,
                    symptom_name=s["symptom_name"],
                    severity=severity,
                    occurred_at=occurred_at,
                    notes=s.get("notes"),
                )
                entries.append(entry)

            saved = await self.symptom_repo.create_entries(entries)
            logger.info(f"Symptoms saved — document_id={document.id} count={len(saved)}")

            for entry in saved:
                severity_part = f" ({entry.severity})" if entry.severity else ""
                await self.timeline_service.create_event(
                    event_type=EventType.symptom,
                    reference_id=entry.id,
                    reference_table="symptom_entries",
                    event_date=entry.occurred_at,
                    summary=f"Symptom: {entry.symptom_name}{severity_part}",
                )

        except Exception as e:
            logger.error(f"Failed to save symptoms — document_id={document.id} error={e}")

    async def _save_supplements(self, document: Document, supplement_data: dict) -> None:
        """Persist supplement entries extracted by the ai-agent to PostgreSQL."""
        try:
            entries = []
            for s in supplement_data["entries"]:
                started_at = None
                if s.get("started_at"):
                    try:
                        started_at = date.fromisoformat(s["started_at"])
                    except (ValueError, TypeError):
                        pass

                stopped_at = None
                if s.get("stopped_at"):
                    try:
                        stopped_at = date.fromisoformat(s["stopped_at"])
                    except (ValueError, TypeError):
                        pass

                entry = SupplementEntry(
                    document_id=document.id,
                    name=s["name"],
                    dosage=s["dosage"],
                    frequency=s["frequency"],
                    started_at=started_at or document.source_date,
                    stopped_at=stopped_at,
                    notes=s.get("notes"),
                )
                entries.append(entry)

            saved = await self.supplement_repo.create_entries(entries)
            logger.info(f"Supplements saved — document_id={document.id} count={len(saved)}")

            for entry in saved:
                start_date = entry.started_at or date.today()
                await self.timeline_service.create_event(
                    event_type=EventType.supplement_change,
                    reference_id=entry.id,
                    reference_table="supplement_entries",
                    event_date=start_date,
                    summary=f"Started supplement: {entry.name} {entry.dosage} {entry.frequency}",
                )
                if entry.stopped_at:
                    await self.timeline_service.create_event(
                        event_type=EventType.supplement_change,
                        reference_id=entry.id,
                        reference_table="supplement_entries",
                        event_date=entry.stopped_at,
                        summary=f"Stopped supplement: {entry.name} {entry.dosage} {entry.frequency}",
                    )

        except Exception as e:
            logger.error(f"Failed to save supplements — document_id={document.id} error={e}")
