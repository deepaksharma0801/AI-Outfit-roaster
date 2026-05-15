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
Outfit-only humiliation is allowed: make the clothes feel roasted, exposed, and embarrassed.
Do not soften Brutal or Nuclear mode with polite phrasing.
Never body-shame. Never insult protected classes, age, race, gender, disability, religion, sexuality,
body type, poverty, or the person wearing the clothes. No sexual comments."""

SPECIFICITY_INSTRUCTIONS = (
    "Be picture-specific. The roast must call out at least one visible garment or accessory with its color, "
    "material, placement, or shape, like 'that gray coat', 'the black hoodie', 'those white sneakers', "
    "or 'the watch fighting for attention'. Do not give generic advice such as 'try a watch' if a watch, "
    "bracelet, bag, cap, jewelry, or other accessory is already visible. If an accessory is visible, acknowledge "
    "it and explain whether it helps or makes the fit worse. Every issue and recommendation must reference a "
    "visible detail from the photo. If you are uncertain about the item type, say 'upper layer', 'outer layer', "
    "'pants', 'shoes', or 'visible accessory' rather than inventing a wrong item."
)


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
        "Roast level: BRUTAL. The user asked for damage. Be rude to the clothes, not the person. "
        "Use direct lines like 'bro what is that hoodie', 'take that coat off', or 'this fit is fighting "
        "for its life' when appropriate. Make it funny, harsh, specific, and a little painful. "
        "Profanity is allowed sparingly. Still outfit-only, no body or identity insults."
    ),
    RoastLevel.nuclear: (
        "Roast level: NUCLEAR. Maximum comedy violence toward the clothes. Make it feel like a comment "
        "section public execution of the outfit: quotable, ruthless, and short enough to screenshot. "
        "Use 'wtf', 'bro', 'take it off', 'delete the evidence', or similar phrasing when it fits. "
        "Profanity is allowed sparingly. Still outfit-only, no body or identity insults."
    ),
}

FALLBACK_ROASTS = {
    RoastLevel.chill: {
        "low_contrast": "That {top_color} upper layer is trying to whisper, but the whole fit is already silent.",
        "high_contrast": "The {top_color} top and {accent_color} accents have energy, they just need a manager.",
        "dark": "That {top_color} upper layer has stealth mode unlocked, but somebody forgot to add the plot.",
        "bright": "That {top_color} top layer is cheerful, but the fit is one decision away from looking accidental.",
    },
    RoastLevel.spicy: {
        "low_contrast": "Bro that {top_color} upper layer has airplane-mode confidence. It exists, but it is not connecting.",
        "high_contrast": "That {top_color} layer and {accent_color} contrast walked in with main-character music and tripped over the beat.",
        "dark": "That {top_color} top layer is not mysterious, it is laundry-basket noir.",
        "bright": "That {top_color} layer said 'trust the process' and then left the group chat.",
    },
    RoastLevel.brutal: {
        "low_contrast": "Bro what is that {top_color} upper-layer situation, a loading screen with sleeves? Take it off before the mirror files a complaint.",
        "high_contrast": "Bro that {top_color} layer next to {accent_color} looks like two bad decisions fighting for the camera. The fit lost in every direction.",
        "dark": "Wtf is that {top_color} upper layer, undercover couch-core? Take it off, the closet clearly rage-quit halfway through.",
        "bright": "That {top_color} layer is loud for no reason, like a warning label got promoted to stylist. The fit needs an apology note.",
    },
    RoastLevel.nuclear: {
        "low_contrast": "Bro that {top_color} upper layer is fashion bankruptcy with sleeves. Take it off, delete the evidence, and let the closet apologize.",
        "high_contrast": "Wtf is that {top_color} layer doing next to {accent_color}? Every piece is arguing, the outfit is losing, and the camera deserves compensation.",
        "dark": "That {top_color} top layer looks like it got assembled during a power outage and rejected by lost-and-found. Take it off and let the fit breathe.",
        "bright": "That {top_color} layer is a visual jump scare. The palette is committing crimes with confidence and somehow still has no drip.",
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
                                f"{SPECIFICITY_INSTRUCTIONS} "
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
        top_color = self._color_name(palette[0])
        accent_color = self._color_name(palette[-1])
        roast = FALLBACK_ROASTS[roast_level][roast_key].format(
            top_color=top_color,
            accent_color=accent_color,
        )

        return OutfitAnalysis(
            style=style,
            aesthetic=aesthetic,
            confidence=0.74,
            drip_score=round(score, 1),
            detected_items=[
                DetectedItem(category="top", name=f"{top_color} upper layer", color=palette[0], confidence=0.68),
                DetectedItem(category="bottom", name=f"{self._color_name(palette[1])} lower layer", color=palette[1], confidence=0.62),
                DetectedItem(category="shoes", name=f"{accent_color} footwear shape", color=palette[-1], confidence=0.55),
            ],
            issues=[
                StyleIssue(
                    title=f"That {top_color} layer needs a cleaner job",
                    detail=(
                        f"The visible {top_color} upper layer is carrying the fit, but it does not create a sharp "
                        "enough silhouette or point of view."
                    ),
                    severity=2,
                    fix="Either make that top layer more structured or swap it for an outer layer with a cleaner shape.",
                ),
                StyleIssue(
                    title="Visible details need to stop freeloading",
                    detail=(
                        "Any visible accessory or small detail should look intentional, not like it wandered into "
                        "the photo by accident."
                    ),
                    severity=2,
                    fix="Use the accessory already in the fit as the anchor, or remove distractions and let one piece talk.",
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
            roast=roast,
            explanation=(
                f"The visible {top_color} upper layer and {accent_color} accent read as a practical base, but the "
                "fit needs a clearer silhouette, cleaner color decision, or one detail that feels deliberate."
            ),
            recommendations=[
                Recommendation(
                    title=f"Fix the {top_color} layer first",
                    reason="The biggest visible layer sets the whole outfit's tone, so it needs the cleanest shape.",
                    priority=5,
                ),
                Recommendation(
                    title=f"Echo the {accent_color} detail once",
                    reason="Repeating one visible accent makes the styling look chosen instead of random.",
                    priority=4,
                ),
                Recommendation(
                    title="Upgrade texture contrast",
                    reason=f"The {top_color} layer needs a texture contrast so it does not flatten the whole photo.",
                    priority=3,
                ),
            ],
            alternate_outfits=[
                AlternateOutfit(
                    name="Streetwear patch",
                    items=[f"structured {top_color} overshirt", "straight-leg denim", "clean sneakers", "one visible accessory"],
                    vibe="more intentional, less laundry-day roulette",
                ),
                AlternateOutfit(
                    name="Smart casual patch",
                    items=[f"clean {top_color} knit", "tailored trouser", "minimal leather sneaker", "one sharp visible detail"],
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

    def _color_name(self, color: str) -> str:
        r, g, b = self._rgb(color)
        max_channel = max(r, g, b)
        min_channel = min(r, g, b)
        spread = max_channel - min_channel
        brightness = (r + g + b) / 3

        if brightness < 35:
            return "black"
        if brightness > 225 and spread < 35:
            return "white"
        if spread < 22:
            if brightness < 85:
                return "charcoal"
            if brightness < 170:
                return "gray"
            return "light gray"

        if r > 165 and g > 135 and b < 120:
            return "tan"
        if r > 150 and g > 120 and b > 110 and spread < 70:
            return "beige"
        if r > g + 45 and r > b + 45:
            return "red" if g < 110 else "orange"
        if g > 120 and b > 120 and abs(g - b) < 75:
            return "teal"
        if g > r + 35 and g > b + 25:
            return "green"
        if b > r + 40 and b > g + 25:
            return "navy" if brightness < 95 else "blue"
        if r > 95 and b > 95 and abs(r - b) < 60 and g < max(r, b) - 25:
            return "purple"
        if r > 95 and g > 55 and b < 80:
            return "brown"
        return "muted"
