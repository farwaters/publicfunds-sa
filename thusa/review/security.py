"""Credentials, sessions, CSRF and login rate limiting for the review app. Standard library only.

- Passwords: scrypt (N=2^15, r=8, p=1, 16-byte salt), verified in constant time.
- API tokens: 256-bit random `pfr_...`; only their SHA-256 is stored (high-entropy, so a fast hash is fine).
- Sessions: 256-bit random cookie value; only its SHA-256 is stored. Idle timeout 2 h, absolute 12 h.
- CSRF: per-session synchroniser token on every state-changing form; login uses a double-submit cookie.
- Rate limiting: 5 failed logins per username or 20 per client IP within 15 minutes -> HTTP 429.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1
USERNAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,31}$")
PASSWORD_MIN = 12
SESSION_IDLE = timedelta(hours=2)
SESSION_MAX = timedelta(hours=12)
RATE_WINDOW = timedelta(minutes=15)
MAX_FAILS_USER, MAX_FAILS_IP = 5, 20
TOKEN_PREFIX = "pfr_"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def valid_username(u: str) -> bool:
    return bool(USERNAME_RE.match(u or ""))


def generate_password() -> str:
    return secrets.token_urlsafe(18)          # 24 chars, 144 bits


def hash_password(password: str) -> str:
    if len(password) < PASSWORD_MIN:
        raise ValueError(f"password must be at least {PASSWORD_MIN} characters")
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=2 ** 26, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(dk)}"


_DUMMY = None


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check. With stored=None (unknown user) a dummy hash is still computed to equalise timing."""
    global _DUMMY
    if stored is None:
        _DUMMY = _DUMMY or hash_password("dummy-password-for-timing")
        stored, password = _DUMMY, password + "\x00never"
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        cand = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), maxmem=2 ** 26,
                              dklen=len(_unb64(dk)))
        return hmac.compare_digest(cand, _unb64(dk))
    except (ValueError, TypeError):
        return False


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def new_session() -> tuple[str, str, str]:
    """(cookie value, its hash for storage, csrf token)."""
    raw = secrets.token_urlsafe(32)
    return raw, sha256_hex(raw), secrets.token_urlsafe(32)


def session_valid(sess: dict | None, now: datetime | None = None) -> bool:
    if not sess or sess["revoked"] or not sess["active"]:
        return False
    now = now or datetime.now(timezone.utc)
    created = datetime.fromisoformat(sess["created_at_utc"].replace("Z", "+00:00"))
    seen = datetime.fromisoformat(sess["last_seen_utc"].replace("Z", "+00:00"))
    return now - created < SESSION_MAX and now - seen < SESSION_IDLE


def same(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(str(a), str(b))


def rate_limited(store, username: str, ip: str, now: datetime | None = None) -> bool:
    since = ((now or datetime.now(timezone.utc)) - RATE_WINDOW).isoformat(timespec="seconds").replace("+00:00", "Z")
    return (store.failures_since(f"user:{username}", since) >= MAX_FAILS_USER
            or store.failures_since(f"ip:{ip}", since) >= MAX_FAILS_IP)
