"""Authentication utilities: token generation/verification and password hashing.

Uses itsdangerous URLSafeSerializer with the Flask app SECRET_KEY for simple signed tokens.
Password hashing uses Werkzeug security helpers.
"""

from __future__ import annotations

from typing import Optional

from flask import current_app
from itsdangerous import URLSafeSerializer, BadSignature
from werkzeug.security import generate_password_hash as _gen_hash, check_password_hash as _chk_hash


def _get_secret_key() -> str:
    """Internal helper to obtain SECRET_KEY from app config."""
    # PUBLIC_INTERFACE
    secret_key = None
    if current_app and current_app.config:
        secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        # Fallback default matches BaseConfig default; not recommended for production.
        secret_key = "dev-secret-key-change-me"
    return secret_key


def _get_serializer() -> URLSafeSerializer:
    """Create a serializer with the current SECRET_KEY and a fixed salt."""
    secret = _get_secret_key()
    # PUBLIC_INTERFACE
    return URLSafeSerializer(secret_key=secret, salt="auth-token")


# PUBLIC_INTERFACE
def generate_token(user_id: str) -> str:
    """Generate a signed access token for the given user_id.

    The token is a compact URL-safe string signed with SECRET_KEY.
    """
    s = _get_serializer()
    payload = {"sub": user_id}
    return s.dumps(payload)


# PUBLIC_INTERFACE
def verify_token(token: str) -> Optional[str]:
    """Verify a signed token and return the user_id if valid; otherwise None."""
    s = _get_serializer()
    try:
        data = s.loads(token)
        user_id = data.get("sub")
        if not isinstance(user_id, str):
            return None
        return user_id
    except BadSignature:
        return None
    except Exception:
        return None


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using Werkzeug's recommended defaults."""
    return _gen_hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its hash."""
    return _chk_hash(password_hash, password)
