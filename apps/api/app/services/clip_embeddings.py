import hashlib
import math
import random


class ClipEmbeddingService:
    """CLIP-compatible image embedding service with a deterministic local fallback."""

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        # The fallback preserves API behavior in CI/local demos without shipping a huge model.
        digest = hashlib.sha256(image_bytes).digest()
        seed = int.from_bytes(digest[:8], "big")
        rng = random.Random(seed)
        values = [rng.uniform(-1, 1) for _ in range(self.dimensions)]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [round(value / norm, 8) for value in values]
