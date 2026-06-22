"""
Token Savings Demo
==================
Before: full-context prompting — paste your entire codebase + conversation
        history into every prompt. Token costs compound every session.

After:  Memori — the SDK retrieves only the relevant memories and injects
        them automatically. Prompts stay lean no matter how long the project runs.

This demo simulates a realistic 4-session auth refactor and shows the numbers.
Run standalone:
    python demos/token_savings.py
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Realistic scenario: an auth refactor across 4 dev sessions
# ---------------------------------------------------------------------------

CODEBASE_DUMP = """\
# ============================================================
# auth/jwt.py
# ============================================================
import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)

SECRET_KEY = "hardcoded_secret_123"  # TODO: move to env — tracked in JIRA AUTH-41
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

def create_access_token(user_id: str, extra_claims: dict | None = None) -> str:
    now = datetime.utcnow()
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug("Created access token for user=%s exp=%s", user_id, payload["exp"])
    return token

def create_refresh_token(user_id: str, session_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
    if payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload

def hash_password(password: str) -> str:
    # TODO AUTH-42: migrate to bcrypt — currently MD5, do not ship to prod
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


# ============================================================
# auth/middleware.py
# ============================================================
import functools
from flask import g, request, jsonify
from auth.jwt import verify_token

def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = verify_token(token, expected_type="access")
            g.user_id = payload["sub"]
            g.token_payload = payload
        except ValueError as e:
            return jsonify({"error": str(e)}), 401
        return f(*args, **kwargs)
    return decorated

def require_role(*roles: str):
    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            user_roles = g.token_payload.get("roles", [])
            if not any(r in user_roles for r in roles):
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# auth/models.py
# ============================================================
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(32), nullable=False)  # MD5 — migrate to bcrypt (AUTH-42)
    display_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    roles = Column(Text, default="user")  # comma-separated role list

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def has_role(self, role: str) -> bool:
        return role in (self.roles or "").split(",")


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_refresh_token", "refresh_token"),
        Index("ix_user_sessions_user_id", "user_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String(512), nullable=True)
    refresh_token_expires = Column(DateTime, nullable=True)
    refresh_token_version = Column(String(36), nullable=True)  # for rotation tracking
    device_info = Column(String(255))
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    is_revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")


# ============================================================
# auth/service.py
# ============================================================
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from auth.jwt import create_access_token, create_refresh_token, hash_password, verify_password, verify_token
from auth.models import User, UserSession

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, email: str, password: str, display_name: str | None = None) -> User:
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError(f"Email already registered: {email}")
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info("Registered new user id=%s email=%s", user.id, email)
        return user

    def login(self, email: str, password: str, device_info: str = "", ip: str = "") -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is disabled")

        session = UserSession(user_id=user.id, device_info=device_info, ip_address=ip)
        self.db.add(session)
        user.last_login = datetime.utcnow()
        self.db.commit()

        access = create_access_token(user.id, extra_claims={"roles": user.roles})
        refresh = create_refresh_token(user.id, session_id=session.id)

        session.refresh_token = refresh
        session.refresh_token_expires = datetime.utcnow()  # TODO: set proper expiry
        self.db.commit()

        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

    def logout(self, session_id: str) -> None:
        session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.is_revoked = True
            session.refresh_token = None
            self.db.commit()


# ============================================================
# auth/routes.py
# ============================================================
from flask import Blueprint, g, jsonify, request
from database import get_db
from auth.service import AuthService
from auth.middleware import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    try:
        with get_db() as db:
            svc = AuthService(db)
            user = svc.register(email=email, password=password, display_name=data.get("name"))
        return jsonify({"id": user.id, "email": user.email}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    try:
        with get_db() as db:
            svc = AuthService(db)
            tokens = svc.login(
                email=data.get("email", "").strip().lower(),
                password=data.get("password", ""),
                device_info=request.headers.get("User-Agent", ""),
                ip=request.remote_addr or "",
            )
        return jsonify(tokens)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    session_id = g.token_payload.get("sid")
    if session_id:
        with get_db() as db:
            AuthService(db).logout(session_id)
    return jsonify({"message": "Logged out"}), 200

@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"user_id": g.user_id, "roles": g.token_payload.get("roles", "user")})


