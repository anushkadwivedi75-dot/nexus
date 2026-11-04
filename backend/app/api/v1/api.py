from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, invitations, projects, tasks, users, workspaces, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(projects.router, tags=["Projects"])
api_router.include_router(tasks.router, tags=["Tasks"])
api_router.include_router(ws.router, tags=["WebSocket"])
