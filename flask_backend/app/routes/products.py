"""Products routes for the Ecommerce API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import current_app, request
from flask.views import MethodView
from flask_smorest import Blueprint

from ..errors import BadRequest, NotFound
from ..schemas.products import (
    ProductCreateSchema,
    ProductListResponseSchema,
    ProductUpdateSchema,
    PublicProductSchema,
)
from ..schemas.common import PaginationQuerySchema
from ..services.storage import get_products_repo

# Products blueprint under /products with OpenAPI tag "Products"
blp = Blueprint(
    "Products",
    "Products",
    url_prefix="/products",
    description="Product catalog and search",
)


def _parse_list_query_params(args) -> Dict[str, Any]:
    """Parse and normalize list query params from request.args."""
    # Use webargs validation through smorest for base pagination fields
    # Additional filters handled here
    q = args.get("q")
    category = args.get("category")
    min_price = args.get("min_price")
    max_price = args.get("max_price")
    sort = args.get("sort")

    # Normalize sort aliases for price/name asc/desc
    # Supported: price_asc/price_desc, name_asc/name_desc, created_asc/created_desc (default)
    if sort:
        sort_l = sort.lower()
        # Map name sorting to created sorting isn't correct; instead, handle in repo if needed.
        # Our storage supports price_asc/price_desc and created_asc/created_desc. We'll map name_asc/desc
        # to created_* for backward compatibility OR handle name sort inline after repo returns.
        if sort_l not in {
            "price_asc",
            "price_desc",
            "created_asc",
            "created_desc",
            "name_asc",
            "name_desc",
        }:
            raise BadRequest("Invalid sort parameter")
    else:
        sort_l = None

    # Price validations: ensure numeric decimal-like strings
    def _coerce_price(val: Optional[str]) -> Optional[str]:
        if val is None or val == "":
            return None
        try:
            # We don't convert to Decimal here; storage._to_decimal will handle it
            float(val)  # basic validation
            return val
        except Exception:
            raise BadRequest("min_price/max_price must be numbers")

    min_price = _coerce_price(min_price)
    max_price = _coerce_price(max_price)

    return {
        "q": q,
        "category": category,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort_l,
    }


@blp.route("")
class ProductsListCreate(MethodView):
    """List products with pagination and filters; create new products."""

    @blp.arguments(PaginationQuerySchema, location="query")
    @blp.response(200, ProductListResponseSchema, description="Paginated list of products with metadata.")
    def get(self, pagination_args: dict):
        """List products with optional filters and sorting.

        Query parameters:
        - page: integer, 1-indexed (default 1)
        - page_size: integer, items per page (default: server config DEFAULT_PAGE_SIZE)
        - q: string, free text search across name, description, sku, and tags
        - category: string, filter products where any tag contains this category term
        - min_price: number/string, minimum price inclusive
        - max_price: number/string, maximum price inclusive
        - sort: string, one of:
            - price_asc, price_desc
            - name_asc, name_desc
            - created_asc, created_desc (default created_desc)

        Returns:
        - data: Array of product objects
        - pagination: Metadata including total, page, total_pages, next/previous links
        """
        page = pagination_args.get("page", 1)
        page_size = pagination_args.get("page_size")
        filters = _parse_list_query_params(request.args)

        products_repo = get_products_repo()

        # Our repo supports sorting by price_* and created_*. It does not support name_* directly.
        repo_sort = filters["sort"]
        if repo_sort in ("name_asc", "name_desc"):
            # Perform sort after fetching filtered list without pagination,
            # then paginate manually using the same helper.
            # We'll call repo.list with page=1 and large page_size to get all filtered results.
            items, _ = products_repo.list(
                page=1,
                page_size=10_000,  # sufficiently large for demo; real impl should support name sort in repo
                q=filters["q"],
                category=filters["category"],
                price_min=filters["min_price"],
                price_max=filters["max_price"],
                sort="created_desc",  # deterministic base order
                include_inactive=False,
            )
            reverse = repo_sort == "name_desc"
            items.sort(key=lambda p: (p.get("name") or "").lower(), reverse=reverse)

            # Use the same pagination helper for consistent metadata
            default_page_size = int(current_app.config.get("DEFAULT_PAGE_SIZE", 10))
            # Reuse paginate_list via repository module to keep logic consistent
            from ..services.storage import paginate_list as _paginate

            page_items, meta = _paginate(items, page, page_size, default_page_size)
            return {"data": page_items, "pagination": meta}

        # Normal path: use repo's pagination and sorting
        items, meta = products_repo.list(
            page=page,
            page_size=page_size,
            q=filters["q"],
            category=filters["category"],
            price_min=filters["min_price"],
            price_max=filters["max_price"],
            sort=repo_sort,
            include_inactive=False,
        )
        return {"data": items, "pagination": meta}

    @blp.arguments(ProductCreateSchema, location="json")
    @blp.response(201, PublicProductSchema, description="Created product.")
    def post(self, json_data: dict):
        """Create a new product.

        Request body: ProductCreateSchema
        Returns: Created product.
        """
        products_repo = get_products_repo()
        try:
            product = products_repo.create(json_data)
        except ValueError as e:
            raise BadRequest(str(e))
        return product


@blp.route("/<string:product_id>")
class ProductDetail(MethodView):
    """Retrieve, update, or delete a single product by id."""

    @blp.response(200, PublicProductSchema, description="Product by id.")
    def get(self, product_id: str):
        """Get a product by its id."""
        products_repo = get_products_repo()
        product = products_repo.get(product_id)
        if not product:
            raise NotFound("Product not found")
        return product

    @blp.arguments(ProductUpdateSchema, location="json")
    @blp.response(200, PublicProductSchema, description="Updated product.")
    def patch(self, json_data: dict, product_id: str):
        """Update product fields.

        Request body: ProductUpdateSchema (partial)
        Returns: Updated product.
        """
        products_repo = get_products_repo()
        try:
            updated = products_repo.update(product_id, json_data)
        except ValueError as e:
            raise BadRequest(str(e))
        if not updated:
            raise NotFound("Product not found")
        return updated

    @blp.response(204, description="Product deleted.")
    def delete(self, product_id: str):
        """Delete a product by id. Returns no content on success."""
        products_repo = get_products_repo()
        deleted = products_repo.delete(product_id)
        if not deleted:
            raise NotFound("Product not found")
        # flask-smorest will format empty body with 204 automatically when returning None
        return None
