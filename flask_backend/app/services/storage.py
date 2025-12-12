"""Thread-safe in-memory storage repositories for Users, Products, Carts, and Orders.

This module provides simple in-memory repositories with CRUD, filtering, and pagination helpers.
It also seeds initial products at app startup.

Design notes:
- Repositories use threading.RLock for thread safety.
- IDs are prefixed strings like usr_, prod_, cart_, ord_ for clarity.
- Timestamps are stored as timezone-aware UTC datetimes (ISO via serialization layer).
- Prices are stored as Decimal for accuracy.
- Pagination helpers return (items, metadata) to integrate with schemas.common.PaginationMetadataSchema.
- Product filtering supports query 'q', category via tags containing a category string, price ranges,
  and sorting by price or created time.
- Cart operations include add/update/remove items and totals calculation using product snapshots.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

# Type aliases for clarity
JSONDict = Dict[str, Any]


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _gen_id(prefix: str) -> str:
    """Generate a short unique id with a given prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _to_decimal(value: Any) -> Decimal:
    """Coerce a value into a Decimal with 2 decimal places."""
    if isinstance(value, Decimal):
        d = value
    else:
        d = Decimal(str(value))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# PUBLIC_INTERFACE
def paginate_list(data: List[JSONDict], page: int, page_size: int, default_page_size: int) -> Tuple[List[JSONDict], JSONDict]:
    """Paginate a list of dictionaries.

    Returns tuple: (page_items, pagination_metadata)
    """
    if page_size is None:
        page_size = default_page_size
    total = len(data)
    first_page = 1
    last_page = max(1, (total + page_size - 1) // page_size)
    page = max(first_page, min(page, last_page))
    start = (page - 1) * page_size
    end = start + page_size
    items = data[start:end]
    meta = {
        "total": total,
        "total_pages": last_page,
        "first_page": first_page,
        "last_page": last_page,
        "page": page,
        "previous_page": page - 1 if page > first_page else None,
        "next_page": page + 1 if page < last_page else None,
    }
    return items, meta


class _BaseRepo:
    """Base repository providing thread-safety helpers."""
    def __init__(self) -> None:
        self._lock = threading.RLock()


class UsersRepo(_BaseRepo):
    """In-memory user repository."""
    def __init__(self) -> None:
        super().__init__()
        self._users: Dict[str, JSONDict] = {}  # id -> user

    # PUBLIC_INTERFACE
    def create(self, email: str, name: str, password_hash: str) -> JSONDict:
        """Create a new user."""
        with self._lock:
            # enforce unique email
            if any(u["email"].lower() == email.lower() for u in self._users.values()):
                raise ValueError("Email already registered")
            user_id = _gen_id("usr_")
            now = _utcnow()
            user = {
                "id": user_id,
                "email": email,
                "name": name,
                "password_hash": password_hash,
                "created_at": now,
                "updated_at": now,
            }
            self._users[user_id] = user
            return user.copy()

    # PUBLIC_INTERFACE
    def get(self, user_id: str) -> Optional[JSONDict]:
        """Get a user by id."""
        with self._lock:
            u = self._users.get(user_id)
            return u.copy() if u else None

    # PUBLIC_INTERFACE
    def get_by_email(self, email: str) -> Optional[JSONDict]:
        """Get a user by email."""
        with self._lock:
            for u in self._users.values():
                if u["email"].lower() == email.lower():
                    return u.copy()
            return None

    # PUBLIC_INTERFACE
    def update(self, user_id: str, **fields: Any) -> Optional[JSONDict]:
        """Update user fields (name, password_hash)."""
        with self._lock:
            if user_id not in self._users:
                return None
            user = self._users[user_id]
            for k in ("name", "password_hash"):
                if k in fields and fields[k] is not None:
                    user[k] = fields[k]
            user["updated_at"] = _utcnow()
            return user.copy()


class ProductsRepo(_BaseRepo):
    """In-memory product catalog repository."""
    def __init__(self) -> None:
        super().__init__()
        self._products: Dict[str, JSONDict] = {}  # id -> product

    # PUBLIC_INTERFACE
    def create(self, data: JSONDict) -> JSONDict:
        """Create a product. Expected keys: name, price, currency, sku, inventory, etc."""
        with self._lock:
            # SKU uniqueness
            if any(p["sku"] == data["sku"] for p in self._products.values()):
                raise ValueError("SKU already exists")
            prod_id = _gen_id("prod_")
            now = _utcnow()
            product = {
                "id": prod_id,
                "name": data["name"],
                "description": data.get("description"),
                "price": _to_decimal(data["price"]),
                "currency": data["currency"],
                "sku": data["sku"],
                "inventory": int(data.get("inventory", 0)),
                "image_url": data.get("image_url"),
                "active": bool(data.get("active", True)),
                "tags": list(data.get("tags") or []),
                "created_at": now,
                "updated_at": now,
            }
            self._products[prod_id] = product
            return product.copy()

    # PUBLIC_INTERFACE
    def get(self, product_id: str) -> Optional[JSONDict]:
        """Get product by id."""
        with self._lock:
            p = self._products.get(product_id)
            return p.copy() if p else None

    # PUBLIC_INTERFACE
    def update(self, product_id: str, data: JSONDict) -> Optional[JSONDict]:
        """Update product fields."""
        with self._lock:
            product = self._products.get(product_id)
            if not product:
                return None
            if "sku" in data and data["sku"] != product["sku"]:
                if any(p["sku"] == data["sku"] for pid, p in self._products.items() if pid != product_id):
                    raise ValueError("SKU already exists")
            for k in ("name", "description", "currency", "sku", "image_url", "active"):
                if k in data:
                    product[k] = data[k]
            if "price" in data:
                product["price"] = _to_decimal(data["price"])
            if "inventory" in data:
                product["inventory"] = int(data["inventory"])
            if "tags" in data:
                product["tags"] = list(data["tags"] or [])
            product["updated_at"] = _utcnow()
            return product.copy()

    # PUBLIC_INTERFACE
    def delete(self, product_id: str) -> bool:
        """Delete product by id."""
        with self._lock:
            return self._products.pop(product_id, None) is not None

    # PUBLIC_INTERFACE
    def list(
        self,
        page: int,
        page_size: Optional[int],
        q: Optional[str] = None,
        category: Optional[str] = None,
        price_min: Optional[Any] = None,
        price_max: Optional[Any] = None,
        sort: Optional[str] = None,
        include_inactive: bool = False,
    ) -> Tuple[List[JSONDict], JSONDict]:
        """List products with filtering and pagination.

        sort options:
        - price_asc, price_desc
        - created_asc, created_desc
        default: created_desc
        """
        with self._lock:
            items = [p.copy() for p in self._products.values()]
        # filter active
        if not include_inactive:
            items = [p for p in items if p.get("active", True)]

        # free-text search on name/description/sku/tags
        if q:
            ql = q.lower()
            def match(p: JSONDict) -> bool:
                if ql in (p.get("name") or "").lower():
                    return True
                if ql in (p.get("description") or "").lower():
                    return True
                if ql in (p.get("sku") or "").lower():
                    return True
                tags = [str(t).lower() for t in (p.get("tags") or [])]
                return any(ql in t for t in tags)
            items = [p for p in items if match(p)]

        # category filter via tags category
        if category:
            cl = category.lower()
            items = [p for p in items if any(cl in str(t).lower() for t in (p.get("tags") or []))]

        # price range
        if price_min is not None:
            pmin = _to_decimal(price_min)
            items = [p for p in items if _to_decimal(p["price"]) >= pmin]
        if price_max is not None:
            pmax = _to_decimal(price_max)
            items = [p for p in items if _to_decimal(p["price"]) <= pmax]

        # sorting
        if not sort:
            sort = "created_desc"
        if sort == "price_asc":
            items.sort(key=lambda p: _to_decimal(p["price"]))
        elif sort == "price_desc":
            items.sort(key=lambda p: _to_decimal(p["price"]), reverse=True)
        elif sort == "created_asc":
            items.sort(key=lambda p: p.get("created_at") or _utcnow())
        else:
            # created_desc
            items.sort(key=lambda p: p.get("created_at") or _utcnow(), reverse=True)

        default_page_size = int(current_app.config.get("DEFAULT_PAGE_SIZE", 10)) if current_app else 10
        return paginate_list(items, page, page_size, default_page_size)


class CartsRepo(_BaseRepo):
    """In-memory carts repository."""

    def __init__(self, products_repo: ProductsRepo) -> None:
        super().__init__()
        self._carts: Dict[str, JSONDict] = {}  # id -> cart
        self._products_repo = products_repo

    def _empty_cart(self, user_id: Optional[str] = None, currency: str = "USD") -> JSONDict:
        now = _utcnow()
        return {
            "id": _gen_id("cart_"),
            "user_id": user_id,
            "items": [],  # [{product_id, quantity}]
            "currency": currency,
            "subtotal": Decimal("0.00"),
            "tax": Decimal("0.00"),
            "total": Decimal("0.00"),
            "updated_at": now,
            "created_at": now,
        }

    # PUBLIC_INTERFACE
    def get_or_create(self, cart_id: Optional[str] = None, user_id: Optional[str] = None, currency: str = "USD") -> JSONDict:
        """Get existing cart by id or create a new one."""
        with self._lock:
            if cart_id and cart_id in self._carts:
                return self._carts[cart_id].copy()
            cart = self._empty_cart(user_id=user_id, currency=currency)
            self._carts[cart["id"]] = cart
            return cart.copy()

    # PUBLIC_INTERFACE
    def add_item(self, cart_id: str, product_id: str, quantity: int) -> Optional[JSONDict]:
        """Add or increase quantity of a product in the cart."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart:
                return None
            # validate product exists and active
            product = self._products_repo.get(product_id)
            if not product or not product.get("active", True):
                raise ValueError("Product unavailable")
            # update or insert
            existing = next((it for it in cart["items"] if it["product_id"] == product_id), None)
            if existing:
                existing["quantity"] += quantity
            else:
                cart["items"].append({"product_id": product_id, "quantity": quantity})
            self._recalc_totals(cart)
            cart["updated_at"] = _utcnow()
            return cart.copy()

    # PUBLIC_INTERFACE
    def set_item(self, cart_id: str, product_id: str, quantity: int) -> Optional[JSONDict]:
        """Set quantity for a product in the cart (remove if 0)."""
        if quantity < 0:
            raise ValueError("Quantity must be >= 0")
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart:
                return None
            if quantity == 0:
                cart["items"] = [it for it in cart["items"] if it["product_id"] != product_id]
            else:
                product = self._products_repo.get(product_id)
                if not product or not product.get("active", True):
                    raise ValueError("Product unavailable")
                existing = next((it for it in cart["items"] if it["product_id"] == product_id), None)
                if existing:
                    existing["quantity"] = quantity
                else:
                    cart["items"].append({"product_id": product_id, "quantity": quantity})
            self._recalc_totals(cart)
            cart["updated_at"] = _utcnow()
            return cart.copy()

    # PUBLIC_INTERFACE
    def remove_item(self, cart_id: str, product_id: str) -> Optional[JSONDict]:
        """Remove an item from the cart."""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart:
                return None
            before = len(cart["items"])
            cart["items"] = [it for it in cart["items"] if it["product_id"] != product_id]
            if len(cart["items"]) != before:
                self._recalc_totals(cart)
                cart["updated_at"] = _utcnow()
            return cart.copy()

    # PUBLIC_INTERFACE
    def get(self, cart_id: str) -> Optional[JSONDict]:
        """Get a cart by id."""
        with self._lock:
            cart = self._carts.get(cart_id)
            return cart.copy() if cart else None

    # PUBLIC_INTERFACE
    def clear(self, cart_id: str) -> Optional[JSONDict]:
        """Clear all items in a cart."""
        with self._lock:
            cart = self._carts.get(cart_id)
            if not cart:
                return None
            cart["items"] = []
            self._recalc_totals(cart)
            cart["updated_at"] = _utcnow()
            return cart.copy()

    def _recalc_totals(self, cart: JSONDict) -> None:
        """Recalculate subtotal, tax, and total using product prices."""
        subtotal = Decimal("0.00")
        for it in cart["items"]:
            product = self._products_repo.get(it["product_id"])
            if not product:
                # skip invalid items (defensive)
                continue
            qty = int(it["quantity"])
            line = _to_decimal(product["price"]) * qty
            subtotal += line
        subtotal = subtotal.quantize(Decimal("0.01"))
        tax_rate = Decimal("0.10")  # 10% simple tax for demo
        tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
        total = subtotal + tax
        cart["subtotal"] = subtotal
        cart["tax"] = tax
        cart["total"] = total


class OrdersRepo(_BaseRepo):
    """In-memory orders repository."""
    def __init__(self, products_repo: ProductsRepo) -> None:
        super().__init__()
        self._orders: Dict[str, JSONDict] = {}  # id -> order
        self._products_repo = products_repo

    # PUBLIC_INTERFACE
    def create_from_cart(
        self,
        cart: JSONDict,
        user_id: Optional[str],
        shipping_address: JSONDict,
        billing_address: Optional[JSONDict],
        payment: JSONDict,
        currency: str,
        notes: Optional[str] = None,
    ) -> JSONDict:
        """Create an order from a cart snapshot."""
        with self._lock:
            order_id = _gen_id("ord_")
            now = _utcnow()
            items: List[JSONDict] = []
            subtotal = Decimal("0.00")
            for it in cart.get("items", []):
                p = self._products_repo.get(it["product_id"])
                if not p:
                    # Skip missing items
                    continue
                qty = int(it["quantity"])
                unit_price = _to_decimal(p["price"])
                line_total = (unit_price * qty).quantize(Decimal("0.01"))
                items.append(
                    {
                        "product": p,  # snapshot
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )
                subtotal += line_total
            tax_rate = Decimal("0.10")
            tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
            shipping = Decimal("0.00")  # free shipping for demo
            total = (subtotal + tax + shipping).quantize(Decimal("0.01"))
            order = {
                "id": order_id,
                "user_id": user_id,
                "status": "paid" if payment else "pending",
                "currency": currency,
                "items": items,
                "shipping_address": shipping_address,
                "billing_address": billing_address,
                "subtotal": subtotal,
                "tax": tax,
                "shipping": shipping,
                "total": total,
                "payment": payment,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
            self._orders[order_id] = order
            return order.copy()

    # PUBLIC_INTERFACE
    def get(self, order_id: str) -> Optional[JSONDict]:
        """Get order by id."""
        with self._lock:
            o = self._orders.get(order_id)
            return o.copy() if o else None

    # PUBLIC_INTERFACE
    def list(
        self,
        page: int,
        page_size: Optional[int],
        user_id: Optional[str] = None,
        sort: Optional[str] = "created_desc",
    ) -> Tuple[List[JSONDict], JSONDict]:
        """List orders, optionally filtering by user_id."""
        with self._lock:
            items = [o.copy() for o in self._orders.values()]
        if user_id:
            items = [o for o in items if o.get("user_id") == user_id]
        if sort == "created_asc":
            items.sort(key=lambda o: o.get("created_at") or _utcnow())
        else:
            items.sort(key=lambda o: o.get("created_at") or _utcnow(), reverse=True)
        default_page_size = int(current_app.config.get("DEFAULT_PAGE_SIZE", 10)) if current_app else 10
        return paginate_list(items, page, page_size, default_page_size)


# Singletons initialized at module import and seeded at app startup.
_USERS = UsersRepo()
_PRODUCTS = ProductsRepo()
_CARTS = CartsRepo(_PRODUCTS)
_ORDERS = OrdersRepo(_PRODUCTS)


def _seed_products() -> None:
    """Seed initial catalog with 15 demo products if empty."""
    with _PRODUCTS._lock:
        if _PRODUCTS._products:
            return  # already seeded
        demo_products = [
            {
                "name": "Wireless Mouse",
                "description": "Ergonomic 2.4G wireless mouse with adjustable DPI.",
                "price": "29.99",
                "currency": "USD",
                "sku": "WM-001-BLK",
                "inventory": 120,
                "image_url": "https://picsum.photos/seed/mouse/400/300",
                "active": True,
                "tags": ["electronics", "accessories", "mouse"],
            },
            {
                "name": "Mechanical Keyboard",
                "description": "RGB backlit mechanical keyboard with blue switches.",
                "price": "79.00",
                "currency": "USD",
                "sku": "MK-002-RGB",
                "inventory": 85,
                "image_url": "https://picsum.photos/seed/keyboard/400/300",
                "active": True,
                "tags": ["electronics", "accessories", "keyboard"],
            },
            {
                "name": "USB-C Hub 6-in-1",
                "description": "Expand your laptop ports with HDMI, USB 3.0, and SD card.",
                "price": "45.50",
                "currency": "USD",
                "sku": "HUB-006-USBC",
                "inventory": 200,
                "image_url": "https://picsum.photos/seed/hub/400/300",
                "active": True,
                "tags": ["electronics", "usb-c", "adapter"],
            },
            {
                "name": "Noise Cancelling Headphones",
                "description": "Over-ear wireless ANC headphones with 30h battery.",
                "price": "129.99",
                "currency": "USD",
                "sku": "HP-ANC-100",
                "inventory": 60,
                "image_url": "https://picsum.photos/seed/headphones/400/300",
                "active": True,
                "tags": ["audio", "headphones", "wireless"],
            },
            {
                "name": "4K Webcam",
                "description": "Crystal clear 4K webcam with auto-focus and dual mics.",
                "price": "99.00",
                "currency": "USD",
                "sku": "CAM-4K-01",
                "inventory": 90,
                "image_url": "https://picsum.photos/seed/webcam/400/300",
                "active": True,
                "tags": ["video", "camera", "webcam"],
            },
            {
                "name": "Portable SSD 1TB",
                "description": "Fast USB 3.2 Gen2 portable SSD with aluminum body.",
                "price": "149.00",
                "currency": "USD",
                "sku": "SSD-1TB-PORT",
                "inventory": 55,
                "image_url": "https://picsum.photos/seed/ssd/400/300",
                "active": True,
                "tags": ["storage", "ssd", "portable"],
            },
            {
                "name": "Smart LED Bulb",
                "description": "Wi-Fi enabled multicolor smart bulb; works with voice assistants.",
                "price": "14.99",
                "currency": "USD",
                "sku": "BULB-SMART-1",
                "inventory": 500,
                "image_url": "https://picsum.photos/seed/bulb/400/300",
                "active": True,
                "tags": ["smart-home", "lighting"],
            },
            {
                "name": "Bluetooth Speaker",
                "description": "Portable waterproof speaker with deep bass.",
                "price": "39.99",
                "currency": "USD",
                "sku": "SPK-BT-01",
                "inventory": 140,
                "image_url": "https://picsum.photos/seed/speaker/400/300",
                "active": True,
                "tags": ["audio", "speaker", "wireless"],
            },
            {
                "name": "Fitness Tracker",
                "description": "Activity tracker with heart rate and sleep monitor.",
                "price": "49.99",
                "currency": "USD",
                "sku": "FIT-TRK-01",
                "inventory": 160,
                "image_url": "https://picsum.photos/seed/fit/400/300",
                "active": True,
                "tags": ["wearables", "fitness"],
            },
            {
                "name": "Action Camera 4K",
                "description": "Rugged action camera with image stabilization.",
                "price": "179.00",
                "currency": "USD",
                "sku": "ACT-CAM-4K",
                "inventory": 40,
                "image_url": "https://picsum.photos/seed/action/400/300",
                "active": True,
                "tags": ["video", "camera", "outdoor"],
            },
            {
                "name": "Laptop Stand",
                "description": "Adjustable aluminum laptop stand for better ergonomics.",
                "price": "27.99",
                "currency": "USD",
                "sku": "LAP-STD-AL",
                "inventory": 220,
                "image_url": "https://picsum.photos/seed/stand/400/300",
                "active": True,
                "tags": ["office", "accessories"],
            },
            {
                "name": "Wireless Charger",
                "description": "Fast Qi wireless charging pad with USB-C input.",
                "price": "19.99",
                "currency": "USD",
                "sku": "CHR-WLS-10W",
                "inventory": 300,
                "image_url": "https://picsum.photos/seed/charger/400/300",
                "active": True,
                "tags": ["charging", "wireless"],
            },
            {
                "name": "Gaming Mouse Pad XL",
                "description": "Large extended mouse pad with stitched edges.",
                "price": "16.50",
                "currency": "USD",
                "sku": "PAD-XL-01",
                "inventory": 260,
                "image_url": "https://picsum.photos/seed/mousepad/400/300",
                "active": True,
                "tags": ["gaming", "accessories"],
            },
            {
                "name": "USB-C Cable 2m",
                "description": "Durable braided USB-C to USB-C cable (60W).",
                "price": "9.99",
                "currency": "USD",
                "sku": "CBL-USBC-2M",
                "inventory": 600,
                "image_url": "https://picsum.photos/seed/cable/400/300",
                "active": True,
                "tags": ["cables", "usb-c"],
            },
            {
                "name": "1080p Monitor 24\"",
                "description": "24-inch IPS monitor with thin bezels and HDMI.",
                "price": "129.00",
                "currency": "USD",
                "sku": "MON-FHD-24",
                "inventory": 70,
                "image_url": "https://picsum.photos/seed/monitor/400/300",
                "active": True,
                "tags": ["display", "monitor"],
            },
        ]
        for p in demo_products:
            _PRODUCTS.create(p)


# PUBLIC_INTERFACE
def get_users_repo() -> UsersRepo:
    """Get singleton UsersRepo."""
    return _USERS


# PUBLIC_INTERFACE
def get_products_repo() -> ProductsRepo:
    """Get singleton ProductsRepo."""
    return _PRODUCTS


# PUBLIC_INTERFACE
def get_carts_repo() -> CartsRepo:
    """Get singleton CartsRepo."""
    return _CARTS


# PUBLIC_INTERFACE
def get_orders_repo() -> OrdersRepo:
    """Get singleton OrdersRepo."""
    return _ORDERS


# PUBLIC_INTERFACE
def init_storage_seed() -> None:
    """Seed initial data; call once at app startup."""
    _seed_products()
