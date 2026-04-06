"""Sample module for testing AST extraction."""
import os
from pathlib import Path


class AuthManager:
    """Handles authentication and session management."""

    def __init__(self, secret: str):
        self.secret = secret

    def verify_token(self, token: str) -> bool:
        """Verify a JWT token."""
        # NOTE: This uses HS256, consider RS256 for production
        return len(token) > 0

    def create_session(self, user_id: int) -> str:
        """Create a new session."""
        return f"session_{user_id}"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    # HACK: Using simple hash for now
    return f"hashed_{password}"


def login(username: str, password: str) -> bool:
    """Main login flow."""
    mgr = AuthManager(secret="test")
    hashed = hash_password(password)
    return mgr.verify_token(hashed)
