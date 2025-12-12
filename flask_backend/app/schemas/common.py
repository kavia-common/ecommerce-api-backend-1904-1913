"""Common reusable Marshmallow schemas for the Ecommerce API."""

from marshmallow import Schema, fields, validate


# PUBLIC_INTERFACE
class IdSchema(Schema):
    """Schema representing an object identifier."""

    id = fields.String(
        required=True,
        description="Unique identifier of the resource",
        validate=validate.Length(min=1),
        example="prod_12345",
    )


# PUBLIC_INTERFACE
class PaginationQuerySchema(Schema):
    """Query parameters for paginated endpoints."""

    page = fields.Integer(
        required=False,
        missing=1,
        load_default=1,
        validate=validate.Range(min=1),
        description="Page number (1-indexed).",
        example=1,
    )
    page_size = fields.Integer(
        required=False,
        allow_none=True,
        validate=validate.Range(min=1, max=200),
        description="Number of items per page. If not provided, the server default will be used.",
        example=20,
    )
    q = fields.String(
        required=False,
        allow_none=True,
        description="Optional free-text search query.",
        example="wireless mouse",
    )
    sort = fields.String(
        required=False,
        allow_none=True,
        description="Optional sort parameter, e.g., 'price_asc', 'price_desc', 'created_desc'.",
        example="price_asc",
    )


# PUBLIC_INTERFACE
class PaginationMetadataSchema(Schema):
    """Pagination metadata returned along with list results."""

    total = fields.Integer(required=True, description="Total number of items.")
    total_pages = fields.Integer(required=True, description="Total number of pages.")
    first_page = fields.Integer(required=True, description="First page number (always 1).")
    last_page = fields.Integer(required=True, description="Last page number.")
    page = fields.Integer(required=True, description="Current page number.")
    previous_page = fields.Integer(
        allow_none=True, description="Previous page number if any, else null."
    )
    next_page = fields.Integer(
        allow_none=True, description="Next page number if any, else null."
    )
