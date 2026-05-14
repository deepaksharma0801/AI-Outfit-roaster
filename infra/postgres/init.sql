CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS outfits (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'demo-user',
  image_sha256 TEXT NOT NULL,
  storage_url TEXT,
  status TEXT NOT NULL,
  style TEXT,
  aesthetic TEXT,
  confidence DOUBLE PRECISION,
  drip_score DOUBLE PRECISION,
  analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(512),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outfits_user_created ON outfits (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outfits_embedding ON outfits USING ivfflat (embedding vector_cosine_ops) WITH (lists = 64);
