import base64
import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ImageValidationError


SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    sha256: str
    width: int
    height: int
    mime_type: str

    @property
    def data_url(self) -> str:
        encoded = base64.b64encode(self.content).decode("ascii")
        return f"data:{self.mime_type};base64,{encoded}"


class ImagePipeline:
    def __init__(self, max_upload_bytes: int, max_side: int = 1600, jpeg_quality: int = 86) -> None:
        self.max_upload_bytes = max_upload_bytes
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality

    def process(self, content: bytes, content_type: str | None) -> ProcessedImage:
        if not content:
            raise ImageValidationError("Upload was empty.")

        if len(content) > self.max_upload_bytes:
            raise ImageValidationError("Image is too large for the configured upload limit.")

        if content_type not in SUPPORTED_MIME_TYPES:
            raise ImageValidationError("Unsupported image type. Use JPEG, PNG, or WebP.")

        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
            image = Image.open(io.BytesIO(content))
        except (UnidentifiedImageError, OSError) as exc:
            raise ImageValidationError("Could not read the uploaded image.") from exc

        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((self.max_side, self.max_side))

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=self.jpeg_quality, optimize=True)
        compressed = output.getvalue()

        return ProcessedImage(
            content=compressed,
            sha256=hashlib.sha256(compressed).hexdigest(),
            width=image.width,
            height=image.height,
            mime_type="image/jpeg",
        )
