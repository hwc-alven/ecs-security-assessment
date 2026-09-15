"""Authentication service — multi-user support, session management, audit logging.

Security model:
- Users stored in JSON file on disk (data/auth/users.json)
- Passwords hashed with PBKDF2-HMAC-SHA256 (100k iterations)
- Session tokens are cryptographically random, stored in memory with expiry
- Registration requires an invite code (configurable via env var)
- First registered user auto-promoted to admin if no admin exists
- All auth events recorded in audit log (JSONL persisted to disk)
"""
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "ChangeMe!2024"

SESSION_TTL_SECONDS = 8 * 3600
SESSION_COOKIE_NAME = "ecs_session"
MAX_SESSIONS = 50
MAX_AUDIT_ENTRIES = 10000

REGISTRATION_INVITE_CODE = os.environ.get("REGISTRATION_INVITE_CODE", "ECS-SECURE-2024")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{3,32}$")

EVENT_TYPES = {
    "LOGIN_SUCCESS":      {"label": "Login Success",      "severity": "info"},
    "LOGIN_FAILURE":      {"label": "Login Failure",      "severity": "warning"},
    "LOGOUT":             {"label": "Logout",             "severity": "info"},
    "SESSION_EXPIRED":    {"label": "Session Expired",    "severity": "info"},
    "USER_REGISTER":      {"label": "User Registered",    "severity": "warning"},
    "PASSWORD_CHANGE":    {"label": "Password Changed",   "severity": "warning"},
    "PASSWORD_RESET":     {"label": "Password Reset",     "severity": "warning"},
    "USER_DEACTIVATED":   {"label": "User Deactivated",   "severity": "error"},
    "USER_ACTIVATED":     {"label": "User Activated",     "severity": "info"},
    "ASSESSMENT_START":   {"label": "Assessment Started", "severity": "info"},
    "ASSESSMENT_COMPLETE":{"label": "Assessment Complete","severity": "info"},
    "ASSESSMENT_CANCEL":  {"label": "Assessment Cancelled","severity": "warning"},
    "ASSESSMENT_FAIL":    {"label": "Assessment Failed",  "severity": "error"},
    "KEYPAIR_GENERATE":   {"label": "Keypair Generated",  "severity": "warning"},
    "SERVER_ADD":         {"label": "Server Added",       "severity": "info"},
    "SERVER_REMOVE":      {"label": "Server Removed",     "severity": "warning"},
    "LLM_CONFIG_UPDATE":  {"label": "LLM Config Updated", "severity": "warning"},
    "LLM_CONFIG_VERIFY":  {"label": "LLM Config Verified","severity": "info"},
    "REPORT_VIEW":        {"label": "Report Viewed",      "severity": "info"},
    "REPORT_DOWNLOAD":    {"label": "Report Downloaded",  "severity": "info"},
    "CHECKLIST_UPLOAD":   {"label": "Checklist Uploaded", "severity": "info"},
    "CHECKLIST_ANALYZE":  {"label": "Checklist Analyzed", "severity": "info"},
    "BENCHMARK_VIEW":     {"label": "Benchmark Viewed",   "severity": "info"},
    "CONFIG_CHANGE":      {"label": "Configuration Changed","severity": "warning"},
}


def _hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    if salt is None:
        salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), dk.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(dk, expected)


