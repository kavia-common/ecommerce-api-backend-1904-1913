import os


class BaseConfig:
    """Base configuration for the Flask application."""
    # PUBLIC_INTERFACE
    DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes", "on")
    """Whether to run the application in debug mode (from env DEBUG, default False)."""

    # PUBLIC_INTERFACE
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    """Secret key for session signing and security (from env SECRET_KEY, dev default provided)."""

    # PUBLIC_INTERFACE
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "10"))
    """Default pagination size for list endpoints."""
