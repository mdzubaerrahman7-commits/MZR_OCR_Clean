import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import audits, auth, bill_of_entries, companies, conversion, documents, entitlements, findings, imports, matching, reports, rules
from app.core.config import get_settings

logger = logging.getLogger("bondaudit")

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Enterprise Customs Bond Import Audit System — Module 01: Import Audit",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # The frontend never sends cookies (auth is a bearer token in an Authorization
    # header, added explicitly per request) — no browser request from this app is
    # ever "credentialed", so this is accurately False rather than a formality.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(audits.router)
app.include_router(documents.router)
app.include_router(documents.templates_router)
app.include_router(entitlements.router)
app.include_router(imports.router)
app.include_router(bill_of_entries.router)
app.include_router(matching.audit_router)
app.include_router(conversion.router)
app.include_router(rules.router)
app.include_router(findings.router)
app.include_router(reports.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Spec section 3/24 apply to failure modes too: an audit tool must never leak an
    internal stack trace (which could itself be mistaken for evidence) to the client.
    The real error is logged server-side; the client gets a safe, generic message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
