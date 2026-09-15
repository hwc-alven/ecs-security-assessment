"""Auth routes — login, logout, register, account, reg codes, audit log."""
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from ..config import TEMPLATE_DIR, state
from ..services.auth_service import (
    AuthService, AuditLog, SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, EVENT_TYPES,
)

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

_auth_service: Optional[AuthService] = None
_audit_log: Optional[AuditLog] = None


def init_auth_services(auth: AuthService, audit: AuditLog):
    global _auth_service, _audit_log
    _auth_service = auth
    _audit_log = audit


def get_auth_service() -> AuthService:
    return _auth_service


def get_audit_log() -> AuditLog:
    return _audit_log


def get_current_user(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token: return None
    session = get_auth_service().validate_session(token)
    return session["username"] if session else None


def get_current_session(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return get_auth_service().validate_session(token) if token else None


router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login_submit(request: Request, req: LoginRequest):
    ip = request.client.host if request.client else "unknown"
    session = get_auth_service().authenticate(req.username, req.password, ip_address=ip)
    if session:
        response = JSONResponse({"success": True, "redirect": "/"})
        response.set_cookie(key=SESSION_COOKIE_NAME, value=session["token"],
                            max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax", secure=False, path="/")
        return response
    return JSONResponse({"success": False, "error": "Invalid username or password"}, status_code=401)


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token: get_auth_service().destroy_session(token)
    response = JSONResponse({"success": True, "redirect": "/login"})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/api/auth/status")
async def auth_status(request: Request):
    user = get_current_user(request)
    return {"authenticated": user is not None, "username": user}


# ── Registration ──

@router.get("/register")
async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: str


@router.post("/api/auth/register")
async def register_user(request: Request, req: RegisterRequest):
    ip = request.client.host if request.client else "unknown"
    success, message = get_auth_service().register_user(req.username, req.password, req.invite_code, ip_address=ip)
    if success: return {"success": True, "message": message}
    return JSONResponse({"success": False, "error": message}, status_code=400)


# ── Registration Code Management (admin only) ──

@router.get("/regcodes")
async def regcodes_page(request: Request):
    session = get_current_session(request)
    if not session: return RedirectResponse(url="/login", status_code=303)
    if session.get("role") != "admin": return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("regcodes.html", {"request": request, "username": session["username"]})


class GenerateCodeRequest(BaseModel):
    max_uses: int = 1
    expires_hours: Optional[int] = None
    note: str = ""


@router.post("/api/auth/regcodes/generate")
async def generate_code(request: Request, req: GenerateCodeRequest):
    session = get_current_session(request)
    if not session or session.get("role") != "admin":
        return JSONResponse({"success": False, "error": "Admin access required"}, status_code=403)
    ip = request.client.host if request.client else "unknown"
    code, err = get_auth_service().generate_registration_code(
        session["username"], max_uses=req.max_uses, expires_hours=req.expires_hours,
        note=req.note, ip_address=ip)
    if code: return {"success": True, "code": code}
    return JSONResponse({"success": False, "error": err or "Failed"}, status_code=400)


@router.get("/api/auth/regcodes/list")
async def list_codes(request: Request):
    session = get_current_session(request)
    if not session or session.get("role") != "admin":
        return JSONResponse({"success": False, "error": "Admin access required"}, status_code=403)
    return {"codes": get_auth_service().list_registration_codes()}


class CodeActionRequest(BaseModel):
    code: str


@router.post("/api/auth/regcodes/revoke")
async def revoke_code(request: Request, req: CodeActionRequest):
    session = get_current_session(request)
    if not session or session.get("role") != "admin":
        return JSONResponse({"success": False, "error": "Admin access required"}, status_code=403)
    ip = request.client.host if request.client else "unknown"
    if get_auth_service().revoke_registration_code(req.code, session["username"], ip_address=ip):
        return {"success": True}
    return JSONResponse({"success": False, "error": "Code not found"}, status_code=404)


@router.post("/api/auth/regcodes/delete")
async def delete_code(request: Request, req: CodeActionRequest):
    session = get_current_session(request)
    if not session or session.get("role") != "admin":
        return JSONResponse({"success": False, "error": "Admin access required"}, status_code=403)
    ip = request.client.host if request.client else "unknown"
    if get_auth_service().delete_registration_code(req.code, session["username"], ip_address=ip):
        return {"success": True}
    return JSONResponse({"success": False, "error": "Code not found"}, status_code=404)


# ── Account ──

@router.get("/account")
async def account_page(request: Request):
    session = get_current_session(request)
    if not session: return RedirectResponse(url="/login", status_code=303)
    auth = get_auth_service()
    user_info = auth.get_user_info(session["username"]) or {}
    users = auth.list_users() if session.get("role") == "admin" else []
    return templates.TemplateResponse("account.html", {
        "request": request, "username": session["username"],
        "user_info": user_info, "users": users})


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/auth/change-password")
async def change_password(request: Request, req: ChangePasswordRequest):
    session = get_current_session(request)
    if not session: return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
    ip = request.client.host if request.client else "unknown"
    success, message = get_auth_service().change_password(
        session["username"], req.current_password, req.new_password, ip_address=ip)
    if success:
        get_auth_service().destroy_session(request.cookies.get(SESSION_COOKIE_NAME, ""))
        return {"success": True, "message": message}
    return JSONResponse({"success": False, "error": message}, status_code=400)


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str


@router.post("/api/auth/admin/reset-password")
async def admin_reset_password(request: Request, req: ResetPasswordRequest):
    session = get_current_session(request)
    if not session or session.get("role") != "admin":
        return JSONResponse({"success": False, "error": "Admin access required"}, status_code=403)
    ip = request.client.host if request.client else "unknown"
    success, message = get_auth_service().reset_password(req.username, req.new_password, session["username"], ip_address=ip)
    if success: return {"success": True, "message": message}
    return JSONResponse({"success": False, "error": message}, status_code=400)


# ── Audit log ──

@router.get("/audit-log")
async def audit_log_page(request: Request):
    session = get_current_session(request)
    if not session: return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("audit_log.html", {
        "request": request, "username": session["username"],
        "event_types": EVENT_TYPES, "stats": get_audit_log().get_stats()})


@router.get("/api/audit-log/query")
async def audit_log_query(request: Request, event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None), username: Optional[str] = Query(None),
    search: Optional[str] = Query(None), start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None), limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0)):
    session = get_current_session(request)
    if not session: return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    entries, total = get_audit_log().query(event_type=event_type, severity=severity, username=username,
        search_text=search, start_date=start_date, end_date=end_date, limit=limit, offset=offset)
    return {"entries": entries, "total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total}


@router.get("/api/audit-log/stats")
async def audit_log_stats(request: Request):
    session = get_current_session(request)
    if not session: return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return get_audit_log().get_stats()


@router.get("/api/audit-log/export")
async def audit_log_export(request: Request, format: str = Query("json")):
    session = get_current_session(request)
    if not session: return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    entries, total = get_audit_log().query(limit=10000)
    if format == "csv":
        import csv, io
        output = io.StringIO()
        if entries:
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            for e in entries: writer.writerow({k: str(v) if not isinstance(v, str) else v for k, v in e.items()})
        from fastapi.responses import Response as RawResponse
        return RawResponse(content=output.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"})
    return JSONResponse({"entries": entries, "total": total})


# ── Sessions ──

@router.get("/api/auth/sessions")
async def active_sessions(request: Request):
    session = get_current_session(request)
    if not session: return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    sessions = get_auth_service().get_active_sessions()
    return {"sessions": [{"username": s["username"], "ip_address": s.get("ip_address", ""),
        "created_at": datetime.fromtimestamp(s["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": datetime.fromtimestamp(s["expires_at"]).strftime("%Y-%m-%d %H:%M:%S"),
        "is_current": request.cookies.get(SESSION_COOKIE_NAME) == s["token"]} for s in sessions], "count": len(sessions)}