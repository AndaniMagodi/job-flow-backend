from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.applications.router import router as applications_router
from app.activities.router import router as activities_router


app = FastAPI(title=settings.app_name)

# ✅ CORS MUST BE FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://job-flow-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(activities_router)