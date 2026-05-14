from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ImageValidationError, bad_upload
from app.db.session import get_db
from app.schemas.outfit import (
    AnalyzeOutfitResponse,
    OutfitRecordResponse,
    OutfitStatus,
    RoastLevel,
    StyleHistoryResponse,
)
from app.services.clip_embeddings import ClipEmbeddingService
from app.services.image_pipeline import ImagePipeline
from app.services.outfit_repository import OutfitRepository
from app.services.style_graph import OutfitAnalysisGraph
from app.services.style_history import style_history_store
from app.services.vision import VisionAnalyzer


router = APIRouter()
settings = get_settings()
image_pipeline = ImagePipeline(max_upload_bytes=settings.max_upload_bytes)
analysis_graph = OutfitAnalysisGraph(
    analyzer=VisionAnalyzer(settings),
    embeddings=ClipEmbeddingService(settings.clip_embedding_dimensions),
)


@router.post("/outfits/analyze", response_model=AnalyzeOutfitResponse, tags=["outfits"])
async def analyze_outfits(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="One or more outfit images.")],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str, Form()] = "demo-user",
    async_processing: Annotated[bool, Form()] = False,
    roast_level: Annotated[RoastLevel, Form()] = RoastLevel.brutal,
) -> AnalyzeOutfitResponse:
    batch_id = uuid4()
    results: list[OutfitRecordResponse] = []
    repository = OutfitRepository(db, style_history_store)

    for upload in files:
        raw = await upload.read()
        try:
            processed = image_pipeline.process(raw, upload.content_type)
        except ImageValidationError as exc:
            raise bad_upload(str(exc)) from exc

        record_id = uuid4()
        preview_url = processed.data_url

        if async_processing:
            queued = OutfitRecordResponse(
                id=record_id,
                user_id=user_id,
                status=OutfitStatus.queued,
                image_sha256=processed.sha256,
                image_preview_url=preview_url,
            )
            background_tasks.add_task(_process_background, record_id, user_id, processed, roast_level)
            results.append(queued)
            continue

        analysis, embedding = await analysis_graph.run(processed, roast_level)
        results.append(
            await repository.add_completed(
                record_id=record_id,
                user_id=user_id,
                image_sha256=processed.sha256,
                image_preview_url=preview_url,
                analysis=analysis,
                embedding=embedding,
            )
        )

    return AnalyzeOutfitResponse(
        batch_id=batch_id,
        processing_mode="async" if async_processing else "sync",
        results=results,
    )


@router.get("/outfits/history", response_model=list[OutfitRecordResponse], tags=["outfits"])
async def list_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Query(default="demo-user"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OutfitRecordResponse]:
    return await OutfitRepository(db, style_history_store).list(user_id=user_id, limit=limit)


@router.get("/style/history", response_model=StyleHistoryResponse, tags=["style"])
async def get_style_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Query(default="demo-user"),
) -> StyleHistoryResponse:
    return await OutfitRepository(db, style_history_store).summary(user_id)


async def _process_background(record_id, user_id: str, processed, roast_level: RoastLevel) -> None:
    analysis, _embedding = await analysis_graph.run(processed, roast_level)
    style_history_store.add(
        record_id=record_id,
        user_id=user_id,
        image_sha256=processed.sha256,
        image_preview_url=processed.data_url,
        analysis=analysis,
    )
