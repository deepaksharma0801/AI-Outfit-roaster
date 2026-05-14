import type { AnalyzeResponse, OutfitAnalysis, OutfitRecord, StyleHistory } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function analyzeFits(files: File[], userId = "demo-user"): Promise<AnalyzeResponse> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("user_id", userId);
  form.append("async_processing", "false");

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

export function demoAnalyze(files: Array<{ id: string; previewUrl: string }>): AnalyzeResponse {
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
        title: "Needs a sharper focal point",
        detail: "The base is wearable, but no single piece is fully taking the aux.",
        severity: 3,
        fix: "Add one high-contrast jacket, bag, or shoe shape.",
      },
      {
        title: "Accessory layer is undercooked",
        detail: "The fit is asking for a cap, watch, jewelry, or bag to finish the sentence.",
        severity: 2,
        fix: "Pick one accessory in a repeated accent color.",
      },
    ],
    strengths: [
      { title: "Palette discipline", detail: "The colors feel controlled instead of chaotic." },
      { title: "Easy upgrade path", detail: "A few styling choices can move this from fine to feed-worthy." },
    ],
    roast: "This outfit has LinkedIn profile picture confidence with TikTok draft energy.",
    explanation:
      "The look has a clean base and enough restraint to build on. Push silhouette, texture, or accessories so the outfit reads intentional on camera.",
    recommendations: [
      { title: "Add a technical outer layer", reason: "It gives the silhouette more architecture.", priority: 5 },
      { title: "Repeat an accent color", reason: "Color repetition makes the outfit feel styled.", priority: 4 },
      { title: "Increase texture contrast", reason: "Matte, ribbed, denim, or nylon layers add depth.", priority: 3 },
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
    tags: ["streetwear", "techwear", "upgradeable", "camera-ready"],
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