# ============================================================
# tests/test_auth.py  (existing suite — 47 tests, abbreviated)
# ============================================================
import pytest
from unittest.mock import patch, MagicMock
from auth.jwt import create_access_token, create_refresh_token, verify_token, hash_password

def test_create_access_token_contains_sub():
    token = create_access_token("user-123")
    payload = verify_token(token)
    assert payload["sub"] == "user-123"

def test_create_access_token_type_claim():
    token = create_access_token("user-123")
    payload = verify_token(token)
    assert payload["type"] == "access"

def test_verify_token_wrong_type_raises():
    token = create_access_token("user-123")
    with pytest.raises(ValueError, match="Expected token type"):
        verify_token(token, expected_type="refresh")

def test_expired_token_raises():
    with patch("auth.jwt.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
        token = create_access_token("user-expired")
    with pytest.raises(ValueError, match="expired"):
        verify_token(token)

def test_hash_password_deterministic():
    assert hash_password("secret") == hash_password("secret")

def test_hash_password_not_plaintext():
    assert hash_password("secret") != "secret"

# ... 41 more tests covering AuthService, routes, middleware, session management
"""

# Conversation history accumulates across sessions in the naive approach
SESSION_HISTORY: list[tuple[str, str]] = [
    (
        "What security issues exist in our auth module?",
        "Found three critical issues: (1) HS256 with hardcoded secret — anyone with the secret "
        "can forge tokens. Migrate to RS256 with env-loaded private key. (2) MD5 password hashing "
        "is cryptographically broken — switch to bcrypt with cost factor 12. (3) No refresh token "
        "rotation — a stolen refresh token is valid forever.",
    ),
    (
        "What's our migration plan for the JWT changes?",
        "Agreed plan: (1) Generate RSA-2048 keypair, store private key in SECRET_JWT_PRIVATE env "
        "var. (2) Add 15-minute access token TTL, 7-day refresh token TTL. (3) Implement refresh "
        "rotation — each use issues a new token and invalidates the old one. (4) Keep HS256 "
        "endpoint alive behind feature flag for 2-week deprecation window.",
    ),
    (
        "Reviewer flagged concurrent refresh — what did we decide?",
        "Decision: use optimistic locking on the refresh_token column with a version counter. "
        "First concurrent refresh wins; subsequent ones within the same 500ms window get a 409 "
        "and the client retries with the new token. Document this in the API error catalog.",
    ),
]

CURRENT_TASK = "Implement the refresh token rotation endpoint per our agreed spec."

SYSTEM_PROMPT_BASE = "You are a senior engineer helping with an auth module refactor."


# ---------------------------------------------------------------------------
# Token counting — use tiktoken when available, fall back to word estimate
# ---------------------------------------------------------------------------

def _make_counter():
    try:
        import tiktoken  # type: ignore[import]

        enc = tiktoken.encoding_for_model("gpt-4o-mini")

        def count(text: str) -> int:
            return len(enc.encode(text))

    except ImportError:

        def count(text: str) -> int:
            # ~1.3 tokens per word is a reasonable approximation for English code
            return int(len(text.split()) * 1.3)

    return count


count_tokens = _make_counter()


# ---------------------------------------------------------------------------
# Simulate both approaches
# ---------------------------------------------------------------------------

SessionResult = dict  # {"label", "tokens", "prompt_preview"}


def simulate_before() -> list[SessionResult]:
    """Naive: every session re-sends system prompt + full codebase + all history."""
    results = []
    history_text = ""

    for i, (question, answer) in enumerate(SESSION_HISTORY, 1):
        prompt = (
            f"{SYSTEM_PROMPT_BASE}\n\n"
            f"FULL CODEBASE:\n{CODEBASE_DUMP}\n\n"
            f"CONVERSATION HISTORY:\n{history_text}"
            f"USER: {question}\n"
        )
        tokens = count_tokens(prompt)
        results.append({"session": i, "label": question[:55], "tokens": tokens})
        history_text += f"USER: {question}\nASSISTANT: {answer}\n\n"

    # Final task session
    prompt = (
        f"{SYSTEM_PROMPT_BASE}\n\n"
        f"FULL CODEBASE:\n{CODEBASE_DUMP}\n\n"
        f"CONVERSATION HISTORY:\n{history_text}"
        f"USER: {CURRENT_TASK}\n"
    )
    results.append(
        {"session": len(SESSION_HISTORY) + 1, "label": CURRENT_TASK[:55], "tokens": count_tokens(prompt)}
    )
    return results


def simulate_after() -> list[SessionResult]:
    """Memori: each session sends only a lean prompt; the SDK injects relevant memories.

    Session 1 has no prior memories to recall, so Memori injects nothing.
    Sessions 2+ receive ~150 tokens of recalled context — only what's relevant,
    never the full history. This estimate is based on typical Memori injection size
    for a mature project; actual numbers vary with memory density.
    """
    results = []

    for i, (question, _) in enumerate(SESSION_HISTORY, 1):
        lean_prompt = f"{SYSTEM_PROMPT_BASE}\n\nUSER: {question}\n"
        # Session 1: no memories stored yet — Memori injects nothing.
        # Session 2+: Memori recalls only relevant context (~150 tokens typical).
        memori_injection = 0 if i == 1 else 150
        tokens = count_tokens(lean_prompt) + memori_injection
        results.append({"session": i, "label": question[:55], "tokens": tokens})

    lean_prompt = f"{SYSTEM_PROMPT_BASE}\n\nUSER: {CURRENT_TASK}\n"
    results.append(
        {
            "session": len(SESSION_HISTORY) + 1,
            "label": CURRENT_TASK[:55],
            "tokens": count_tokens(lean_prompt) + 150,
        }
    )
    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def run_demo() -> None:
    console.print()
    console.print(
        Panel(
            "[bold]Scenario:[/bold] 4-session auth module refactor\n"
            "[dim]BEFORE[/dim]  Re-sends full codebase + conversation history every session\n"
            "[dim]AFTER[/dim]   Memori recalls only what's relevant — prompts stay lean forever",
            title="[bold cyan]Token Savings Demo — Persistent Memory Dev Agents[/bold cyan]",
            border_style="cyan",
        )
    )

    before = simulate_before()
    after = simulate_after()

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("Task", width=56)
    table.add_column("Before", justify="right", style="red", width=8)
    table.add_column("After", justify="right", style="green", width=8)
    table.add_column("Saved", justify="right", style="bold green", width=7)

    total_before = 0
    total_after = 0

    for b, a in zip(before, after):
        saved_pct = int((b["tokens"] - a["tokens"]) / b["tokens"] * 100)
        table.add_row(
            str(b["session"]),
            b["label"] + ("…" if len(b["label"]) == 55 else ""),
            f"{b['tokens']:,}",
            f"{a['tokens']:,}",
            f"{saved_pct}%",
        )
        total_before += b["tokens"]
        total_after += a["tokens"]

    console.print()
    console.print(table)

    total_saved = total_before - total_after
    total_pct = int(total_saved / total_before * 100)

    # GPT-4o-mini input pricing: $0.15 / 1M tokens
    price_per_m = 0.15
    cost_before = total_before / 1_000_000 * price_per_m
    cost_after = total_after / 1_000_000 * price_per_m
    cost_saved = cost_before - cost_after

    # Scale-up estimate: 50 devs, 20 sessions/day
    daily_sessions = 50 * 20
    daily_saved = cost_saved * daily_sessions

    console.print()
    console.print(
        Panel(
            f"[red]BEFORE (full context):[/red]  {total_before:>7,} tokens   ${cost_before:.4f}\n"
            f"[green]AFTER  (Memori):[/green]        {total_after:>7,} tokens   ${cost_after:.4f}\n"
            f"[bold green]Reduction:[/bold green]              {total_pct}% fewer tokens   ${cost_saved:.4f} saved\n\n"
            f"[dim]At scale — 50 devs × 20 sessions/day: [bold]${daily_saved:.2f}/day[/bold] saved[/dim]",
            title="[bold]Summary[/bold]",
            border_style="green",
        )
    )
    console.print(
        "[dim]Token counts use tiktoken (gpt-4o-mini encoding) when installed, "
        "otherwise a word-count approximation.[/dim]\n"
    )


if __name__ == "__main__":
    run_demo()
