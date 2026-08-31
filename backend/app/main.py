from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import audits, auth, companies, documents, entitlements
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Enterprise Customs Bond Import Audit System — Module 01: Import Audit",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(audits.router)
app.include_router(documents.router)
app.include_router(documents.templates_router)
app.include_router(entitlements.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
