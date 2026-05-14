from typing import Any, TypedDict

from app.schemas.outfit import OutfitAnalysis
from app.schemas.outfit import RoastLevel
from app.services.clip_embeddings import ClipEmbeddingService
from app.services.image_pipeline import ProcessedImage
from app.services.vision import VisionAnalyzer

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - optional local fallback
    END = None
    StateGraph = None


class OutfitGraphState(TypedDict, total=False):
    image: ProcessedImage
    roast_level: RoastLevel
    analysis: OutfitAnalysis
    embedding: list[float]


class OutfitAnalysisGraph:
    """LangGraph orchestration boundary for multimodal outfit analysis."""

    def __init__(self, analyzer: VisionAnalyzer, embeddings: ClipEmbeddingService) -> None:
        self.analyzer = analyzer
        self.embeddings = embeddings
        self.graph = self._build_graph()

    async def run(
        self,
        image: ProcessedImage,
        roast_level: RoastLevel = RoastLevel.brutal,
    ) -> tuple[OutfitAnalysis, list[float]]:
        if self.graph is not None:
            state = await self.graph.ainvoke({"image": image, "roast_level": roast_level})
            return state["analysis"], state["embedding"]

        analysis = await self.analyzer.analyze(image, roast_level)
        embedding = await self.embeddings.embed_image(image.content)
        return analysis, embedding

    def _build_graph(self) -> Any | None:
        if StateGraph is None or END is None:
            return None

        async def analyze_node(state: OutfitGraphState) -> OutfitGraphState:
            return {
                "analysis": await self.analyzer.analyze(
                    state["image"],
                    state.get("roast_level", RoastLevel.brutal),
                )
            }

        async def embed_node(state: OutfitGraphState) -> OutfitGraphState:
            return {"embedding": await self.embeddings.embed_image(state["image"].content)}

        graph = StateGraph(OutfitGraphState)
        graph.add_node("vision_analysis", analyze_node)
        graph.add_node("clip_embedding", embed_node)
        graph.set_entry_point("vision_analysis")
        graph.add_edge("vision_analysis", "clip_embedding")
        graph.add_edge("clip_embedding", END)
        return graph.compile()
