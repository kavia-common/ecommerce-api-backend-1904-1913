"""Shopping Cart routes for the Ecommerce API."""

from __future__ import annotations

from typing import Dict

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint

from ..errors import BadRequest, NotFound
from ..routes.auth import require_auth
from ..schemas.cart import CartItemSchema, PublicCartSchema
from ..services.storage import get_carts_repo

# Cart blueprint under /cart with OpenAPI tag "Cart"
blp = Blueprint(
    "Cart",
    "Cart",
    url_prefix="/cart",
    description="Shopping cart operations",
)


def _ensure_cart_for_user() -> Dict:
    """Get or create a cart associated to the current user.

    For this demo implementation we create or retrieve a cart using user_id for association.
    """
    user = g.current_user
    user_id = user["id"] if user else None
    carts = get_carts_repo()
    # Use a user-associated cart. For simplicity, one cart per user in-memory:
    # We don't have direct lookup by user, so we'll create/get a new cart per call and
    # keep returning the same id from client side typically via session. For this demo,
    # we just create or return a stable cart stored on g for the duration of request.
    # To keep behavior predictable, we'll stash a cart_id on g for this request and
    # create it if not exists.
    # In a real system, cart id would be persisted in session/cookie.
    existing = getattr(g, "_cart_id", None)
    if existing:
        cart = carts.get(existing)
        if cart:
            return cart
    # Otherwise ensure a cart exists and memoize its id this request
    cart = carts.get_or_create(user_id=user_id, currency="USD")
    g._cart_id = cart["id"]
    return cart


def _cart_to_public(cart: Dict) -> Dict:
    """Transform internal cart structure to PublicCartSchema format.

    CartsRepo already stores monetary fields as Decimal and includes necessary fields.
    We need to expand items with product snapshot and line_total as expected by schema.
    CartsRepo totals are correct; for line items we recompute using repo logic by calling get()
    which returns product ids only; hence we derive product snapshot here via repo.
    """
    from ..services.storage import get_products_repo  # local import to avoid cycles
    products_repo = get_products_repo()
    items_public = []
    for it in cart.get("items", []):
        product = products_repo.get(it["product_id"])
        if not product:
            # skip invalid items defensively
            continue
        qty = int(it["quantity"])
        unit_price = product["price"]
        line_total = (unit_price * qty).quantize(unit_price)  # both are Decimal with 2 dp
        items_public.append(
            {
                "product": product,
                "quantity": qty,
                "line_total": line_total,
            }
        )
    return {
        "id": cart["id"],
        "user_id": cart.get("user_id"),
        "items": items_public,
        "currency": cart.get("currency", "USD"),
        "subtotal": cart["subtotal"],
        "tax": cart["tax"],
        "total": cart["total"],
        "updated_at": cart["updated_at"],
    }


@blp.route("")
class CartResource(MethodView):
    """Get or clear the authenticated user's cart."""

    @require_auth
    @blp.response(200, PublicCartSchema, description="Current authenticated user's cart.")
    def get(self):
        """Retrieve current authenticated user's shopping cart."""
        cart = _ensure_cart_for_user()
        return _cart_to_public(cart)

    @require_auth
    @blp.response(204, description="Cleared the cart.")
    def delete(self):
        """Clear all items from the current authenticated user's cart."""
        carts = get_carts_repo()
        cart = _ensure_cart_for_user()
        cleared = carts.clear(cart["id"])
        if not cleared:
            # Shouldn't happen for our flow; cart must exist after _ensure_cart_for_user
            raise NotFound("Cart not found")
        return None


@blp.route("/items")
class CartItemsCollection(MethodView):
    """Add new items to the cart (merge/increment)."""

    @require_auth
    @blp.arguments(CartItemSchema, location="json")
    @blp.response(200, PublicCartSchema, description="Cart after adding the item.")
    def post(self, json_data: Dict):
        """Add an item to the cart or increase its quantity.

        Request body:
        - product_id: string
        - quantity: integer >= 1

        Returns: Updated cart.
        """
        product_id = json_data.get("product_id")
        quantity = json_data.get("quantity")
        if not product_id:
            raise BadRequest("product_id is required")
        if quantity is None:
            raise BadRequest("quantity is required")
        try:
            qty = int(quantity)
        except Exception:
            raise BadRequest("quantity must be an integer")
        if qty <= 0:
            raise BadRequest("quantity must be >= 1")

        carts = get_carts_repo()
        cart = _ensure_cart_for_user()
        try:
            updated = carts.add_item(cart["id"], product_id, qty)
        except ValueError as e:
            # Map repo validation errors to 400
            raise BadRequest(str(e))
        if not updated:
            raise NotFound("Cart not found")
        return _cart_to_public(updated)


@blp.route("/items/<string:product_id>")
class CartItemDetail(MethodView):
    """Update or remove a specific item in the cart."""

    @require_auth
    @blp.arguments(CartItemSchema(partial=True), location="json")
    @blp.response(200, PublicCartSchema, description="Cart after updating the item.")
    def patch(self, json_data: Dict, product_id: str):
        """Update quantity for an item; remove if quantity == 0.

        Request body:
        - quantity: integer >= 0

        Returns: Updated cart.
        """
        if "quantity" not in json_data:
            raise BadRequest("quantity is required")
        try:
            qty = int(json_data["quantity"])
        except Exception:
            raise BadRequest("quantity must be an integer")
        if qty < 0:
            raise BadRequest("quantity must be >= 0")

        carts = get_carts_repo()
        cart = _ensure_cart_for_user()
        try:
            updated = carts.set_item(cart["id"], product_id, qty)
        except ValueError as e:
            raise BadRequest(str(e))
        if not updated:
            raise NotFound("Cart not found")
        return _cart_to_public(updated)

    @require_auth
    @blp.response(200, PublicCartSchema, description="Cart after removing the item.")
    def delete(self, product_id: str):
        """Remove an item from the cart by product_id.

        Returns: Updated cart.
        """
        carts = get_carts_repo()
        cart = _ensure_cart_for_user()
        updated = carts.remove_item(cart["id"], product_id)
        if not updated:
            raise NotFound("Cart not found")
        return _cart_to_public(updated)
