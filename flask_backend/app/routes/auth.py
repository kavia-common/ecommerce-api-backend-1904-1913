"""Authentication routes and auth decorator for the Ecommerce API."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint

from ..errors import BadRequest, Unauthorized
from ..schemas.auth import LoginSchema, PublicUserSchema, RegisterSchema, TokenSchema
from ..services import auth as auth_service
from ..services.storage import get_users_repo

# Expose tag "Auth" routes under /auth
blp = Blueprint(
    "Auth",
    "Auth",
    url_prefix="/auth",
    description="Authentication related endpoints",
)


def _extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# PUBLIC_INTERFACE
def require_auth(fn: Callable) -> Callable:
    """Decorator that validates Authorization: Bearer <token> and injects current_user.

    On success:
    - Sets g.current_user to the user dict
    - Proceeds to the wrapped view

    On failure:
    - Raises Unauthorized API error (401)

    Usage:
        @require_auth
        def get(self):
            user = g.current_user
            ...
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = _extract_bearer_token(auth_header)
        if not token:
            raise Unauthorized("Missing or invalid Authorization header")
        user_id = auth_service.verify_token(token)
        if not user_id:
            raise Unauthorized("Invalid or expired token")

        user = get_users_repo().get(user_id)
        if not user:
            # Token valid but user not found (shouldn't happen often)
            raise Unauthorized("User not found")
        # Remove sensitive fields before storing on g
        user_public = {k: v for k, v in user.items() if k != "password_hash"}
        g.current_user = user_public
        return fn(*args, **kwargs)

    return wrapper


@blp.route("/register")
class Register(MethodView):
    """Register a new user."""

    @blp.arguments(RegisterSchema, location="json")
    @blp.response(201, PublicUserSchema)
    def post(self, json_data: dict):
        """Register a new user account.

        Request body:
        - email: string (email)
        - password: string (8-128)
        - name: string

        Returns: Public user object (no password hash).
        """
        email = json_data["email"]
        password = json_data["password"]
        name = json_data["name"]

        users = get_users_repo()
        # Use services.auth for hashing to keep consistency
        password_hash = auth_service.hash_password(password)

        try:
            user = users.create(email=email, name=name, password_hash=password_hash)
        except ValueError as e:
            # Likely email already registered
            raise BadRequest(str(e))

        # Strip sensitive fields
        user_public = {k: v for k, v in user.items() if k != "password_hash"}
        return user_public


@blp.route("/login")
class Login(MethodView):
    """Authenticate a user and return an access token."""

    @blp.arguments(LoginSchema, location="json")
    @blp.response(200, TokenSchema)
    def post(self, json_data: dict):
        """Authenticate user with email and password.

        Returns:
        - access_token: opaque signed token
        - token_type: 'Bearer'
        - expires_in: seconds (non-expiring demo token -> return large constant)
        """
        email = json_data["email"]
        password = json_data["password"]

        users = get_users_repo()
        user = users.get_by_email(email)
        if not user:
            # To avoid user enumeration, keep generic message
            raise Unauthorized("Invalid credentials")

        if not auth_service.verify_password(password, user["password_hash"]):
            raise Unauthorized("Invalid credentials")

        token = auth_service.generate_token(user_id=user["id"])
        # Demo tokens are not expiring; provide a conventional large TTL
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 24 * 3600,  # 24 hours nominal
        }


@blp.route("/me")
class Me(MethodView):
    """Get current authenticated user's profile."""

    @require_auth
    @blp.response(200, PublicUserSchema)
    def get(self):
        """Return the current authenticated user's public profile."""
        return g.current_user
