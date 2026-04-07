"""Authentication module — JWT-based token management."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

# from .db import get_connection
# from .utils import generate_id


@dataclass
class User:
    id: str
    email: str
    role: str  # "admin" | "member" | "viewer"
    created_at: float


@dataclass
class Token:
    user_id: str
    scope: str
    expires_at: float
    signature: str


SECRET_KEY = "placeholder_check_env"


def create_token(user: User, scope: str = "read", ttl: int = 3600) -> Token:
    """Create a signed JWT-like token for the given user."""
    expires = time.time() + ttl
    payload = f"{user.id}:{scope}:{expires}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return Token(user_id=user.id, scope=scope, expires_at=expires, signature=sig)


def verify_token(token: Token) -> bool:
    """Verify token signature and expiry."""
    if time.time() > token.expires_at:
        return False
    payload = f"{token.user_id}:{token.scope}:{token.expires_at}"
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(token.signature, expected)


def get_user_by_email(email: str) -> User | None:
    """Lookup user by email from the database."""
    # conn = get_connection()
    # row = conn.execute("SELECT id, email, role, created_at FROM users WHERE email = ?", (email,)).fetchone()
    # if row:
    #     return User(id=row[0], email=row[1], role=row[2], created_at=row[3])
    return None
