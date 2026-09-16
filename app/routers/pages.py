# AI生成
"""Page routes — render HTML templates for the web console."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATE_DIR, state, AVAILABLE_MODELS

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard / home page."""
    return templates.TemplateResponse(request, "index.html", {
        "keypair_exists": state.keypair is not None,
        "server_count": len(state.servers),
        "task_count": len(state.tasks),
        "llm_configured": bool(state.llm_config.api_key),
    })


@router.get("/keypair", response_class=HTMLResponse)
async def keypair_page(request: Request):
    """Keypair generation and management page."""
    public_key = ""
    instructions = ""
    if state.keypair:
        public_key = state.keypair[1]  # public_key string
    return templates.TemplateResponse(request, "keypair.html", {
        "public_key": public_key,
        "keypair_exists": state.keypair is not None,
    })


@router.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request):
    """Server management page."""
    return templates.TemplateResponse(request, "servers.html", {
        "servers": state.servers,
        "keypair_exists": state.keypair is not None,
    })


@router.get("/assessment", response_class=HTMLResponse)
async def assessment_page(request: Request):
    """Assessment execution page."""
    return templates.TemplateResponse(request, "assessment.html", {
        "servers": state.servers,
        "tasks": state.tasks,
        "llm_configured": bool(state.llm_config.api_key),
        "custom_checklists": state.custom_checklists,
    })


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """LLM configuration page."""
    return templates.TemplateResponse(request, "config.html", {
        "llm_config": state.llm_config,
        "available_models": AVAILABLE_MODELS,
    })


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    """Report viewing page."""
    return templates.TemplateResponse(request, "report.html", {
        "tasks": state.tasks,
    })


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    """Account settings page."""
    return templates.TemplateResponse(request, "account.html", {
        "username": "admin",
        "user_info": {
            "role": "admin",
            "created_at": None,
            "last_login": None,
            "password_changed_at": None,
            "is_active": True,
        },
    })


@router.get("/regcodes", response_class=HTMLResponse)
async def regcodes_page(request: Request):
    """Registration code management page."""
    return templates.TemplateResponse(request, "regcodes.html", {})
