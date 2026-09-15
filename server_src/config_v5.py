"""Application configuration and per-user state management."""
import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
REPORT_DIR = DATA_DIR / "reports"
KEYPAIR_DIR = DATA_DIR / "keypair"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = BASE_DIR / "static"
AUDIT_LOG_FILE = DATA_DIR / "audit" / "audit.jsonl"
USERS_FILE = DATA_DIR / "auth" / "users.json"
REGCODES_FILE = DATA_DIR / "auth" / "registration_codes.json"
USER_DATA_DIR = DATA_DIR / "users"

AVAILABLE_MODELS = ["glm-5.2", "deepseek-v4-flash", "deepseek-v4-pro", "qwen3-32b"]


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://api-ap-southeast-1.modelarts-maas.com/v2"
    model: str = "glm-5.2"
    temperature: float = 0.1
    rag_enabled: bool = True


@dataclass
class AppState:
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    keypair: Optional[tuple] = None
    servers: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    custom_checklists: list = field(default_factory=list)


class UserStateStore:
    """Manages per-user AppState instances with persistence."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._states: Dict[str, AppState] = {}

    def _user_dir(self, username: str) -> Path:
        safe = "".join(c for c in username if c.isalnum() or c in ('-', '_', '.'))
        d = self.base_dir / safe
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_state(self, username: str) -> AppState:
        if username not in self._states:
            self._states[username] = self._load_or_create(username)
        return self._states[username]

    def _load_or_create(self, username: str) -> AppState:
        from .services.keypair_service import load_keypair_from_disk
        st = AppState()
        ud = self._user_dir(username)

        kp_dir = ud / "keypair"
        saved = load_keypair_from_disk(kp_dir)
        if saved:
            st.keypair = (saved["private_key"], saved["public_key"])

        cfg_file = ud / "config" / "llm_config.json"
        if cfg_file.exists():
            try:
                data = json.loads(cfg_file.read_text(encoding="utf-8"))
                st.llm_config = LLMConfig(**data)
            except Exception:
                pass

        srv_file = ud / "servers.json"
        if srv_file.exists():
            try:
                st.servers = json.loads(srv_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        logger.info("Loaded state for user '%s' (servers=%d, keypair=%s, llm=%s)",
                     username, len(st.servers),
                     bool(st.keypair), bool(st.llm_config.api_key))
        return st

    def save_keypair(self, username: str, keypair_result: dict):
        from .services.keypair_service import save_keypair_to_disk
        kp_dir = self._user_dir(username) / "keypair"
        save_keypair_to_disk(keypair_result, kp_dir)

    def save_llm_config(self, username: str, config: LLMConfig):
        cfg_dir = self._user_dir(username) / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "llm_config.json"
        cfg_file.write_text(json.dumps({
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
            "temperature": config.temperature,
            "rag_enabled": config.rag_enabled,
        }), encoding="utf-8")
        try:
            cfg_file.chmod(0o600)
        except Exception:
            pass

    def save_servers(self, username: str, servers: list):
        srv_file = self._user_dir(username) / "servers.json"
        srv_file.write_text(json.dumps(servers), encoding="utf-8")
        try:
            srv_file.chmod(0o600)
        except Exception:
            pass

    def get_report_dir(self, username: str) -> Path:
        rd = self._user_dir(username) / "reports"
        rd.mkdir(parents=True, exist_ok=True)
        return rd

    def get_keypair_dir(self, username: str) -> Path:
        kd = self._user_dir(username) / "keypair"
        kd.mkdir(parents=True, exist_ok=True)
        return kd


user_state_store = UserStateStore(USER_DATA_DIR)