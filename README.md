# Ecommerce API Backend

## Overview
This is a simple Flask backend exposing REST APIs for an ecommerce application. It includes endpoints for authentication, product catalog, shopping cart, and order management. The service auto-seeds an in-memory product catalog at startup and serves an interactive API explorer at /docs with the OpenAPI JSON available at /openapi.json.

## Quick Start
1. Ensure Python 3.10+ is installed.
2. Install dependencies:
   ```
   pip install -r flask_backend/requirements.txt
   ```
3. (Optional) Set environment variables (see Environment Variables).
4. Run the server:
   ```
   python -m flask_backend.run
   ```
5. Open the interactive docs:
   - Swagger UI: http://localhost:3001/docs
   - OpenAPI JSON: http://localhost:3001/openapi.json

Note: In hosted preview, you can use:
- Docs: https://vscode-internal-17505-beta.beta01.cloud.kavia.ai:3001/docs
- OpenAPI: https://vscode-internal-17505-beta.beta01.cloud.kavia.ai:3001/openapi.json

## Environment Variables
The application reads configuration from environment variables in app.config.BaseConfig.

- SECRET_KEY
  - Purpose: Secret key for signing tokens and Flask session security.
  - Default: "dev-secret-key-change-me"
  - Security: Always override in production.

- DEBUG
  - Purpose: Enables Flask debug mode when truthy.
  - Accepted truthy values: "1", "true", "yes", "on" (case-insensitive).
  - Default: False

- DEFAULT_PAGE_SIZE
  - Purpose: Default number of items per page for list endpoints when page_size is not specified.
  - Type: integer
  - Default: 10

Example .env (if you use one):
```
SECRET_KEY=please-change-me
DEBUG=false
DEFAULT_PAGE_SIZE=20
```

## API Documentation
- Swagger UI: GET /docs
  - Interactive API explorer powered by flask-smorest and swagger-ui.
- OpenAPI spec: GET /openapi.json
  - Machine-readable OpenAPI 3.0.3 JSON.

These are configured in app/__init__.py with OPENAPI_URL_PREFIX set to /docs, and the JSON spec served at the default root /openapi.json.

## Authentication
This API uses opaque signed tokens generated via itsdangerous (URLSafeSerializer) using SECRET_KEY. Tokens are returned on login and must be supplied in the Authorization header as Bearer <token> for protected endpoints.

Flow:
1. Register: POST /auth/register
2. Login: POST /auth/login → returns access_token
3. Include Authorization: Bearer <access_token> to call protected endpoints such as /auth/me, /cart, and /orders.

Token generation/verification is implemented in app/services/auth.py. The decorator @require_auth (app/routes/auth.py) validates the bearer token and injects g.current_user for request handlers.

## Endpoints Summary

### Health
- GET /
  - Purpose: Health check; returns {"message": "Healthy"}.

### Auth
- POST /auth/register
  - Body:
    ```
    {
      "email": "user@example.com",
      "password": "P@ssw0rd!",
      "name": "Jane Doe"
    }
    ```
  - 201 Response (example):
    ```
    {
      "id": "usr_abc123...",
      "email": "user@example.com",
      "name": "Jane Doe",
      "created_at": "2025-01-01T12:00:00+00:00"
    }
    ```

- POST /auth/login
  - Body:
    ```
    {
      "email": "user@example.com",
      "password": "P@ssw0rd!"
    }
    ```
  - 200 Response (example):
    ```
    {
      "access_token": "eyJp...signed...",
      "token_type": "Bearer",
      "expires_in": 86400
    }
    ```

- GET /auth/me
  - Requires: Authorization: Bearer <access_token>
  - 200 Response (example):
    ```
    {
      "id": "usr_abc123...",
      "email": "user@example.com",
      "name": "Jane Doe",
      "created_at": "2025-01-01T12:00:00+00:00"
    }
    ```

### Products
- GET /products
  - Query params (validated via PaginationQuerySchema and additional parsing):
    - page (default 1), page_size (default DEFAULT_PAGE_SIZE)
    - q, category, min_price, max_price
    - sort: price_asc, price_desc, name_asc, name_desc, created_asc, created_desc (default created_desc)
  - 200 Response:
    ```
    {
      "data": [ {<PublicProduct>}, ... ],
      "pagination": {
        "total": 15,
        "total_pages": 2,
        "first_page": 1,
        "last_page": 2,
        "page": 1,
        "previous_page": null,
        "next_page": 2
      }
    }
    ```

- POST /products
  - Body (ProductCreateSchema):
    ```
    {
      "name": "Wireless Mouse",
      "description": "Ergonomic 2.4G...",
      "price": "29.99",
      "currency": "USD",
      "sku": "WM-001-BLK",
      "inventory": 120,
      "image_url": "https://...",
      "active": true,
      "tags": ["electronics", "mouse", "wireless"]
    }
    ```
  - 201 Response: PublicProduct

- GET /products/{product_id}
  - 200 Response: PublicProduct
- PATCH /products/{product_id}
  - Body: ProductUpdateSchema (partial)
  - 200 Response: PublicProduct
- DELETE /products/{product_id}
  - 204 No Content

Notes:
- The repository supports sorting by price_* and created_* directly. name_* is handled in the route by sorting in Python and then paginating.

