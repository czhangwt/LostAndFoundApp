import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routers import items, moderation, users

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Campus Lost and Found")

# Include API routers
app.include_router(users.router)
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(moderation.router, prefix="/moderation", tags=["moderation"])

# Ensure uploads directory exists and mount uploads
uploads_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Mount static files directory for frontend UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

