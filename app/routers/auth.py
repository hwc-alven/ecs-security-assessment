"""Auth routes — login, logout, session check, and audit log endpoints."""
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Response, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from ..config import TEMPLATE_DIR, state
from ..services.auth_service import (
    AuthService, AuditLog, SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, EVENT_TYPES,
)

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# These will be injected by main.py at startup
_auth_service: Optional[AuthService] = None
_audit_log: Optional[AuditLog] = None


def init_auth_services(auth: AuthService, audit: AuditLog):
    """Called by main.py to inject the service instances."""
    global _auth_service, _audit_log
    _auth_service = auth
    _audit_log = audit


def get_auth_service() -> AuthService:
    if _auth_service is None:
        raise RuntimeError("Auth service not initialized")
    return _auth_service


def get_audit_log() -> AuditLog:
    if _audit_log is None:
        raise RuntimeError("Audit log not initialized")
    return _audit_log


def get_current_user(request: Request) -> Optional[str]:
    """Extract and validate the session from the request cookie.
    Returns username if authenticated, None otherwise.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    session = get_auth_service().validate_session(token)
    if session:
        return session["username"]
    return None


def require_auth(request: Request) -> str:
    """FastAPI dependency that requires authentication.
    Returns the username if authenticated, raises 401/redirect otherwise.
    """
    user = get_current_user(request)
    if not user:
        accept = request.headers.get("accept", "")
        if "text/html" in accept or "application/json" not in accept:
            raise HTTPException(status_code=303, detail="/login")
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


router = APIRouter()


# ── Login page ──

@router.get("/login")
async def login_page(request: Request):
    """Render the login page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {
        "error": None,
    })


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login_submit(request: Request, req: LoginRequest):
    """Process login form submission."""
    ip = request.client.host if request.client else "unknown"
    session = get_auth_service().authenticate(req.username, req.password, ip_address=ip)
    if session:
        response = JSONResponse({"success": True, "redirect": "/"})
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session["token"],
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            secure=False,  # Set True when behind HTTPS proxy
            path="/",
        )
        return response
    return JSONResponse(
        {"success": False, "error": "Invalid username or password"},
        status_code=401,
    )


@router.post("/logout")
async def logout(request: Request):
    """Log out the current user."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        get_auth_service().destroy_session(token)
    response = JSONResponse({"success": True, "redirect": "/login"})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/api/auth/status")
async def auth_status(request: Request):
    """Check if the current session is valid."""
    user = get_current_user(request)
    return {
        "authenticated": user is not None,
        "username": user,
    }


# ── Audit log page ──

@router.get("/audit-log")
async def audit_log_page(request: Request, user: str = Depends(require_auth)):
    """Render the audit log page."""
    audit = get_audit_log()
    stats = audit.get_stats()
    return templates.TemplateResponse(request, "audit_log.html", {
        "username": user,
        "event_types": EVENT_TYPES,
        "stats": stats,
    })


@router.get("/api/audit-log/query")
async def audit_log_query(
    request: Request,
    user: str = Depends(require_auth),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Query audit log entries with filtering and pagination."""
    audit = get_audit_log()
    entries, total = audit.query(
        event_type=event_type,
        severity=severity,
        username=username,
        search_text=search,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return {
        "entries": entries,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/api/audit-log/stats")
async def audit_log_stats(request: Request, user: str = Depends(require_auth)):
    """Get audit log summary statistics."""
    audit = get_audit_log()
    return audit.get_stats()


@router.get("/api/audit-log/export")
async def audit_log_export(
    request: Request,
    user: str = Depends(require_auth),
    format: str = Query("json", regex="^(json|csv)$"),
):
    """Export audit log entries."""
    audit = get_audit_log()
    entries, total = audit.query(limit=10000)

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if entries:
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            for e in entries:
                row = {k: str(v) if not isinstance(v, str) else v for k, v in e.items()}
                writer.writerow(row)
        from fastapi.responses import Response as RawResponse
        return RawResponse(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"},
        )

    return JSONResponse({"entries": entries, "total": total})


# ── Session management ──

@router.get("/api/auth/sessions")
async def active_sessions(request: Request, user: str = Depends(require_auth)):
    """List active sessions (admin only)."""
    sessions = get_auth_service().get_active_sessions()
    return {
        "sessions": [
            {
                "username": s["username"],
                "ip_address": s.get("ip_address", ""),
                "created_at": datetime.fromtimestamp(s["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": datetime.fromtimestamp(s["expires_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                "is_current": request.cookies.get(SESSION_COOKIE_NAME) == s["token"],
            }
            for s in sessions
        ],
        "count": len(sessions),
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/auth/change-password")
async def change_password(request: Request, req: ChangePasswordRequest):
    """Change the admin password."""
    ip = request.client.host if request.client else "unknown"
    auth = get_auth_service()

    # Verify current password
    session_obj = auth.authenticate(auth.admin_username, req.current_password, ip_address=ip)
    if not session_obj:
        return JSONResponse({"success": False, "error": "Current password is incorrect"}, status_code=401)

    # Destroy the temporary session we just created
    auth.destroy_session(session_obj["token"])

    # Change password
    if len(req.new_password) < 8:
        return JSONResponse({"success": False, "error": "New password must be at least 8 characters"}, status_code=400)

    success = auth.change_password(req.new_password)
    if success:
        return {"success": True, "message": "Password changed successfully. Please log in again."}
    return JSONResponse({"success": False, "error": "Failed to change password"}, status_code=500)