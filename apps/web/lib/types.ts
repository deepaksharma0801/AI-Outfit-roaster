export type DetectedItem = {
  category: string;
  name: string;
  color: string;
  material?: string | null;
  confidence: number;
};

export type StyleIssue = {
  title: string;
  detail: string;
  severity: number;
  fix: string;
};

export type StyleStrength = {
  title: string;
  detail: string;
};

export type Recommendation = {
  title: string;
  reason: string;
  priority: number;
};

export type AlternateOutfit = {
  name: string;
  items: string[];
  vibe: string;
};

export type OutfitAnalysis = {
  style: string;
  aesthetic: string;
  confidence: number;
  drip_score: number;
  detected_items: DetectedItem[];
  issues: StyleIssue[];
  strengths: StyleStrength[];
  roast: string;
  explanation: string;
  recommendations: Recommendation[];
  alternate_outfits: AlternateOutfit[];
  color_palette: string[];
  tags: string[];
};

export type OutfitRecord = {
  id: string;
  user_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  image_sha256: string;
  image_preview_url?: string | null;
  analysis?: OutfitAnalysis | null;
  created_at: string;
};

export type AnalyzeResponse = {
  batch_id: string;
  processing_mode: string;
  results: OutfitRecord[];
};

export type StyleHistory = {
  user_id: string;
  average_score: number;
  best_score: number;
  total_outfits: number;
  dominant_styles: string[];
  timeline: Array<{
    date: string;
    drip_score: number;
    style: string;
    aesthetic: string;
  }>;
};
