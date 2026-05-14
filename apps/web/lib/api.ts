import type { AnalyzeResponse, OutfitAnalysis, OutfitRecord, RoastLevel, StyleHistory } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function analyzeFits(
  files: File[],
  userId = "demo-user",
  roastLevel: RoastLevel = "brutal",
): Promise<AnalyzeResponse> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("user_id", userId);
  form.append("async_processing", "false");
  form.append("roast_level", roastLevel);

  const response = await fetch(`${API_BASE_URL}/api/v1/outfits/analyze`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new Error(`Analysis failed with ${response.status}`);
  }

  return response.json() as Promise<AnalyzeResponse>;
}

export async function fetchHistory(userId = "demo-user"): Promise<OutfitRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/outfits/history?user_id=${userId}`, {
    cache: "no-store",
  });
  if (!response.ok) return [];
  return response.json() as Promise<OutfitRecord[]>;
}

export async function fetchStyleHistory(userId = "demo-user"): Promise<StyleHistory | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/style/history?user_id=${userId}`, {
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json() as Promise<StyleHistory>;
}

const demoRoasts: Record<RoastLevel, string> = {
  chill: "That gray upper layer is trying. It has the energy of a decent draft that still needs notes.",
  spicy: "Bro that gray top layer has airplane-mode confidence. It exists, but it is not connecting.",
  brutal: "Bro what is that gray hoodie-coat situation? Take it off, the fit is giving default settings with sleeves.",
  nuclear: "Wtf is that gray layer doing, bro? It looks like the hoodie and coat had an argument and both lost.",
};

const demoExplanations: Record<RoastLevel, string> = {
  chill:
    "The base is workable, but the gray upper layer needs one sharper focal point so it feels styled instead of merely assembled.",
  spicy:
    "The fit is not cooked beyond saving, but the gray top layer and visible details need to stop acting like optional side quests.",
  brutal:
    "The outfit is not dead, but that gray layer is absolutely on life support. Pick a stronger silhouette and make the visible accessory/detail actually anchor the look.",
  nuclear:
    "The fit needs a full emergency patch: fix the gray layer first, clean the proportions, and make one visible detail look intentional.",
};

export function demoAnalyze(
  files: Array<{ id: string; previewUrl: string }>,
  roastLevel: RoastLevel = "brutal",
): AnalyzeResponse {
  const baseScore = 7.2 + Math.min(files.length, 3) * 0.2;
  const analysis: OutfitAnalysis = {
    style: "streetwear",
    aesthetic: "clean techwear",
    confidence: 0.82,
    drip_score: Number(baseScore.toFixed(1)),
    detected_items: [
      { category: "top", name: "structured upper layer", color: "#d9e2dc", confidence: 0.78 },
      { category: "bottom", name: "relaxed trouser shape", color: "#181d24", confidence: 0.72 },
      { category: "shoes", name: "low-profile sneaker", color: "#f5f0e8", confidence: 0.66 },
    ],
    issues: [
      {
        title: "That gray layer needs a real job",
        detail: "The base is wearable, but the gray upper layer is taking up camera space without earning it.",
        severity: 3,
        fix: "Make that layer sharper, crop it cleaner, or swap it for something with actual structure.",
      },
      {
        title: "Visible details are not landing",
        detail: "Any watch, bag, cap, or jewelry already in the photo needs to look intentional instead of decorative noise.",
        severity: 2,
        fix: "Use the visible accessory as the anchor or simplify the fit so one detail actually hits.",
      },
    ],
    strengths: [
      { title: "Palette discipline", detail: "The colors feel controlled instead of chaotic." },
      { title: "Easy upgrade path", detail: "A few styling choices can move this from fine to feed-worthy." },
    ],
    roast: demoRoasts[roastLevel],
    explanation: demoExplanations[roastLevel],
    recommendations: [
      { title: "Fix the gray layer", reason: "The biggest visible piece sets the whole outfit's tone.", priority: 5 },
      { title: "Make the visible accessory matter", reason: "If the watch or detail is already there, it needs to anchor the fit instead of floating.", priority: 4 },
      { title: "Increase texture contrast", reason: "Matte, ribbed, denim, or nylon texture would keep the gray layer from looking flat.", priority: 3 },
    ],
    alternate_outfits: [
      {
        name: "Subway protagonist",
        items: ["cropped utility jacket", "straight black denim", "silver chain", "sleek sneaker"],
        vibe: "clean, fast, mildly intimidating",
      },
      {
        name: "Cafe investor",
        items: ["ribbed knit", "pleated trouser", "leather belt", "minimal loafer"],
        vibe: "quiet money with Wi-Fi",
      },
    ],
    color_palette: ["#181d24", "#f5f0e8", "#7de2d1", "#ff6f61", "#c6ff4a"],
    tags: ["streetwear", "techwear", "upgradeable", "camera-ready", `roast:${roastLevel}`],
  };

  return {
    batch_id: crypto.randomUUID(),
    processing_mode: "demo",
    results: files.map((file, index) => ({
      id: file.id,
      user_id: "demo-user",
      status: "completed",
      image_sha256: file.id.replaceAll("-", ""),
      image_preview_url: file.previewUrl,
      analysis: {
        ...analysis,
        drip_score: Number((analysis.drip_score + index * 0.3).toFixed(1)),
      },
      created_at: new Date().toISOString(),
    })),
  };
}
