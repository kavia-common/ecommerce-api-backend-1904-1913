"""Product related Marshmallow schemas."""

from marshmallow import Schema, fields, validate
from .common import PaginationMetadataSchema


# PUBLIC_INTERFACE
class ProductCreateSchema(Schema):
    """Request payload to create a product."""

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
        description="Product name.",
        example="Wireless Mouse",
    )
    description = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=5000),
        description="Detailed product description.",
        example="Ergonomic wireless mouse with adjustable DPI.",
    )
    price = fields.Decimal(
        required=True,
        as_string=True,
        validate=validate.Range(min=0),
        description="Unit price as decimal string.",
        example="29.99",
    )
    currency = fields.String(
        required=True,
        validate=validate.Length(equal=3),
        description="ISO 4217 currency code.",
        example="USD",
    )
    sku = fields.String(
        required=True,
        validate=validate.Length(min=1, max=64),
        description="Stock keeping unit identifier.",
        example="WM-001-BLK",
    )
    inventory = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
        description="Available inventory count.",
        example=100,
    )
    image_url = fields.Url(
        required=False,
        allow_none=True,
        description="Primary product image URL.",
        example="https://cdn.example.com/products/wm-001.png",
    )
    active = fields.Boolean(
        required=False,
        missing=True,
        load_default=True,
        description="Whether the product is active/visible.",
        example=True,
    )
    tags = fields.List(
        fields.String(validate=validate.Length(min=1, max=32)),
        required=False,
        allow_none=True,
        description="Optional list of product tags.",
        example=["electronics", "mouse", "wireless"],
    )


# PUBLIC_INTERFACE
class ProductUpdateSchema(Schema):
    """Request payload to update a product."""

    name = fields.String(validate=validate.Length(min=1, max=200))
    description = fields.String(validate=validate.Length(max=5000), allow_none=True)
    price = fields.Decimal(as_string=True, validate=validate.Range(min=0))
    currency = fields.String(validate=validate.Length(equal=3))
    sku = fields.String(validate=validate.Length(min=1, max=64))
    inventory = fields.Integer(validate=validate.Range(min=0))
    image_url = fields.Url(allow_none=True)
    active = fields.Boolean()
    tags = fields.List(fields.String(validate=validate.Length(min=1, max=32)), allow_none=True)


# PUBLIC_INTERFACE
class PublicProductSchema(Schema):
    """Public representation of a product."""

    id = fields.String(required=True, description="Product identifier.", example="prod_123")
    name = fields.String(required=True, description="Product name.")
    description = fields.String(allow_none=True, description="Product description.")
    price = fields.Decimal(as_string=True, required=True, description="Unit price.")
    currency = fields.String(required=True, description="ISO currency code.")
    sku = fields.String(required=True, description="SKU.")
    inventory = fields.Integer(required=True, description="Available inventory count.")
    image_url = fields.Url(allow_none=True, description="Primary product image URL.")
    active = fields.Boolean(required=True, description="Whether product is active.")
    tags = fields.List(fields.String(), required=False, description="List of product tags.")
    created_at = fields.DateTime(required=True, description="Creation timestamp (ISO8601).")
    updated_at = fields.DateTime(required=True, description="Last update timestamp (ISO8601).")


# PUBLIC_INTERFACE
class ProductListResponseSchema(Schema):
    """Paginated product list response schema."""

    data = fields.List(
        fields.Nested(PublicProductSchema),
        required=True,
        description="List of products for the current page.",
    )
    pagination = fields.Nested(
        PaginationMetadataSchema, required=True, description="Pagination metadata."
    )
