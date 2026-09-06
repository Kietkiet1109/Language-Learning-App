# Language Learning App - Prononcia

Prononcia is a web-first French pronunciation-learning application. A learner submits a YouTube or audio link, practises a sentence-by-sentence lesson, records a repetition, and receives a transcript-based accuracy score with constructive feedback.

The first release is intentionally narrow: French content, personal use, and text-based evaluation. Phoneme-level analysis, additional languages, and mobile clients are future extensions.

## Current project status

This repository is an early scaffold, not a completed application.

- `frontend/` is a Next.js/React web scaffold.
- `backend/` currently contains a Flask placeholder. The target backend is FastAPI, so this placeholder must be migrated before the API is functional.
- Authentication, media processing, transcription, evaluation, persistence, progress history, and notifications are not implemented yet.

Do not describe these features as complete until they have working code and tests.

## Technical direction

| Area | Decision |
| --- | --- |
| Client | Next.js with React and TypeScript |
| API | Python with FastAPI and Uvicorn |
| Database | MongoDB Atlas accessed through PyMongo |
| Media processing | FFmpeg, with permitted YouTube/audio access handled by the backend |
| Speech recognition | Whisper-compatible transcription via `faster-whisper` |
| Initial comparison | Normalized text similarity, word error rate, and Levenshtein-style comparison |
| Deployment | Docker-based services for the web client, API, and media tooling |
| Scope of v1 | French, web-first, sentence-by-sentence practice, saved results |

Text similarity measures recognized words, not pronunciation quality by itself. A later evaluation version should add timing, fluency, forced alignment, and phoneme-level analysis.

## User flow

1. The learner signs in and opens Start Learning.
2. They submit a YouTube or audio link.
3. The API validates the link, obtains permitted audio, transcribes French speech, segments sentences, and records timestamps.
4. Part 1 plays the source with the French transcript.
5. Part 2 pauses after each sentence, records the learner, transcribes the recording, and returns a score, missed words, and feedback.
6. Part 3 provides audio-only comprehension or recall practice.
7. The learner reviews overall and sentence-level results and may save the session.
8. Progress history can be searched by name, date, link, and score range.

Part 3 is planned and may be deferred until the first usable release is stable.

## API contract

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `POST` | `/process-video` | Validate a source and return metadata, transcript segments, sentences, and timestamps |
| `GET` | `/video/{id}/parts` | Return the three-part lesson structure |
| `POST` | `/evaluate-pronunciation` | Transcribe learner audio, compare it with the target sentence, and return evaluation |
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

The API should validate audio, source URLs, authentication, record ownership, and processing limits. It must also respect applicable YouTube terms and copyright requirements; do not assume downloading any submitted video is permitted.

## Repository layout

```text
.
├── backend/          # FastAPI service and media/evaluation pipeline
├── frontend/         # Next.js web client
├── .gitignore
├── requirements.txt  # Python backend dependencies
└── README.md
```

## Local setup

### Backend

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install FFmpeg separately and verify that `ffmpeg` is available on `PATH`. Configure variables such as:

```text
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/<database>
MONGODB_DATABASE=prononcia
WHISPER_MODEL=small
FRONTEND_ORIGIN=http://localhost:3000
```

Once the FastAPI entry point exists:

```bash
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use `NEXT_PUBLIC_API_URL=http://localhost:8000` rather than hard-coding the API base URL.

## Engineering expectations

- Keep secrets, downloaded media, model caches, and generated artifacts out of Git.
- Add tests for URL validation, sentence segmentation, text normalization, scoring, and feedback thresholds before complex UI.
- Keep processing jobs bounded and observable; transcription must not block a web request indefinitely.
- Treat the score as an initial learning aid, not a definitive measure of French pronunciation.
- Prefer small, testable services for ingestion, transcription, segmentation, evaluation, persistence, and notifications.
