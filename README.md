# JobFlow — Backend

REST API for [JobFlow](https://github.com/AndaniMagodi/job-flow-frontend), a South African job board with a built-in application tracker. Browse and search real SA listings, then track every application you make. Built with FastAPI and PostgreSQL.

**Live API:** [jobflow-api.onrender.com](https://jobflow-api.onrender.com) <!-- replace with your URL -->  
**Frontend Repo:** [job-flow-frontend](https://github.com/AndaniMagodi/job-flow-frontend)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | JWT (python-jose + bcrypt + passlib) |
| Config | pydantic-settings |
| Server | Uvicorn |
| Deployment | Render |

---

## Features

**Built for South Africa**
- Learnerships, internships, graduate programmes and apprenticeships classified as first-class opportunity types, not buried among ordinary vacancies — this is how a large share of South Africans actually enter the labour market
- "No experience needed" detected from the advert text and filterable
- Salary benchmarks estimated from our own corpus, because roughly three quarters of SA listings publish no salary and seekers otherwise negotiate blind
- WhatsApp job alerts — where South African users already are, and free to receive
- Data-light mode: skips the webfont and halves the payload per page, for users on capped prepaid data

**Job board**
- Job listings ingested from pluggable sources (Greenhouse public boards, Adzuna South Africa)
- Search and filter by province, sector, experience level, contract type, salary band and remote
- Save jobs for later
- Applying records the application in the tracker and links out to the original posting

**AI (Groq)**
- CV-to-job match scoring — strengths, gaps and next steps for a specific listing, persisted per CV
- Natural-language search — "junior python roles in Cape Town under R40k a month" parsed into structured filters

**Application tracker**
- JWT authentication — register, login, token refresh
- Full CRUD for job applications
- Status tracking per application (Applied, Interview, Offer, Rejected)
- Notes per application
- Application history / activity log
- Follow-up date tracking
- Dashboard stats endpoint (totals, response rate, interview rate)
- Role-based route protection

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL running locally

### Installation

```bash
git clone https://github.com/AndaniMagodi/job-flow-backend.git
cd job-flow-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root:

See [`backend/.env.example`](backend/.env.example) for the full list.

```env
DATABASE_URL=postgresql://user:password@localhost:5432/jobflow
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Job sources, comma-separated in priority order.
# "seed" is synthetic sample data — offline development only.
JOB_SOURCES=greenhouse,adzuna
ADZUNA_APP_ID=          # free from https://developer.adzuna.com/
ADZUNA_APP_KEY=
GREENHOUSE_BOARDS=luno:Luno,ozow:Ozow,entersekt:Entersekt,stitch:Stitch

# Free key from https://console.groq.com/. Without it the /ai
# endpoints return 503 and the UI hides the AI features.
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
```

### Load job listings

```bash
curl -X POST http://localhost:8000/jobs/sync -H "Authorization: Bearer <token>"
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Run Locally

```bash
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and receive JWT token |

### Applications
| Method | Endpoint | Description |
|---|---|---|
| GET | `/applications` | Get all applications for current user |
| POST | `/applications` | Create a new application |
| GET | `/applications/{id}` | Get a single application |
| PUT | `/applications/{id}` | Update an application |
| DELETE | `/applications/{id}` | Delete an application |

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/jobs` | Browse and filter listings |
| GET | `/jobs/facets` | Filter values present in the data |
| GET | `/jobs/{id}` | A single listing |
| POST | `/jobs/{id}/save` | Save a listing |
| DELETE | `/jobs/{id}/save` | Unsave a listing |
| GET | `/jobs/saved` | Saved listings for the current user |
| POST | `/jobs/{id}/apply` | Record an application against a listing |
| POST | `/jobs/sync` | Pull fresh listings from the configured sources |

### AI
| Method | Endpoint | Description |
|---|---|---|
| GET | `/ai/status` | Whether a model is configured |
| POST | `/ai/match` | Score a CV against one listing |
| POST | `/ai/search` | Parse a plain-English query and run it |

### Salary transparency
| Method | Endpoint | Description |
|---|---|---|
| GET | `/jobs/{id}/salary-estimate` | What comparable adverts pay, when the employer states nothing |

### Alerts
| Method | Endpoint | Description |
|---|---|---|
| GET | `/alerts/channels` | Which delivery channels are configured |
| GET | `/alerts` | The current user's alerts |
| POST | `/alerts` | Create a saved search with a WhatsApp destination |
| PATCH | `/alerts/{id}` | Rename, re-filter, pause or resume |
| DELETE | `/alerts/{id}` | Remove an alert |
| POST | `/alerts/{id}/preview` | See what it would send, without sending |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/stats` | Get summary stats for the current user |

---

## Project Structure

```
app/
├── activities/       # Activity log feature
├── ai/               # Groq-backed match scoring and query parsing
├── alerts/           # Saved searches and their delivery
├── api/              # API route registration
├── applications/     # Job applications feature
├── auth/             # JWT auth and user management
├── core/             # Config and settings
├── db/               # Database connection and session
├── jobs/             # Job board
│   ├── router.py     # Browse, save, apply
│   ├── sync.py       # Upsert listings into our database
│   └── sources/      # One file per provider, behind a common interface
├── models/           # SQLAlchemy models
├── notifications/    # Delivery channels (WhatsApp, console) behind one interface
├── salary/           # Salary benchmarks computed from our own listings
└── main.py           # App entry point
```

### Running the alert scheduler

`run_all_alerts` in `app/alerts/service.py` is the entry point. Alerts are
matched against a watermark of the highest job id already sent, so a run only
ever notifies about genuinely new listings, and a delivery failure means the
seeker gets those jobs on the next run rather than losing them.

### Tests

```bash
python -m pytest tests/
```

### Adding a job source

Implement `JobSource` in `app/jobs/sources/`, returning `NormalisedJob` objects,
register it in `sources/__init__.py`, and add its name to `JOB_SOURCES`. Nothing
else in the app changes — routes and the UI never learn which board a listing
came from.

---

## Deployment

Deployed to **Google Cloud Run** in `africa-south1` — the region closest to the
users this board serves — via the Cloud Build pipeline in `cloudbuild.yaml`.

The pipeline builds the image, runs `alembic upgrade head` as a Cloud Run job,
and only then rolls out the new revision. Migrations run as a job rather than on
container start so a scale-out never has two instances migrating at once, and a
failed migration stops the pipeline before the bad revision serves traffic.

### Secrets

Secrets are held in Secret Manager and referenced by the deploy — never written
into `cloudbuild.yaml`, and never baked into the image (see
`backend/.dockerignore`). The service expects these to exist:

| Secret | Purpose |
|---|---|
| `DATABASE_URL` | Cloud SQL connection string |
| `SECRET_KEY` | JWT signing key |
| `GROQ_API_KEY` | CV matching and natural-language search |
| `ADZUNA_APP_ID` | Adzuna South Africa listings |
| `ADZUNA_APP_KEY` | Adzuna South Africa listings |

Create or update one with:

```bash
printf '%s' 'the-value' | gcloud secrets create GROQ_API_KEY --data-file=- --project=<project>
```

Non-secret configuration (`JOB_SOURCES`, `GROQ_MODEL`, `FRONTEND_URL`,
`APP_ENV`) is set as plain environment variables in the deploy step.

### Frontend

The frontend reads `VITE_API_URL` **at build time**, so changing the backend URL
requires a redeploy of the frontend, not just an environment change. The backend
must also list the frontend's origin in the CORS block in `app/main.py`.
