# Language Learning App - Prononcia

Prononcia is a web-first French pronunciation-learning application. A learner submits a YouTube or audio link, practises a sentence-by-sentence lesson, records a repetition, and receives a transcript-based accuracy score with constructive feedback.

The first release is intentionally narrow: French content, personal use, and text-based evaluation. Phoneme-level analysis, additional languages, and mobile clients are future extensions.

## Current project status

The project is currently hosted and the first usable French pronunciation-learning flow is available.

- Frontend: https://prononcia-fqfmyfzpo-kiet15.vercel.app
- Backend: https://prononcia-1063858437208.us-west1.run.app
- `frontend/` is a Next.js application built with React and TypeScript.
- `backend/` is a FastAPI application using PostgreSQL and Alembic migrations.
- Email/password authentication, Google and Facebook authentication, password recovery, session cookies, video processing, transcript segmentation, pronunciation evaluation, and result saving are implemented.
- The Menu page currently supports Start Learning. Progress, Profile Setting, and Notification Setting are displayed as unavailable features while they are in development.
- Phoneme-level pronunciation analysis, additional languages, and production-grade progress and notification settings remain future work.

The hosted deployments require their frontend and backend environment variables to be configured independently.

Video transcription and translation run in the separate `prononcia-worker`
Cloud Run Job. The API service creates a PostgreSQL processing job and starts
one worker execution with `PRONONCIA_JOB_ID`; the worker runs Whisper and the
Helsinki French-to-English model, saves the result, and exits. PostgreSQL is
the queue and source of truth; Redis is not required.

The API service requires these worker-trigger settings in production:

```text
GOOGLE_CLOUD_PROJECT=<google-cloud-project-id>
WORKER_JOB_NAME=prononcia-worker
WORKER_JOB_REGION=us-west1
```

The API service account needs permission to execute the Cloud Run Job. The
worker job needs the same `DATABASE_URL`, the model settings, and access to
the YouTube cookie secret. Deploy the API image from `Dockerfile` and the
worker image from `Dockerfile.worker`.

### YouTube extraction deployment

The backend supports a dedicated YouTube cookie file through the
`YOUTUBE_COOKIES_FILE` environment variable. Store the exported Netscape
cookie file as a Google Secret Manager secret and mount that secret into the
Cloud Run container as a file. Set `YOUTUBE_COOKIES_FILE` to the mounted file
path. Never commit the cookie file, send it to the frontend, or expose it from
an API endpoint.

For a Cloud Run deployment, grant the service account
`roles/secretmanager.secretAccessor`, create the secret from a local cookie
file, and mount it without copying it into the image:

```bash
gcloud secrets create prononcia-youtube-cookies \
  --data-file=cookies.txt

gcloud run services update SERVICE_NAME \
  --update-secrets=/secrets/youtube/cookies.txt=prononcia-youtube-cookies:latest \
  --update-env-vars=YOUTUBE_COOKIES_FILE=/secrets/youtube/cookies.txt
```

Keep `cookies.txt` local and remove it from the machine when the secret has
been uploaded successfully.

The Docker image includes Deno and the yt-dlp default components required for
YouTube's JavaScript challenge handling. This improves compatibility but does
not guarantee that YouTube will permit every request.

When French subtitles are available from the permitted source, the backend
uses those timestamped captions first and avoids downloading source audio.
Audio download remains a fallback for videos without usable French captions.
Do not use a proxy as an authentication workaround.

## System design

| Area | Decision |
| --- | --- |
| Frontend | React with TypeScript; the current web shell uses Next.js |
| API | Python with FastAPI and Uvicorn |
| Relational database | PostgreSQL accessed with SQLAlchemy and asyncpg |
| Database migrations | Alembic |
| Object storage | S3-compatible storage for source media, recordings, and generated artifacts |
| Background processing | Cloud Run Job worker coordinated through PostgreSQL |
| Media processing | FFmpeg, with permitted YouTube/audio access handled by the backend |
| Speech recognition | Whisper-compatible transcription via `faster-whisper` |
| Initial comparison | Normalized text similarity, word error rate, and Levenshtein-style comparison |
| Deployment | Docker-based frontend, API, worker, PostgreSQL, and storage integration |
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

The complete local stack will require PostgreSQL, an S3-compatible object-storage service, FFmpeg, the FastAPI API, and a background worker. Docker Compose is recommended once those services are configured.

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
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Password recovery requires working SMTP settings. For Gmail, use
`smtp.gmail.com` on port `587` with a Google app password rather than the
normal account password. Copy `backend/.env.example` to `backend/.env`, fill
in the provider values, and restart the FastAPI service.

After the FastAPI entry point and worker are implemented, the intended commands are:

```bash
cd backend
uvicorn main:app --reload --port 8000
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

Add a project license before distribution. Review the terms for YouTube, Whisper/model weights, PostgreSQL hosting, object storage, and notification providers before deploying beyond personal use.
