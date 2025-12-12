from flask_smorest import Blueprint
from flask.views import MethodView

# Align name and description for OpenAPI tags
blp = Blueprint("Health", "Health", url_prefix="/", description="Health check and service status endpoints")


@blp.route("/")
class HealthCheck(MethodView):
    """Health check endpoint."""
    # PUBLIC_INTERFACE
    def get(self):
        """Return service health status."""
        return {"message": "Healthy"}
