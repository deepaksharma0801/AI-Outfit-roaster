import json
from collections import Counter

from openai import AsyncOpenAI
from PIL import Image

from app.core.config import Settings
from app.schemas.outfit import (
    AlternateOutfit,
    DetectedItem,
    OutfitAnalysis,
    Recommendation,
    RoastLevel,
    StyleIssue,
    StyleStrength,
)
from app.services.image_pipeline import ProcessedImage


SYSTEM_PROMPT = """You are DripJudge AI, a multimodal fashion critic.
Analyze the outfit with useful styling intelligence and internet-native roast comedy.
Return only valid JSON matching the requested schema.
The roast may be savage, direct, and slangy, but it must only attack the outfit, styling choices,
colors, proportions, layering, accessories, and overall vibe.
Never body-shame. Never insult protected classes, age, race, gender, disability, religion, sexuality,
body type, poverty, or the person wearing the clothes. No sexual comments."""


ROAST_GUIDES = {
    RoastLevel.chill: (
        "Roast level: CHILL. Keep it playful and useful. One clever jab, no profanity. "
        "The roast should feel like a stylish friend nudging them."
    ),
    RoastLevel.spicy: (
        "Roast level: SPICY. TikTok comment energy. Be sharper, punchier, and more meme-aware. "
        "A little 'bro' energy is welcome, but keep it outfit-only."
    ),
    RoastLevel.brutal: (
        "Roast level: BRUTAL. The user asked for damage. Use direct lines like 'bro what is this fit' "
        "or 'this outfit is fighting for its life' when appropriate. Be funny, harsh, and specific. "
        "Profanity is allowed sparingly. Still outfit-only, no body or identity insults."
    ),
    RoastLevel.nuclear: (
        "Roast level: NUCLEAR. Maximum comedy violence toward the clothes. Make it quotable, ruthless, "
        "and short enough to screenshot. Profanity is allowed sparingly. Still outfit-only, no body or "
        "identity insults."
    ),
}

FALLBACK_ROASTS = {
    RoastLevel.chill: {
        "low_contrast": "This fit is trying to whisper, but the room is already silent.",
        "high_contrast": "The outfit has energy, it just needs a manager before it starts yelling.",
        "dark": "This look has stealth mode unlocked, but somebody forgot to add the plot.",
        "bright": "The fit is cheerful, but it is one accent away from looking accidentally loud.",
    },
    RoastLevel.spicy: {
        "low_contrast": "Bro this fit has airplane-mode confidence. It exists, but it is not connecting.",
        "high_contrast": "This outfit walked in with main-character music and tripped over the beat.",
        "dark": "This is not mysterious, this is laundry basket noir.",
        "bright": "The palette said 'trust the process' and then left the group chat.",
    },
    RoastLevel.brutal: {
        "low_contrast": "Bro what is this fit, a loading screen with shoes? The outfit is giving default settings.",
        "high_contrast": "Bro this fit got dressed by spinning a wheel and losing twice. The colors are beefing in public.",
        "dark": "Wtf is this outfit, undercover couch-core? It looks like the closet rage-quit halfway through.",
        "bright": "This fit is loud for no reason, like it learned color theory from a warning label.",
    },
    RoastLevel.nuclear: {
        "low_contrast": "Bro this outfit has the charisma of an unseasoned screenshot. Delete the draft and respawn.",
        "high_contrast": "Wtf is that outfit, every piece is arguing and somehow they are all losing.",
        "dark": "This fit looks like it got assembled during a power outage and nobody checked the footage.",
        "bright": "This outfit is a visual jump scare. The palette is committing crimes with confidence.",
    },
}


JSON_SCHEMA = {
    "name": "outfit_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "style": {"type": "string"},
            "aesthetic": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "drip_score": {"type": "number", "minimum": 0, "maximum": 10},
            "detected_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string"},
                        "name": {"type": "string"},
                        "color": {"type": "string"},
                        "material": {"type": ["string", "null"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "bbox": {
                            "type": ["object", "null"],
                            "additionalProperties": False,
                            "properties": {
                                "x": {"type": "number", "minimum": 0, "maximum": 1},
                                "y": {"type": "number", "minimum": 0, "maximum": 1},
                                "width": {"type": "number", "minimum": 0, "maximum": 1},
                                "height": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                            "required": ["x", "y", "width", "height"],
                        },
                    },
                    "required": ["category", "name", "color", "material", "confidence", "bbox"],
                },
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "severity": {"type": "integer", "minimum": 1, "maximum": 5},
                        "fix": {"type": "string"},
                    },
                    "required": ["title", "detail", "severity", "fix"],
                },
            },
            "strengths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["title", "detail"],
                },
            },
            "roast": {"type": "string"},
            "explanation": {"type": "string"},
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                    "required": ["title", "reason", "priority"],
                },
            },
            "alternate_outfits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                        "vibe": {"type": "string"},
                    },
                    "required": ["name", "items", "vibe"],
                },
            },
            "color_palette": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "style",
            "aesthetic",
            "confidence",
            "drip_score",
            "detected_items",
            "issues",
            "strengths",
            "roast",
            "explanation",
            "recommendations",
            "alternate_outfits",
            "color_palette",
            "tags",
        ],
    },
}


class VisionAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def analyze(self, image: ProcessedImage, roast_level: RoastLevel = RoastLevel.brutal) -> OutfitAnalysis:
        if not self.client:
            return self._fallback_analysis(image, roast_level)

        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.72 if roast_level in {RoastLevel.brutal, RoastLevel.nuclear} else 0.52,
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this outfit for detected garments, style, aesthetic consistency, "
                                "colors, fit coordination, accessories, layering, mistakes, strengths, "
                                "a roast, and practical upgrade recommendations. "
                                f"{ROAST_GUIDES[roast_level]} "
                                "Make the roast one to two sentences max, brutally specific to the visible outfit, "
                                "then keep the explanation and recommendations genuinely useful."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image.data_url}},
                    ],
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        return OutfitAnalysis.model_validate(json.loads(content))

    def _fallback_analysis(self, image: ProcessedImage, roast_level: RoastLevel = RoastLevel.brutal) -> OutfitAnalysis:
        palette = self._dominant_palette(image.content)
        brightness = self._palette_brightness(palette)
        contrast = self._palette_contrast(palette)
        style = "streetwear" if contrast > 80 else "minimal casual"
        aesthetic = "clean-core" if brightness > 125 else "soft techwear"
        score = min(9.1, max(5.6, 6.4 + contrast / 120 + (abs(brightness - 128) / 180)))
        roast_key = self._roast_key(brightness, contrast)

        return OutfitAnalysis(
            style=style,
            aesthetic=aesthetic,
            confidence=0.74,
            drip_score=round(score, 1),
            detected_items=[
                DetectedItem(category="top", name="primary upper layer", color=palette[0], confidence=0.68),
                DetectedItem(category="bottom", name="coordinating lower layer", color=palette[1], confidence=0.62),
                DetectedItem(category="shoes", name="visible footwear silhouette", color=palette[-1], confidence=0.55),
            ],
            issues=[
                StyleIssue(
                    title="Silhouette needs one clearer anchor",
                    detail="The outfit reads cohesive, but the proportions could use a stronger hero piece.",
                    severity=2,
                    fix="Add a structured jacket, cropped layer, or cleaner shoe shape to create a focal point.",
                ),
                StyleIssue(
                    title="Accessory story is quiet",
                    detail="The base fit is doing the group project while accessories are on read.",
                    severity=2,
                    fix="Try a watch, cap, bag, jewelry, or a single statement texture.",
                ),
            ],
            strengths=[
                StyleStrength(
                    title="Palette has control",
                    detail="The dominant colors are not fighting for custody of the mirror.",
                ),
                StyleStrength(
                    title="Wearable base",
                    detail="The outfit has enough restraint to be styled up without rebuilding from zero.",
                ),
            ],
            roast=FALLBACK_ROASTS[roast_level][roast_key],
            explanation=(
                "The outfit works as a practical base. To make it memorable, sharpen one variable: "
                "silhouette, texture, color contrast, or accessories."
            ),
            recommendations=[
                Recommendation(
                    title="Add one high-intent layer",
                    reason="A structured outer layer gives the outfit a deliberate shape instead of a default loadout.",
                    priority=5,
                ),
                Recommendation(
                    title="Repeat one accent color",
                    reason="Echoing a color in shoes, cap, or bag makes the look feel styled instead of accidental.",
                    priority=4,
                ),
                Recommendation(
                    title="Upgrade texture contrast",
                    reason="Mix matte, ribbed, denim, leather, or nylon textures to add depth on camera.",
                    priority=3,
                ),
            ],
            alternate_outfits=[
                AlternateOutfit(
                    name="Streetwear patch",
                    items=["boxy overshirt", "straight-leg denim", "clean sneakers", "small crossbody bag"],
                    vibe="more intentional, less laundry-day roulette",
                ),
                AlternateOutfit(
                    name="Smart casual patch",
                    items=["ribbed knit", "tailored trouser", "minimal leather sneaker", "silver watch"],
                    vibe="date-night polish without trying too loudly",
                ),
            ],
            color_palette=palette,
            tags=[style, aesthetic, "camera-ready", "upgradeable", f"roast:{roast_level.value}"],
        )

    def _roast_key(self, brightness: float, contrast: float) -> str:
        if contrast > 95:
            return "high_contrast"
        if contrast < 45:
            return "low_contrast"
        if brightness < 105:
            return "dark"
        return "bright"

    def _dominant_palette(self, image_bytes: bytes) -> list[str]:
        image = Image.open(__import__("io").BytesIO(image_bytes)).convert("RGB")
        image.thumbnail((80, 80))
        pixels = list(image.getdata())
        buckets: Counter[tuple[int, int, int]] = Counter(
            ((r // 32) * 32, (g // 32) * 32, (b // 32) * 32) for r, g, b in pixels
        )
        colors = [self._hex(rgb) for rgb, _ in buckets.most_common(5)]
        fallback = ["#1f2937", "#f9fafb", "#737373", "#7de2d1", "#ff6f61"]
        return (colors + fallback)[:5]

    def _palette_brightness(self, palette: list[str]) -> float:
        values = []
        for color in palette:
            r, g, b = self._rgb(color)
            values.append((r * 299 + g * 587 + b * 114) / 1000)
        return sum(values) / max(len(values), 1)

    def _palette_contrast(self, palette: list[str]) -> float:
        brightness = []
        for color in palette:
            r, g, b = self._rgb(color)
            brightness.append((r + g + b) / 3)
        return max(brightness) - min(brightness) if brightness else 0

    def _hex(self, rgb: tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _rgb(self, color: str) -> tuple[int, int, int]:
        normalized = color.lstrip("#")
        return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
