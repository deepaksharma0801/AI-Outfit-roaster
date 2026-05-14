import io

import pytest
from PIL import Image

from app.core.config import Settings
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
