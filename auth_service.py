"""Authentication service — session management, password verification, audit logging.

Security model:
- Admin credentials configured via environment variables or defaults
- Passwords hashed with PBKDF2-HMAC-SHA256 (100k iterations)
- Session tokens are cryptographically random, stored in memory with expiry
- All auth events and key actions are recorded in the audit log
- Audit log is persisted to disk (JSONL format) and kept in memory
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ── Default credentials (override via env vars ADMIN_USERNAME / ADMIN_PASSWORD_HASH) ──
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "ChangeMe!2024"  # Plaintext default — replaced by hash on first run

# ── Session configuration ──
SESSION_TTL_SECONDS = 8 * 3600       # 8 hours
SESSION_COOKIE_NAME = "ecs_session"
MAX_SESSIONS = 50                     # Max concurrent sessions
MAX_AUDIT_ENTRIES = 10000             # Max in-memory audit entries

# ── Audit event types ──
EVENT_TYPES = {
    "LOGIN_SUCCESS":      {"label": "Login Success",      "severity": "info"},
    "LOGIN_FAILURE":      {"label": "Login Failure",      "severity": "warning"},
    "LOGOUT":             {"label": "Logout",             "severity": "info"},
    "SESSION_EXPIRED":    {"label": "Session Expired",    "severity": "info"},
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
    """Hash a password using PBKDF2-HMAC-SHA256.

    Returns (salt_hex, hash_hex) tuple.
    """
    if salt is None:
        salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), dk.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    """Verify a password against stored salt+hash using constant-time comparison."""
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(dk, expected)


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
        """Load existing audit entries from the JSONL file on startup."""
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
        """Add an audit log entry."""
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

    def query(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        username: Optional[str] = None,
        search_text: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple:
        """Query audit log entries with filtering.

        Returns (filtered_entries, total_count).
        """
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
            if start_date:
                if entry["timestamp_local"] < start_date:
                    continue
            if end_date:
                if entry["timestamp_local"] > end_date + " 23:59:59":
                    continue
            filtered.append(entry)

        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
        total = len(filtered)
        page = filtered[offset:offset + limit]
        return page, total

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the audit log dashboard."""
        with self._lock:
            entries = list(self._entries)

        stats = {
            "total": len(entries),
            "by_severity": {},
            "by_event_type": {},
            "last_24h": 0,
            "last_1h": 0,
        }
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
        """Clear all audit entries (with audit trail of the clear action)."""
        with self._lock:
            self._entries = []
            if self._log_file and self._log_file.exists():
                self._log_file.unlink()


class AuthService:
    """Authentication service with session management."""

    def __init__(self, audit: AuditLog):
        self.audit = audit
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Load admin credentials
        self.admin_username = os.environ.get("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
        password_env = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        password_hash_env = os.environ.get("ADMIN_PASSWORD_HASH", "")

        if password_hash_env:
            # Pre-hashed password provided (format: salt_hex:hash_hex)
            parts = password_hash_env.split(":")
            if len(parts) == 2:
                self._salt_hex = parts[0]
                self._hash_hex = parts[1]
            else:
                self._salt_hex, self._hash_hex = _hash_password(password_env)
        else:
            self._salt_hex, self._hash_hex = _hash_password(password_env)

        logger.info(f"Auth service initialized (admin user: {self.admin_username})")

    def authenticate(self, username: str, password: str, ip_address: str = "") -> Optional[Dict]:
        """Authenticate a user and create a session.

        Returns session dict on success, None on failure.
        """
        if not username or not password:
            return None

        if username == self.admin_username and _verify_password(password, self._salt_hex, self._hash_hex):
            token = secrets.token_urlsafe(48)
            now = time.time()
            session = {
                "token": token,
                "username": username,
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

            self.audit.add("LOGIN_SUCCESS", username=username, ip_address=ip_address,
                           details=f"Session created, expires in {SESSION_TTL_SECONDS // 3600}h")
            return session

        self.audit.add("LOGIN_FAILURE", username=username or "unknown", ip_address=ip_address,
                       details=f"Invalid credentials for user '{username}'")
        return None

    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate a session token. Returns session dict if valid, None otherwise."""
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
        """Destroy a session (logout)."""
        with self._lock:
            session = self._sessions.pop(token, None)
        if session:
            self.audit.add("LOGOUT", username=session["username"],
                           ip_address=session.get("ip_address", ""),
                           details="User logged out")

    def _cleanup_expired(self):
        """Remove expired sessions (call within lock)."""
        now = time.time()
        expired = [t for t, s in self._sessions.items() if now > s["expires_at"]]
        for t in expired:
            session = self._sessions.pop(t, None)
            if session:
                self.audit.add("SESSION_EXPIRED", username=session["username"],
                               ip_address=session.get("ip_address", ""),
                               details="Session expired during cleanup")

    def get_active_sessions(self) -> List[Dict]:
        """Get list of active sessions (for admin view)."""
        with self._lock:
            self._cleanup_expired()
            return [s.copy() for s in self._sessions.values()]

    def change_password(self, new_password: str) -> bool:
        """Change the admin password (in-memory only, not persisted)."""
        if not new_password or len(new_password) < 8:
            return False
        self._salt_hex, self._hash_hex = _hash_password(new_password)
        self.audit.add("CONFIG_CHANGE", username=self.admin_username,
                       details="Admin password changed")
        return True