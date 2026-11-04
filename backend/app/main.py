import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.api.v1.endpoints import ws
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.redis import close_redis, redis_client
from app.core.websocket_manager import websocket_manager
from app.services.outbox_worker import outbox_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Real-Time Redis Pub/Sub listener & Outbox Worker daemon
    pubsub_task = asyncio.create_task(websocket_manager.start_redis_listener(redis_client))
    audit_task = asyncio.create_task(websocket_manager.start_periodic_audit(AsyncSessionLocal))
    outbox_task = asyncio.create_task(outbox_worker.run_loop(AsyncSessionLocal, redis_client))

    yield

    # Shutdown
    outbox_worker.stop()
    pubsub_task.cancel()
    audit_task.cancel()
    outbox_task.cancel()
    await asyncio.gather(pubsub_task, audit_task, outbox_task, return_exceptions=True)
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Nexus Team Collaboration & Project Management SaaS API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "status": "online",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
