from collections import Counter
from datetime import datetime
from uuid import UUID

from app.schemas.outfit import OutfitAnalysis, OutfitRecordResponse, OutfitStatus, StyleHistoryPoint, StyleHistoryResponse


class StyleHistoryStore:
    """Small in-process store for local demos; production swaps this for Postgres."""

    def __init__(self) -> None:
        self._records: list[OutfitRecordResponse] = []

    def add(
        self,
        *,
        record_id: UUID,
        user_id: str,
        image_sha256: str,
        analysis: OutfitAnalysis,
        image_preview_url: str | None = None,
        created_at: datetime | None = None,
    ) -> OutfitRecordResponse:
        record = OutfitRecordResponse(
            id=record_id,
            user_id=user_id,
            status=OutfitStatus.completed,
            image_sha256=image_sha256,
            image_preview_url=image_preview_url,
            analysis=analysis,
            created_at=created_at or datetime.utcnow(),
        )
        self._records.insert(0, record)
        return record

    def list(self, user_id: str, limit: int = 20) -> list[OutfitRecordResponse]:
        return [record for record in self._records if record.user_id == user_id][:limit]

    def summary(self, user_id: str) -> StyleHistoryResponse:
        records = [record for record in self._records if record.user_id == user_id and record.analysis]
        if not records:
            return StyleHistoryResponse(
                user_id=user_id,
                average_score=0,
                best_score=0,
                total_outfits=0,
                dominant_styles=[],
                timeline=[],
            )

        scores = [record.analysis.drip_score for record in records if record.analysis]
        styles = Counter(record.analysis.style for record in records if record.analysis)
        timeline = [
            StyleHistoryPoint(
                date=record.created_at,
                drip_score=record.analysis.drip_score,
                style=record.analysis.style,
                aesthetic=record.analysis.aesthetic,
            )
            for record in reversed(records)
            if record.analysis
        ]

        return StyleHistoryResponse(
            user_id=user_id,
            average_score=round(sum(scores) / len(scores), 1),
            best_score=max(scores),
            total_outfits=len(records),
            dominant_styles=[style for style, _ in styles.most_common(4)],
            timeline=timeline,
        )


style_history_store = StyleHistoryStore()
