# Language Learning App — Prononcia

Prononcia is a web-first French pronunciation-learning application. A learner submits a YouTube or audio link, practises a sentence-by-sentence lesson, records a repetition, and receives a transcript-based accuracy score with constructive feedback.

The first release is intentionally narrow: French content, personal use, and text-based evaluation. Phoneme-level analysis, additional languages, and mobile clients are future extensions.

## Current project status

This repository is an early scaffold, not a completed application.

- `frontend/` is a Next.js application built with React and TypeScript.
- `backend/` currently contains a Flask placeholder. The target backend is FastAPI, so this placeholder must be migrated before the API is functional.
- PostgreSQL, object storage, background workers, authentication, media processing, transcription, evaluation, persistence, progress history, and notifications are not implemented yet.

Do not describe these features as complete until they have working code, migrations, tests, and a reproducible local setup.

## System design

| Area | Decision |
| --- | --- |
| Frontend | React with TypeScript; the current web shell uses Next.js |
| API | Python with FastAPI and Uvicorn |
| Relational database | PostgreSQL accessed with SQLAlchemy and asyncpg |
| Database migrations | Alembic |
| Object storage | S3-compatible storage for source media, recordings, and generated artifacts |
| Background processing | Celery workers with Redis as the broker/result backend |
| Media processing | FFmpeg, with permitted YouTube/audio access handled by the backend |
| Speech recognition | Whisper-compatible transcription via `faster-whisper` |
| Initial comparison | Normalized text similarity, word error rate, and Levenshtein-style comparison |
| Deployment | Docker-based frontend, API, worker, PostgreSQL, Redis, and storage integration |
| Scope of v1 | French, web-first, sentence-by-sentence practice, and saved results |

PostgreSQL stores application metadata, users, lessons, attempts, scores, and job status. Object storage stores large binary files; they should not be stored inside PostgreSQL or committed to Git. Background workers handle long-running work such as media retrieval, FFmpeg conversion, transcription, segmentation, and cleanup so API requests remain responsive.

Text similarity measures recognized words, not pronunciation quality by itself. A later evaluation version should add timing, fluency, forced alignment, and phoneme-level analysis.

## User flow

1. The learner signs in and opens Start Learning.
2. They submit a YouTube or audio link.
3. The API validates the request and creates a background processing job.
4. A worker obtains permitted audio, stores media in object storage, transcribes French speech, segments sentences, and records timestamps in PostgreSQL.
5. Part 1 plays the source with the French transcript.
6. Part 2 pauses after each sentence, records the learner, uploads the recording, and evaluates it asynchronously.
7. Part 3 provides audio-only comprehension or recall practice.
8. The learner reviews overall and sentence-level results and may save the session.
9. Progress history can be searched by name, date, link, and score range.

Part 3 is planned and may be deferred until the first usable release is stable.

## API contract (planned)

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `POST` | `/process-video` | Validate a source and enqueue media/transcription processing |
| `GET` | `/jobs/{id}` | Return processing status and errors |
| `GET` | `/video/{id}/parts` | Return the three-part lesson structure |
| `POST` | `/evaluate-pronunciation` | Upload learner audio and enqueue evaluation |
| `GET` | `/evaluations/{id}` | Return evaluation status and result |
| `POST` | `/save-result` | Persist a video, attempt, scores, and progress |
| `GET` | `/progress/{user_id}` | Return saved lessons, attempts, scores, and history |

Example evaluation response:

```json
{
  "score": 82,
  "missed_words": ["le", "chien"],
  "feedback": "Try to pronounce “le” more clearly."
}
```

The API should validate audio, source URLs, authentication, record ownership, upload size, job limits, and worker failures. It must also respect applicable YouTube terms and copyright requirements; do not assume downloading any submitted video is permitted.

## Repository layout

```text
.
├── backend/          # FastAPI API, database models, workers, and media pipeline
├── frontend/         # React/Next.js web client
├── .gitignore
├── requirements.txt  # Python backend dependencies
└── README.md
```

## Local setup

The complete local stack will require PostgreSQL, Redis, an S3-compatible object-storage service, FFmpeg, the FastAPI API, and a background worker. Docker Compose is recommended once those services are configured.

### Backend dependencies

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Install FFmpeg separately and verify that `ffmpeg` is available on `PATH`.

Configure variables such as:

```text
DATABASE_URL=postgresql+asyncpg://prononcia:password@localhost:5432/prononcia
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=<local-access-key>
S3_SECRET_ACCESS_KEY=<local-secret-key>
S3_BUCKET_NAME=prononcia-media
S3_REGION=us-west-2
FRONTEND_ORIGIN=http://localhost:3000
WHISPER_MODEL=small
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=<smtp-username>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM_EMAIL=no-reply@example.com
SMTP_START_TLS=true
FACEBOOK_APP_ID=<meta-app-id>
FACEBOOK_APP_SECRET=<meta-app-secret>
FACEBOOK_REDIRECT_URI=http://localhost:8000/auth/facebook/callback
FACEBOOK_GRAPH_VERSION=v24.0
```

Password recovery requires working SMTP settings. For Gmail, use
`smtp.gmail.com` on port `587` with a Google app password rather than the
normal account password. Copy `backend/.env.example` to `backend/.env`, fill
in the provider values, and restart the FastAPI service.

After the FastAPI entry point and worker are implemented, the intended commands are:

```bash
uvicorn backend.main:app --reload --port 8000
celery -A backend.worker.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use `NEXT_PUBLIC_API_URL=http://localhost:8000` rather than hard-coding the API base URL.

## Engineering expectations

- Use Alembic migrations for every PostgreSQL schema change; do not edit production tables manually.
- Keep secrets, downloaded media, model caches, and generated artifacts out of Git.
- Store object-storage keys in the database, not large files or public credentials.
- Make worker jobs idempotent, retryable, observable, and safe to run more than once.
- Add tests for URL validation, database models, sentence segmentation, text normalization, scoring, feedback thresholds, and job failure handling.
- Keep processing jobs bounded; transcription and media conversion must not block an API request indefinitely.
- Treat the score as an initial learning aid, not a definitive measure of French pronunciation.

## License and external services

Add a project license before distribution. Review the terms for YouTube, Whisper/model weights, PostgreSQL hosting, object storage, Redis, and notification providers before deploying beyond personal use.
