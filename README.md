# JobFlow — Backend

REST API for [JobFlow](https://github.com/AndaniMagodi/job-flow-frontend), a full-stack job application tracker. Built with FastAPI and PostgreSQL.

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

```env
DATABASE_URL=postgresql://user:password@localhost:5432/jobflow
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
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

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/stats` | Get summary stats for the current user |

---

## Project Structure

```
app/
├── activities/       # Activity log feature
├── api/              # API route registration
├── applications/     # Job applications feature
├── auth/             # JWT auth and user management
├── core/             # Config and settings
├── db/               # Database connection and session
├── models/           # SQLAlchemy models
└── main.py           # App entry point
```

---

## Deployment

Deployed on **Render** as a web service. Set all environment variables in the Render dashboard. Use a Render PostgreSQL instance for the database.
