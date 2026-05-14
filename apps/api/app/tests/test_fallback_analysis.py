import io

import pytest
from PIL import Image

from app.core.config import Settings
from app.schemas.outfit import RoastLevel
from app.services.image_pipeline import ImagePipeline
from app.services.vision import VisionAnalyzer


def make_image() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 48), color=(180, 80, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_fallback_analysis_returns_contract() -> None:
    image = ImagePipeline(max_upload_bytes=1_000_000).process(make_image(), "image/jpeg")
    analysis = await VisionAnalyzer(Settings(openai_api_key=None)).analyze(image)

    assert analysis.drip_score >= 0
    assert analysis.detected_items
    assert analysis.roast
    assert analysis.recommendations


@pytest.mark.asyncio
async def test_brutal_fallback_roast_is_stronger_than_chill() -> None:
    image = ImagePipeline(max_upload_bytes=1_000_000).process(make_image(), "image/jpeg")
    analyzer = VisionAnalyzer(Settings(openai_api_key=None))

    chill = await analyzer.analyze(image, RoastLevel.chill)
    brutal = await analyzer.analyze(image, RoastLevel.brutal)

    assert chill.roast != brutal.roast
    assert "bro" in brutal.roast.lower() or "wtf" in brutal.roast.lower()
