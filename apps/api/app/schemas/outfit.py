from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OutfitStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class DetectedItem(BaseModel):
    category: str
    name: str
    color: str
    material: str | None = None
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox | None = None


class StyleIssue(BaseModel):
    title: str
    detail: str
    severity: int = Field(ge=1, le=5)
    fix: str


class StyleStrength(BaseModel):
    title: str
    detail: str


class Recommendation(BaseModel):
    title: str
    reason: str
    priority: int = Field(ge=1, le=5)


class AlternateOutfit(BaseModel):
    name: str
    items: list[str]
    vibe: str


class OutfitAnalysis(BaseModel):
    style: str
    aesthetic: str
    confidence: float = Field(ge=0, le=1)
    drip_score: float = Field(ge=0, le=10)
    detected_items: list[DetectedItem]
    issues: list[StyleIssue]
    strengths: list[StyleStrength]
    roast: str
    explanation: str
    recommendations: list[Recommendation]
    alternate_outfits: list[AlternateOutfit]
    color_palette: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OutfitRecordResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    status: OutfitStatus
    image_sha256: str
    image_preview_url: str | None = None
    analysis: OutfitAnalysis | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyzeOutfitResponse(BaseModel):
    batch_id: UUID = Field(default_factory=uuid4)
    processing_mode: str
    results: list[OutfitRecordResponse]


class StyleHistoryPoint(BaseModel):
    date: datetime
    drip_score: float
    style: str
    aesthetic: str


class StyleHistoryResponse(BaseModel):
    user_id: str
    average_score: float
    best_score: float
    total_outfits: int
    dominant_styles: list[str]
    timeline: list[StyleHistoryPoint]
