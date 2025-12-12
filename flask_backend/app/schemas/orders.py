"""Order related Marshmallow schemas."""

from marshmallow import Schema, fields, validate
from .common import PaginationMetadataSchema
from .products import PublicProductSchema


# PUBLIC_INTERFACE
class AddressSchema(Schema):
    """Shipping or billing address."""

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
        description="Full name for the address.",
        example="Jane Doe",
    )
    line1 = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
        description="Primary street line.",
        example="123 Market St",
    )
    line2 = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=200),
        description="Second street line (apt, suite, floor).",
        example="Suite 400",
    )
    city = fields.String(
        required=True,
        validate=validate.Length(min=1, max=120),
        description="City.",
        example="San Francisco",
    )
    state = fields.String(
        required=True,
        validate=validate.Length(min=1, max=120),
        description="State/Province/Region.",
        example="CA",
    )
    postal_code = fields.String(
        required=True,
        validate=validate.Length(min=1, max=32),
        description="ZIP/Postal code.",
        example="94103",
    )
    country = fields.String(
        required=True,
        validate=validate.Length(equal=2),
        description="ISO 3166-1 alpha-2 country code.",
        example="US",
    )
    phone = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=32),
        description="Contact phone number.",
        example="+1-555-123-4567",
    )


# PUBLIC_INTERFACE
class PaymentSchema(Schema):
    """Mock payment payload for creating an order."""

    method = fields.String(
        required=True,
        validate=validate.OneOf(["card", "cod", "paypal"]),
        description="Payment method.",
        example="card",
    )
    # For a mock flow, allow an opaque token or last4 string.
    card_token = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(min=1, max=256),
        description="Opaque client-side payment token (mock).",
        example="tok_abc123",
    )
    last4 = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(equal=4),
        description="Card last 4 digits for display (mock).",
        example="4242",
    )


# PUBLIC_INTERFACE
class OrderItemSchema(Schema):
    """An item to be purchased as part of an order (input)."""

    product_id = fields.String(
        required=True,
        description="Product identifier.",
        example="prod_123",
    )
    quantity = fields.Integer(
        required=True,
        validate=validate.Range(min=1, max=9999),
        description="Quantity to purchase.",
        example=2,
    )


# PUBLIC_INTERFACE
class OrderCreateSchema(Schema):
    """Payload to create/submit an order."""

    items = fields.List(
        fields.Nested(OrderItemSchema),
        required=True,
        validate=validate.Length(min=1),
        description="Line items to purchase.",
    )
    shipping_address = fields.Nested(
        AddressSchema,
        required=True,
        description="Shipping address for the order.",
    )
    billing_address = fields.Nested(
        AddressSchema,
        required=False,
        allow_none=True,
        description="Billing address; if omitted, shipping address is used.",
    )
    payment = fields.Nested(
        PaymentSchema,
        required=True,
        description="Payment information (mock).",
    )
    currency = fields.String(
        required=True,
        validate=validate.Length(equal=3),
        description="ISO 4217 currency code for the order.",
        example="USD",
    )
    notes = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=1000),
        description="Optional order notes.",
    )


# PUBLIC_INTERFACE
class PublicOrderItemSchema(Schema):
    """Public representation of an order line item including a product snapshot."""

    product = fields.Nested(
        PublicProductSchema, required=True, description="Snapshot of the product at purchase time."
    )
    quantity = fields.Integer(required=True, description="Quantity purchased.")
    unit_price = fields.Decimal(
        as_string=True, required=True, description="Unit price at purchase time."
    )
    line_total = fields.Decimal(
        as_string=True, required=True, description="Quantity * unit_price."
    )


# PUBLIC_INTERFACE
class OrderPublicSchema(Schema):
    """Public representation of an order."""

    id = fields.String(required=True, description="Order identifier.", example="ord_123")
    user_id = fields.String(
        required=False, allow_none=True, description="User identifier if authenticated."
    )
    status = fields.String(
        required=True,
        validate=validate.OneOf(["pending", "paid", "processing", "shipped", "delivered", "canceled"]),
        description="Current order status.",
        example="paid",
    )
    currency = fields.String(required=True, description="ISO currency code, e.g., USD.")
    items = fields.List(
        fields.Nested(PublicOrderItemSchema),
        required=True,
        description="Purchased line items.",
    )
    shipping_address = fields.Nested(AddressSchema, required=True, description="Shipping address.")
    billing_address = fields.Nested(
        AddressSchema, required=False, allow_none=True, description="Billing address."
    )
    subtotal = fields.Decimal(as_string=True, required=True, description="Subtotal amount.")
    tax = fields.Decimal(as_string=True, required=True, description="Tax amount.")
    shipping = fields.Decimal(as_string=True, required=True, description="Shipping cost.")
    total = fields.Decimal(as_string=True, required=True, description="Total amount.")
    payment = fields.Nested(
        PaymentSchema,
        required=False,
        allow_none=True,
        description="Payment details (mock) with limited fields.",
    )
    created_at = fields.DateTime(required=True, description="Creation timestamp (ISO8601).")
    updated_at = fields.DateTime(required=True, description="Last update timestamp (ISO8601).")


# PUBLIC_INTERFACE
class OrderListResponseSchema(Schema):
    """Paginated order list response."""

    data = fields.List(
        fields.Nested(OrderPublicSchema),
        required=True,
        description="List of orders for the current page.",
    )
    pagination = fields.Nested(
        PaginationMetadataSchema, required=True, description="Pagination metadata."
    )
