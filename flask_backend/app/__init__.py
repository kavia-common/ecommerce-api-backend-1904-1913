from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from .config import BaseConfig
from .errors import register_error_handlers
from .routes.health import blp as health_blp
from .routes.auth import blp as auth_blp
from .routes.products import blp as products_blp
from .routes.cart import blp as cart_blp
from .services.storage import init_storage_seed  # Seed repositories at startup


def create_app():
    """Application factory that creates and configures the Flask app instance."""
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # Load configuration
    app.config.from_object(BaseConfig)

    # Enable CORS for all routes and origins
    CORS(app, resources={r"/*": {"origins": "*"}})

    # API metadata and OpenAPI settings
    API_DESCRIPTION = (
        "Ecommerce API backend providing endpoints for authentication, product catalog, "
        "shopping cart, and order management. Includes health check and standardized error responses."
    )
    app.config["API_TITLE"] = "Ecommerce API"
    app.config["API_VERSION"] = "v1"
    app.config["API_SPEC_OPTIONS"] = {
        "info": {"description": API_DESCRIPTION},
        "tags": [
            {"name": "Auth", "description": "Authentication related endpoints"},
            {"name": "Products", "description": "Product catalog and search"},
            {"name": "Cart", "description": "Shopping cart operations"},
            {"name": "Orders", "description": "Order submission and status"},
            {"name": "Health", "description": "Health check and service status"},
        ],
    }
    app.config["OPENAPI_VERSION"] = "3.0.3"
    # Keep OpenAPI JSON at default /openapi.json by not setting OPENAPI_URL_PREFIX for JSON
    # Expose Swagger UI at /docs
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Initialize API
    api = Api(app)

    # Register blueprints
    api.register_blueprint(health_blp)
    api.register_blueprint(auth_blp)
    api.register_blueprint(products_blp)
    api.register_blueprint(cart_blp)

    # Register global error handlers
    register_error_handlers(app)

    # Seed initial in-memory data
    with app.app_context():
        init_storage_seed()

    return app


# PUBLIC_INTERFACE
app = create_app()
"""WSGI application instance for running the Flask app."""
