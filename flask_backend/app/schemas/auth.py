"""Authentication related Marshmallow schemas."""

from marshmallow import Schema, fields, validate


# PUBLIC_INTERFACE
class RegisterSchema(Schema):
    """Request payload to register a new user."""

    email = fields.Email(
        required=True,
        description="Email address of the user.",
        example="user@example.com",
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, max=128),
        description="User password (8-128 chars).",
        example="P@ssw0rd!",
    )
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=120),
        description="Full name of the user.",
        example="Jane Doe",
    )


# PUBLIC_INTERFACE
class LoginSchema(Schema):
    """Request payload to authenticate an existing user."""

    email = fields.Email(
        required=True,
        description="Email address used for login.",
        example="user@example.com",
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, max=128),
        description="User password.",
        example="P@ssw0rd!",
    )


# PUBLIC_INTERFACE
class PublicUserSchema(Schema):
    """Public representation of a user."""

    id = fields.String(required=True, description="User identifier.", example="usr_123")
    email = fields.Email(required=True, description="User email address.")
    name = fields.String(required=True, description="Full name of the user.")
    created_at = fields.DateTime(required=True, description="User creation timestamp (ISO8601).")


# PUBLIC_INTERFACE
class TokenSchema(Schema):
    """Authentication token response."""

    access_token = fields.String(
        required=True,
        description="JWT or opaque access token.",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
    token_type = fields.String(
        required=True,
        description="Type of the token.",
        example="Bearer",
    )
    expires_in = fields.Integer(
        required=True,
        description="Token expiry in seconds.",
        example=3600,
    )


# PUBLIC_INTERFACE
class RefreshTokenSchema(Schema):
    """Refresh token request or response."""

    refresh_token = fields.String(
        required=True,
        description="Refresh token used to obtain a new access token.",
        example="rfr_abc123",
    )
