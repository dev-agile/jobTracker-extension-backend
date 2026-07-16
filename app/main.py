from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import api_router
from .core.config import get_settings
from .startup import seed_admin

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_admin()
    yield


app = FastAPI(title="Job Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
