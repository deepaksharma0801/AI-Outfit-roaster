# DripJudge AI

DripJudge AI is a production-style multimodal fashion analysis platform. Users upload outfit photos, get a structured AI analysis, receive a funny roast, learn what is working or failing, and track style evolution over time.

## Stack

- Frontend: Next.js 15, TypeScript, TailwindCSS, Framer Motion, shadcn-style primitives
- Backend: FastAPI, Python 3.12, async services
- AI: OpenAI vision-ready orchestration, CLIP embedding seam, structured JSON contracts
- Data: PostgreSQL with pgvector, Redis cache/queue foundation
- Infra: Docker Compose and GitHub Actions

## Quick Start

```bash
cp .env.example .env
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
docker compose up postgres redis -d
npm run dev:web
uvicorn app.main:app --reload --app-dir apps/api
```

Frontend: http://localhost:3000  
Backend: http://localhost:8000/docs

## Production Notes

- Set `OPENAI_API_KEY` to enable live GPT-4o vision analysis.
- The backend ships with a deterministic fallback analyzer so demos and CI remain stable without model credentials.
- `DATABASE_URL` supports Postgres plus pgvector for outfit history and similarity.
- `REDIS_URL` is reserved for async processing, cache entries, and future worker queues.

## API Shape

The main response contract is intentionally strict:

```json
{
  "style": "streetwear",
  "aesthetic": "techwear",
  "confidence": 0.91,
  "drip_score": 7.8,
  "detected_items": [],
  "issues": [],
  "strengths": [],
  "roast": "",
  "recommendations": [],
  "alternate_outfits": []
}
```

## Structure

```text
apps/web      Next.js product interface
apps/api      FastAPI service, AI pipeline, schemas, tests
infra         database bootstrap
.github       CI workflow
```
