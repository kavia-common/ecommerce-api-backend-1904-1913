from flask_smorest import Blueprint
from flask.views import MethodView

# Blueprint for health with consistent OpenAPI tag "Health"
blp = Blueprint(
    "Health",
    "Health",
    url_prefix="/",
    description="Health check and service status",
)


@blp.route("/")
class HealthCheck(MethodView):
    """Health check endpoint that reports service status."""
    # PUBLIC_INTERFACE
    def get(self):
        """Return service health status.

        This endpoint can be used by load balancers and uptime monitors to verify that
        the API process is running and able to serve requests.
        """
        return {"message": "Healthy"}