### Cart
All cart endpoints require Authorization: Bearer <access_token>. The cart is associated with the authenticated user for the lifetime of the request. A per-user in-memory cart is ensured via get_or_create; data is not persisted across restarts.

- GET /cart
  - Returns current user's cart as PublicCartSchema with expanded product snapshots and monetary fields as decimal strings.
  - 200 Response (example):
    ```
    {
      "id": "cart_abc...",
      "user_id": "usr_abc...",
      "items": [
        {
          "product": { "id": "prod_...", "name": "Wireless Mouse", "...": "..." },
          "quantity": 2,
          "line_total": "59.98"
        }
      ],
      "currency": "USD",
      "subtotal": "59.98",
      "tax": "6.00",
      "total": "65.98",
      "updated_at": "2025-01-01T12:30:00+00:00"
    }
    ```

- DELETE /cart
  - Clears the cart.
  - 204 No Content

- POST /cart/items
  - Body (CartItemSchema):
    ```
    {
      "product_id": "prod_123",
      "quantity": 1
    }
    ```
  - 200 Response: PublicCartSchema

- PATCH /cart/items/{product_id}
  - Body:
    ```
    { "quantity": 3 }
    ```
  - 200 Response: PublicCartSchema

- DELETE /cart/items/{product_id}
  - 200 Response: PublicCartSchema

### Orders
All order endpoints require Authorization: Bearer <access_token>.

- GET /orders
  - Query params:
    - page (default 1), page_size (default DEFAULT_PAGE_SIZE), sort: created_asc|created_desc
  - 200 Response:
    ```
    {
      "data": [ {<OrderPublic>}, ... ],
      "pagination": { ... }
    }
    ```

- POST /orders
  - Creates an order from the current user's cart. Validates availability and inventory, decrements stock, creates the order, and clears the cart.
  - Body (OrderCreateSchema):
    ```
    {
      "items": [
        { "product_id": "prod_123", "quantity": 2 }
      ],
      "shipping_address": {
        "name": "Jane Doe",
        "line1": "123 Market St",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94103",
        "country": "US"
      },
      "billing_address": null,
      "payment": { "method": "card", "card_token": "tok_abc123", "last4": "4242" },
      "currency": "USD",
      "notes": "Leave at door"
    }
    ```
  - 201 Response (example):
    ```
    {
      "id": "ord_abc...",
      "user_id": "usr_abc...",
      "status": "paid",
      "currency": "USD",
      "items": [
        {
          "product": { "id": "prod_123", "name": "Wireless Mouse", "...": "..." },
          "quantity": 2,
          "unit_price": "29.99",
          "line_total": "59.98"
        }
      ],
      "shipping_address": { "...": "..." },
      "billing_address": { "...": "..." },
      "subtotal": "59.98",
      "tax": "6.00",
      "shipping": "0.00",
      "total": "65.98",
      "payment": { "method": "card", "last4": "4242" },
      "created_at": "2025-01-01T12:35:00+00:00",
      "updated_at": "2025-01-01T12:35:00+00:00"
    }
    ```

- GET /orders/{order_id}
  - Returns the order if it belongs to the current user.
  - 200 Response: OrderPublic

## Error Handling
All errors are returned as JSON with the following shape:
```
{
  "code": 400,
  "status": "Bad Request",
  "message": "Validation failed",
  "errors": {}
}
```
This is standardized via app/errors.py and registered globally in app/__init__.py.

## Example cURL Requests

- Register
  ```
  curl -X POST http://localhost:3001/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"P@ssw0rd!","name":"Jane Doe"}'
  ```

- Login
  ```
  TOKEN=$(curl -s -X POST http://localhost:3001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"P@ssw0rd!"}' | jq -r .access_token)
  ```

- Get Products
  ```
  curl "http://localhost:3001/products?page=1&page_size=10&sort=price_asc"
  ```

- Add to Cart
  ```
  curl -X POST http://localhost:3001/cart/items \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"product_id":"prod_...","quantity":2}'
  ```

- Create Order
  ```
  curl -X POST http://localhost:3001/orders \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "items":[{"product_id":"prod_...","quantity":2}],
      "shipping_address":{"name":"Jane Doe","line1":"123 Market St","city":"San Francisco","state":"CA","postal_code":"94103","country":"US"},
      "payment":{"method":"card","card_token":"tok_abc123","last4":"4242"},
      "currency":"USD"
    }'
  ```

## Notes on Data and Persistence
- Storage is in-memory only (see app/services/storage.py). Data resets when the process restarts.
- A demo catalog of 15 products is seeded automatically at startup (init_storage_seed in app/__init__.py).

## Development Tips
- Use DEBUG=true to enable more verbose logs.
- Update DEFAULT_PAGE_SIZE to adjust API pagination defaults.
- SECRET_KEY must be set to a secure random value in non-development environments.

## Using /docs and /openapi.json
- Navigate to /docs for a visual, interactive API explorer. You can authorize once with a token and try calls directly.
- The OpenAPI document served at /openapi.json can be used with client generators or API gateways. The file is generated at runtime by flask-smorest based on registered blueprints and Marshmallow schemas.

## License
This project is provided for demonstration purposes.