def _validate_password_strength(password: str) -> Optional[str]:
    """Validate password strength. Returns error message or None if valid."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return "Password must contain at least one special character"
    return None


def _validate_username(username: str) -> Optional[str]:
    """Validate username format. Returns error message or None if valid."""
    if not USERNAME_PATTERN.match(username):
        return "Username must be 3-32 characters, alphanumeric/underscore/hyphen only"
    return None


class AuditLog:
    """In-memory + file-persisted audit log with filtering support."""

    def __init__(self, log_file: Optional[Path] = None, max_entries: int = MAX_AUDIT_ENTRIES):
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._log_file = log_file
        self._max_entries = max_entries
        if log_file:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def _load_from_disk(self):
        if not self._log_file or not self._log_file.exists():
            return
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self._entries.append(entry)
            logger.info(f"Loaded {len(self._entries)} audit entries from disk")
        except Exception as e:
            logger.warning(f"Failed to load audit log from disk: {e}")

    def add(self, event_type: str, username: str = "system",
            ip_address: str = "", details: str = "", extra: Optional[Dict] = None):
        if event_type not in EVENT_TYPES:
            severity = "info"
        else:
            severity = EVENT_TYPES[event_type]["severity"]

        entry = {
            "id": len(self._entries) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timestamp_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "event_label": EVENT_TYPES.get(event_type, {}).get("label", event_type),
            "severity": severity,
            "username": username,
            "ip_address": ip_address,
            "details": details,
            "extra": extra or {},
        }

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]
            if self._log_file:
                try:
                    with open(self._log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.warning(f"Failed to write audit entry to disk: {e}")

        logger.info(f"AUDIT [{event_type}] user={username} ip={ip_address} details={details}")

    def query(self, event_type=None, severity=None, username=None,
              search_text=None, start_date=None, end_date=None,
              limit=200, offset=0):
        with self._lock:
            entries = list(self._entries)

        filtered = []
        for entry in entries:
            if event_type and entry["event_type"] != event_type:
                continue
            if severity and entry["severity"] != severity:
                continue
            if username and entry["username"] != username:
                continue
            if search_text:
                searchable = f"{entry['event_type']} {entry['event_label']} {entry['username']} {entry['details']} {entry.get('extra', '')}"
                if search_text.lower() not in searchable.lower():
                    continue
            if start_date and entry["timestamp_local"] < start_date:
                continue
            if end_date and entry["timestamp_local"] > end_date + " 23:59:59":
                continue
            filtered.append(entry)

        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        total = len(filtered)
        page = filtered[offset:offset + limit]
        return page, total

    def get_stats(self):
        with self._lock:
            entries = list(self._entries)
        stats = {"total": len(entries), "by_severity": {}, "by_event_type": {},
                 "last_24h": 0, "last_1h": 0}
        now = time.time()
        for entry in entries:
            sev = entry["severity"]
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
            et = entry["event_type"]
            stats["by_event_type"][et] = stats["by_event_type"].get(et, 0) + 1
            try:
                ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                if now - ts < 86400:
                    stats["last_24h"] += 1
                if now - ts < 3600:
                    stats["last_1h"] += 1
            except Exception:
                pass
        return stats

    def clear(self):
        with self._lock:
            self._entries = []
            if self._log_file and self._log_file.exists():
                self._log_file.unlink()


class UserStore:
    """Multi-user store persisted to JSON file on disk."""

    def __init__(self, users_file: Path):
        self._file = users_file
        self._lock = threading.Lock()
        self._users: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._users = data.get("users", {})
                logger.info(f"Loaded {len(self._users)} users from {self._file}")
            except Exception as e:
                logger.warning(f"Failed to load users file: {e}")
                self._users = {}

    def _save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump({"users": self._users}, f, indent=2, ensure_ascii=False)
            self._file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save users file: {e}")

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._users.get(username)

    def list_users(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "username": u,
                    "role": d.get("role", "user"),
                    "created_at": d.get("created_at", ""),
                    "is_active": d.get("is_active", True),
                    "last_login": d.get("last_login", ""),
                }
                for u, d in self._users.items()
            ]

    def add_user(self, username: str, password: str, role: str = "user") -> bool:
        with self._lock:
            if username in self._users:
                return False
            salt_hex, hash_hex = _hash_password(password)
            self._users[username] = {
                "salt_hex": salt_hex,
                "hash_hex": hash_hex,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "last_login": "",
            }
            self._save()
            return True

    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self._users.get(username)
            if not user or not user.get("is_active", True):
                return None
            if _verify_password(password, user["salt_hex"], user["hash_hex"]):
                return {"username": username, "role": user.get("role", "user")}
            return None

    def change_password(self, username: str, new_password: str) -> bool:
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False
            salt_hex, hash_hex = _hash_password(new_password)
            user["salt_hex"] = salt_hex
            user["hash_hex"] = hash_hex
            user["password_changed_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return True

    def verify_password(self, username: str, password: str) -> bool:
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False
            return _verify_password(password, user["salt_hex"], user["hash_hex"])

    def update_last_login(self, username: str):
        with self._lock:
            user = self._users.get(username)
            if user:
                user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save()

    def set_active(self, username: str, is_active: bool) -> bool:
        with self._lock:
            user = self._users.get(username)
            if not user:
                return False
            user["is_active"] = is_active
            self._save()
            return True

    def has_admin(self) -> bool:
        with self._lock:
            return any(u.get("role") == "admin" for u in self._users.values())

    def count(self) -> int:
        with self._lock:
            return len(self._users)


class AuthService:
    """Authentication service with multi-user support and session management."""

    def __init__(self, audit: AuditLog, users_file: Optional[Path] = None):
        self.audit = audit
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        self._user_store = UserStore(users_file) if users_file else None

        self._default_admin = os.environ.get("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
        password_env = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        self._default_salt, self._default_hash = _hash_password(password_env)

        if self._user_store and not self._user_store.has_admin():
            if not self._user_store.get_user(self._default_admin):
                self._user_store.add_user(self._default_admin, password_env, role="admin")
                logger.info(f"Created default admin user '{self._default_admin}' in user store")

        logger.info(f"Auth service initialized (users: {self._user_store.count() if self._user_store else 'single-admin mode'})")

    def authenticate(self, username: str, password: str, ip_address: str = "") -> Optional[Dict]:
        if not username or not password:
            return None

        user_info = None

        if self._user_store:
            user_info = self._user_store.verify_user(username, password)
        elif username == self._default_admin and _verify_password(password, self._default_salt, self._default_hash):
            user_info = {"username": username, "role": "admin"}

        if user_info:
            token = secrets.token_urlsafe(48)
            now = time.time()
            session = {
                "token": token,
                "username": username,
                "role": user_info.get("role", "user"),
                "created_at": now,
                "expires_at": now + SESSION_TTL_SECONDS,
                "ip_address": ip_address,
            }
            with self._lock:
                self._cleanup_expired()
                self._sessions[token] = session
                if len(self._sessions) > MAX_SESSIONS:
                    oldest = min(self._sessions, key=lambda t: self._sessions[t]["created_at"])
                    del self._sessions[oldest]

            if self._user_store:
                self._user_store.update_last_login(username)

            self.audit.add("LOGIN_SUCCESS", username=username, ip_address=ip_address,
                           details=f"Session created, role={user_info.get('role', 'user')}, expires in {SESSION_TTL_SECONDS // 3600}h")
            return session

        self.audit.add("LOGIN_FAILURE", username=username or "unknown", ip_address=ip_address,
                       details=f"Invalid credentials for user '{username}'")
        return None

    def register_user(self, username: str, password: str, invite_code: str,
                      ip_address: str = "") -> tuple:
        """Register a new user. Returns (success: bool, error: str)."""
        if not self._user_store:
            return False, "User registration is not available in single-admin mode"

        if invite_code != REGISTRATION_INVITE_CODE:
            self.audit.add("LOGIN_FAILURE", username=username or "unknown", ip_address=ip_address,
                           details="Registration failed: invalid invite code")
            return False, "Invalid registration invite code"

        username_err = _validate_username(username)
        if username_err:
            return False, username_err

        password_err = _validate_password_strength(password)
        if password_err:
            return False, password_err

        if self._user_store.get_user(username):
            return False, "Username already exists"

        role = "admin" if not self._user_store.has_admin() else "user"

        if self._user_store.add_user(username, password, role=role):
            self.audit.add("USER_REGISTER", username=username, ip_address=ip_address,
                           details=f"New user registered with role={role}")
            return True, f"User '{username}' registered successfully with role '{role}'"
        return False, "Failed to create user"

    def change_password(self, username: str, current_password: str,
                        new_password: str, ip_address: str = "") -> tuple:
        """Change a user's password. Returns (success: bool, error: str)."""
        password_err = _validate_password_strength(new_password)
        if password_err:
            return False, password_err

        if new_password == current_password:
            return False, "New password must be different from current password"

        if self._user_store:
            if not self._user_store.verify_password(username, current_password):
                return False, "Current password is incorrect"
            if self._user_store.change_password(username, new_password):
                self.audit.add("PASSWORD_CHANGE", username=username, ip_address=ip_address,
                               details="Password changed successfully")
                return True, "Password changed successfully"
            return False, "User not found"
        else:
            if not _verify_password(current_password, self._default_salt, self._default_hash):
                return False, "Current password is incorrect"
            self._default_salt, self._default_hash = _hash_password(new_password)
            self.audit.add("PASSWORD_CHANGE", username=username, ip_address=ip_address,
                           details="Password changed successfully")
            return True, "Password changed successfully"

    def reset_password(self, username: str, new_password: str,
                       reset_by: str, ip_address: str = "") -> tuple:
        """Admin reset of a user's password. Returns (success: bool, error: str)."""
        if not self._user_store:
            return False, "Password reset is not available in single-admin mode"

        password_err = _validate_password_strength(new_password)
        if password_err:
            return False, password_err

        if not self._user_store.get_user(username):
            return False, "User not found"

        if self._user_store.change_password(username, new_password):
            self.audit.add("PASSWORD_RESET", username=username, ip_address=ip_address,
                           details=f"Password reset by admin '{reset_by}'")
            return True, f"Password reset successfully for user '{username}'"
        return False, "Failed to reset password"

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information for the account page."""
        if self._user_store:
            user = self._user_store.get_user(username)
            if user:
                return {
                    "username": username,
                    "role": user.get("role", "user"),
                    "created_at": user.get("created_at", ""),
                    "last_login": user.get("last_login", ""),
                    "is_active": user.get("is_active", True),
                    "password_changed_at": user.get("password_changed_at", ""),
                }
        elif username == self._default_admin:
            return {
                "username": username,
                "role": "admin",
                "created_at": "",
                "last_login": "",
                "is_active": True,
                "password_changed_at": "",
            }
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        if self._user_store:
            return self._user_store.list_users()
        return [{"username": self._default_admin, "role": "admin",
                 "created_at": "", "is_active": True, "last_login": ""}]

    def validate_session(self, token: str) -> Optional[Dict]:
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if not session:
                return None
            if time.time() > session["expires_at"]:
                del self._sessions[token]
                self.audit.add("SESSION_EXPIRED", username=session["username"],
                               ip_address=session.get("ip_address", ""),
                               details="Session expired due to TTL")
                return None
            return session.copy()

    def destroy_session(self, token: str):
        with self._lock:
            session = self._sessions.pop(token, None)
        if session:
            self.audit.add("LOGOUT", username=session["username"],
                           ip_address=session.get("ip_address", ""),
                           details="User logged out")

    def _cleanup_expired(self):
        now = time.time()
        expired = [t for t, s in self._sessions.items() if now > s["expires_at"]]
        for t in expired:
            session = self._sessions.pop(t, None)
            if session:
                self.audit.add("SESSION_EXPIRED", username=session["username"],
                               ip_address=session.get("ip_address", ""),
                               details="Session expired during cleanup")

    def get_active_sessions(self) -> List[Dict]:
        with self._lock:
            self._cleanup_expired()
            return [s.copy() for s in self._sessions.values()]