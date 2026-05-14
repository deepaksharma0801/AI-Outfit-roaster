import io

import pytest
from PIL import Image

from app.core.errors import ImageValidationError
from app.services.image_pipeline import ImagePipeline


def make_image() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color=(20, 40, 80)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_pipeline_compresses_valid_image() -> None:
    processed = ImagePipeline(max_upload_bytes=1_000_000).process(make_image(), "image/png")

    assert processed.mime_type == "image/jpeg"
    assert processed.width == 32
    assert processed.height == 32
    assert len(processed.sha256) == 64
    assert processed.data_url.startswith("data:image/jpeg;base64,")


def test_image_pipeline_rejects_bad_mime_type() -> None:
    with pytest.raises(ImageValidationError):
        ImagePipeline(max_upload_bytes=1_000_000).process(make_image(), "application/pdf")
