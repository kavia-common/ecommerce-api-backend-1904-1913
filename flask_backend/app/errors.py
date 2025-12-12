from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    # PUBLIC_INTERFACE
    def __init__(self, message="An error occurred", status_code=500, code=None, errors=None):
        """Generic API error with JSON representation."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code if code is not None else status_code
        self.errors = errors or {}

    # PUBLIC_INTERFACE
    def to_dict(self):
        """Serialize the error to a dictionary payload."""
        return {
            "code": self.code,
            "status": self._status_name(self.status_code),
            "message": self.message,
            "errors": self.errors,
        }

    @staticmethod
    def _status_name(status_code: int) -> str:
        try:
            from http import HTTPStatus
            return HTTPStatus(status_code).phrase
        except Exception:
            return "Error"


class NotFound(APIError):
    # PUBLIC_INTERFACE
    def __init__(self, message="Resource not found", errors=None):
        """404 not found API error."""
        super().__init__(message=message, status_code=404, errors=errors)


class BadRequest(APIError):
    # PUBLIC_INTERFACE
    def __init__(self, message="Bad request", errors=None):
        """400 bad request API error."""
        super().__init__(message=message, status_code=400, errors=errors)


class Unauthorized(APIError):
    # PUBLIC_INTERFACE
    def __init__(self, message="Unauthorized", errors=None):
        """401 unauthorized API error."""
        super().__init__(message=message, status_code=401, errors=errors)


# PUBLIC_INTERFACE
def register_error_handlers(app):
    """Register global JSON error handlers for common HTTP and API errors."""

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        response = jsonify(err.to_dict())
        response.status_code = err.status_code
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        payload = {
            "code": err.code or 500,
            "status": getattr(err, "name", "Error"),
            "message": err.description if hasattr(err, "description") else str(err),
            "errors": {},
        }
        response = jsonify(payload)
        response.status_code = err.code or 500
        return response

    @app.errorhandler(400)
    def handle_400(err):
        return handle_http_exception(err)

    @app.errorhandler(401)
    def handle_401(err):
        return handle_http_exception(err)

    @app.errorhandler(404)
    def handle_404(err):
        return handle_http_exception(err)

    @app.errorhandler(405)
    def handle_405(err):
        return handle_http_exception(err)

    @app.errorhandler(500)
    def handle_500(err):
        if isinstance(err, HTTPException):
            return handle_http_exception(err)
        api_err = APIError(message="Internal server error", status_code=500)
        return handle_api_error(api_err)
