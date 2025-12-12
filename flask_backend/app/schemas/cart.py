"""Shopping cart Marshmallow schemas."""

from marshmallow import Schema, fields, validate
from .products import PublicProductSchema


# PUBLIC_INTERFACE
class CartItemSchema(Schema):
    """A single item in the shopping cart."""

    product_id = fields.String(
        required=True,
        description="Identifier of the product.",
        example="prod_123",
    )
    quantity = fields.Integer(
        required=True,
        validate=validate.Range(min=1, max=9999),
        description="Quantity of the product in the cart.",
        example=2,
    )


# PUBLIC_INTERFACE
class CartUpdateSchema(Schema):
    """Schema to add or update items in the cart."""

    items = fields.List(
        fields.Nested(CartItemSchema),
        required=True,
        validate=validate.Length(min=1),
        description="Array of items to set in the cart (replace or merge depending on endpoint semantics).",
    )


# PUBLIC_INTERFACE
class PublicCartItemSchema(Schema):
    """Public representation of a cart item including product snapshot."""

    product = fields.Nested(PublicProductSchema, required=True, description="Product details.")
    quantity = fields.Integer(required=True, description="Quantity of the product.")
    line_total = fields.Decimal(
        as_string=True, required=True, description="Line total = price * quantity."
    )


# PUBLIC_INTERFACE
class PublicCartSchema(Schema):
    """Public representation of a cart."""

    id = fields.String(required=True, description="Cart identifier.", example="cart_123")
    user_id = fields.String(
        allow_none=True, description="User identifier if the cart is associated with a user."
    )
    items = fields.List(
        fields.Nested(PublicCartItemSchema),
        required=True,
        description="Items in the cart.",
    )
    currency = fields.String(required=True, description="Currency code of the cart totals.")
    subtotal = fields.Decimal(as_string=True, required=True, description="Subtotal amount.")
    tax = fields.Decimal(as_string=True, required=True, description="Tax amount.")
    total = fields.Decimal(as_string=True, required=True, description="Grand total amount.")
    updated_at = fields.DateTime(required=True, description="Last update timestamp (ISO8601).")
