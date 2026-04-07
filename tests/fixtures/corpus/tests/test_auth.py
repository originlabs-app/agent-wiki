"""Tests for the auth module."""
import time
from src.auth import User, Token, create_token, verify_token


def test_create_token():
    user = User(id="u1", email="test@example.com", role="admin", created_at=time.time())
    token = create_token(user, scope="read", ttl=3600)
    assert token.user_id == "u1"
    assert token.scope == "read"
    assert token.expires_at > time.time()


def test_verify_valid_token():
    user = User(id="u1", email="test@example.com", role="admin", created_at=time.time())
    token = create_token(user)
    assert verify_token(token) is True


def test_verify_expired_token():
    user = User(id="u1", email="test@example.com", role="admin", created_at=time.time())
    token = create_token(user, ttl=-1)  # expires in the past
    assert verify_token(token) is False
