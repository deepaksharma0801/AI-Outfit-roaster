from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutfitRecord
from app.schemas.outfit import OutfitAnalysis, OutfitRecordResponse, OutfitStatus, StyleHistoryResponse
from app.services.style_history import StyleHistoryStore

DATABASE_FALLBACK_ERRORS = (SQLAlchemyError, OSError, ConnectionError)


class OutfitRepository:
    def __init__(self, session: AsyncSession, fallback: StyleHistoryStore) -> None:
        self.session = session
        self.fallback = fallback

    async def add_completed(
        self,
        *,
        record_id: UUID,
        user_id: str,
        image_sha256: str,
        image_preview_url: str | None,
        analysis: OutfitAnalysis,
        embedding: list[float],
    ) -> OutfitRecordResponse:
        try:
            record = OutfitRecord(
                id=record_id,
                user_id=user_id,
                image_sha256=image_sha256,
                storage_url=image_preview_url,
                status=OutfitStatus.completed.value,
                style=analysis.style,
                aesthetic=analysis.aesthetic,
                confidence=analysis.confidence,
                drip_score=analysis.drip_score,
                analysis=analysis.model_dump(mode="json"),
                embedding=embedding,
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
            response = self._to_response(record)
            self.fallback.add(
                record_id=response.id,
                user_id=response.user_id,
                image_sha256=response.image_sha256,
                image_preview_url=response.image_preview_url,
                analysis=analysis,
                created_at=response.created_at,
            )
            return response
        except DATABASE_FALLBACK_ERRORS:
            await self.session.rollback()
            return self.fallback.add(
                record_id=record_id,
                user_id=user_id,
                image_sha256=image_sha256,
                image_preview_url=image_preview_url,
                analysis=analysis,
            )

    async def list(self, user_id: str, limit: int = 20) -> list[OutfitRecordResponse]:
        try:
            statement = (
                select(OutfitRecord)
                .where(OutfitRecord.user_id == user_id)
                .order_by(OutfitRecord.created_at.desc())
                .limit(limit)
            )
            rows = (await self.session.scalars(statement)).all()
            if rows:
                return [self._to_response(row) for row in rows]
        except DATABASE_FALLBACK_ERRORS:
            await self.session.rollback()

        return self.fallback.list(user_id=user_id, limit=limit)

    async def summary(self, user_id: str) -> StyleHistoryResponse:
        records = await self.list(user_id=user_id, limit=100)
        if records:
            shadow = StyleHistoryStore()
            for record in reversed(records):
                if record.analysis:
                    shadow.add(
                        record_id=record.id,
                        user_id=record.user_id,
                        image_sha256=record.image_sha256,
                        image_preview_url=record.image_preview_url,
                        analysis=record.analysis,
                        created_at=record.created_at,
                    )
            return shadow.summary(user_id)

        return self.fallback.summary(user_id)

    def _to_response(self, record: OutfitRecord) -> OutfitRecordResponse:
        analysis = OutfitAnalysis.model_validate(record.analysis) if record.analysis else None
        return OutfitRecordResponse(
            id=record.id,
            user_id=record.user_id,
            status=OutfitStatus(record.status),
            image_sha256=record.image_sha256,
            image_preview_url=record.storage_url,
            analysis=analysis,
            created_at=record.created_at,
        )
