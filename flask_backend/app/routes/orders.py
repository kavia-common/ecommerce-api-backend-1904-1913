"""Orders routes for the Ecommerce API."""

from __future__ import annotations

from typing import Dict, List

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint

from ..errors import BadRequest, NotFound
from ..routes.auth import require_auth
from ..schemas.common import PaginationQuerySchema
from ..schemas.orders import (
    OrderCreateSchema,
    OrderListResponseSchema,
    OrderPublicSchema,
)
from ..services.storage import (
    get_carts_repo,
    get_orders_repo,
    get_products_repo,
)

# Orders blueprint under /orders with OpenAPI tag "Orders"
blp = Blueprint(
    "Orders",
    "Orders",
    url_prefix="/orders",
    description="Order submission and status",
)


def _validate_and_prepare_order_from_cart(
    cart: Dict,
    currency: str,
) -> List[Dict]:
    """Validate the cart items for order creation and return enriched line items.

    This function validates:
    - Cart is not empty
    - All products still exist and are active
    - Currency matches
    - Inventory is sufficient

    Returns a list of product snapshots with required info for stock decrement.
    """
    if not cart or not cart.get("items"):
        raise BadRequest("Cart is empty")

    if currency and cart.get("currency") and currency != cart.get("currency"):
        raise BadRequest("Currency mismatch between order and cart")

    products_repo = get_products_repo()
    prepared: List[Dict] = []
    for it in cart.get("items", []):
        pid = it.get("product_id")
        qty = int(it.get("quantity", 0))
        if not pid or qty <= 0:
            raise BadRequest("Invalid cart item detected")
        product = products_repo.get(pid)
        if not product or not product.get("active", True):
            raise BadRequest("One or more products are unavailable")
        inv = int(product.get("inventory", 0))
        if qty > inv:
            raise BadRequest(f"Insufficient stock for product {product.get('name')}")
        prepared.append(
            {
                "product": product,
                "product_id": pid,
                "quantity": qty,
            }
        )
    if not prepared:
        raise BadRequest("Cart is empty")
    return prepared


def _decrement_inventory(prepared_items: List[Dict]) -> None:
    """Decrement inventory for products based on prepared_items."""
    products_repo = get_products_repo()
    for item in prepared_items:
        p = item["product"]
        pid = item["product_id"]
        qty = item["quantity"]
        new_inv = max(0, int(p.get("inventory", 0)) - qty)
        products_repo.update(pid, {"inventory": new_inv})


def _get_user_cart_or_404() -> Dict:
    """Retrieve cart associated to current user if present, else 404 for safety."""
    carts = get_carts_repo()
    # We use a per-request ensure flow similar to cart routes: create/get.
    # Here we should not create a new empty cart for order submission; if no cart exists, treat as empty.
    # Using get_or_create to maintain a consistent cart id per request/user ensures an id exists,
    # but order creation will validate emptiness and fail if no items.
    user_id = g.current_user.get("id") if g.current_user else None
    cart = carts.get_or_create(user_id=user_id, currency="USD")
    if not cart:
        raise NotFound("Cart not found")
    return cart


@blp.route("")
class OrdersListCreate(MethodView):
    """List current user's orders; create a new order from the cart."""

    @require_auth
    @blp.arguments(PaginationQuerySchema, location="query")
    @blp.response(200, OrderListResponseSchema, description="Paginated list of orders.")
    def get(self, pagination_args: dict):
        """List the authenticated user's orders with pagination.

        Query parameters:
        - page: integer, 1-indexed (default 1)
        - page_size: integer, items per page (default: server config DEFAULT_PAGE_SIZE)
        - sort: optional, one of: created_asc, created_desc (default created_desc)

        Returns:
        - data: Array of order objects
        - pagination: Metadata including total, page, total_pages
        """
        page = pagination_args.get("page", 1)
        page_size = pagination_args.get("page_size")
        sort = pagination_args.get("sort") or "created_desc"
        if sort not in (None, "created_asc", "created_desc"):
            # Strict validation for supported sorts
            raise BadRequest("Invalid sort parameter")

        user_id = g.current_user["id"]
        orders_repo = get_orders_repo()
        items, meta = orders_repo.list(page=page, page_size=page_size, user_id=user_id, sort=sort)
        return {"data": items, "pagination": meta}

    @require_auth
    @blp.arguments(OrderCreateSchema, location="json")
    @blp.response(201, OrderPublicSchema, description="Created order.")
    def post(self, json_data: dict):
        """Create an order from the current user's cart.

        Request body: OrderCreateSchema
        Validates stock, calculates totals, decrements product inventory,
        creates the order, clears the cart, and returns the created order.
        """
        # Extract core fields
        shipping_address = json_data["shipping_address"]
        billing_address = json_data.get("billing_address") or shipping_address
        payment = json_data.get("payment") or {}
        currency = json_data.get("currency") or "USD"
        notes = json_data.get("notes")

        # Retrieve the cart
        cart = _get_user_cart_or_404()

        # Validate and prepare items
        prepared_items = _validate_and_prepare_order_from_cart(cart, currency)

        # If schema supplied an items array, ensure it matches cart items set to avoid mismatch
        # For simplicity, we rely on cart content; OrderCreateSchema's items are accepted but not used to override cart.
        # This is typical for "order from cart" flows.

        # Decrement inventory
        _decrement_inventory(prepared_items)

        # Create the order from the cart snapshot
        user_id = g.current_user["id"] if g.current_user else None
        orders_repo = get_orders_repo()
        order = orders_repo.create_from_cart(
            cart=cart,
            user_id=user_id,
            shipping_address=shipping_address,
            billing_address=billing_address,
            payment=payment,
            currency=currency or cart.get("currency", "USD"),
            notes=notes,
        )

        # Clear the cart after successful order creation
        carts = get_carts_repo()
        carts.clear(cart["id"])

        return order


@blp.route("/<string:order_id>")
class OrderDetail(MethodView):
    """Retrieve a single order by id for the current user."""

    @require_auth
    @blp.response(200, OrderPublicSchema, description="Order by id.")
    def get(self, order_id: str):
        """Get an order by id for the authenticated user."""
        orders_repo = get_orders_repo()
        order = orders_repo.get(order_id)
        if not order:
            raise NotFound("Order not found")
        # Ensure the current user is the owner of the order
        if order.get("user_id") != g.current_user["id"]:
            # For this demo, we return not found to avoid leaking existence
            raise NotFound("Order not found")
        return order
