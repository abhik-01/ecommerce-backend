"""End-to-end smoke test for the ecommerce microservices stack.

Runs the full user journey against the nginx API gateway (http://localhost:80)
after `docker-compose up --build -d`. Each step prints PASS/FAIL.

Usage:
    python scripts/e2e_test.py
    BASE_URL=http://localhost python scripts/e2e_test.py
"""
import os
import sys
import time
import uuid

import requests

BASE_URL = os.getenv('BASE_URL', 'http://localhost').rstrip('/')
OAUTH_CLIENT_ID = os.getenv('OAUTH2_CLIENT_ID', 'ecommerce-client')
OAUTH_CLIENT_SECRET = os.getenv('OAUTH2_CLIENT_SECRET', 'ecommerce-secret')

PASS = 0
FAIL = 0


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def main():
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPass123!"
    print(f"\n=== E2E test against {BASE_URL} (user: {email}) ===\n")

    # 1. Signup
    print("1. Signup")
    r = requests.post(f"{BASE_URL}/auth/signup/", json={'email': email, 'password': password})
    check("signup returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # 2. Login via OAuth2 password grant -> get JWT
    print("2. Login (OAuth2 password grant)")
    r = requests.post(
        f"{BASE_URL}/o/token/",
        data={
            'grant_type': 'password',
            'username': email,
            'password': password,
            'client_id': OAUTH_CLIENT_ID,
            'client_secret': OAUTH_CLIENT_SECRET,
        },
    )
    token_data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    jwt_token = token_data.get('jwt_token')
    check("token endpoint returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    check("response contains jwt_token", bool(jwt_token), str(token_data)[:200])
    auth = {'Authorization': f'Bearer {jwt_token}'} if jwt_token else {}

    # 3. Validate the JWT
    print("3. Validate token")
    r = requests.post(f"{BASE_URL}/auth/validate/", headers=auth)
    body = r.json() if r.ok else {}
    check("validate returns valid=True", r.status_code == 200 and body.get('valid') is True, r.text[:200])
    check("validate returns user identity", bool(body.get('user_id')) and body.get('email') == email, str(body)[:200])

    # 4. Browse products (public — no auth required)
    print("4. List products (public)")
    r = requests.get(f"{BASE_URL}/products/")
    check("products list returns 200 without auth", r.status_code == 200, f"got {r.status_code}")

    # 5. Create a product (auth required)
    print("5. Create product (auth required)")
    r = requests.post(
        f"{BASE_URL}/products/",
        headers=auth,
        json={'title': 'E2E Widget', 'description': 'test', 'price': '199.99', 'category': 'E2E', 'image_url': ''},
    )
    check("create product returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    product = r.json() if r.ok else {}
    product_id = product.get('id')

    # 5b. Anonymous create should be rejected
    r = requests.post(
        f"{BASE_URL}/products/",
        json={'title': 'Blocked', 'description': 'x', 'price': '9.99', 'category': 'E2E', 'image_url': ''},
    )
    check("anonymous create is rejected (401/403)", r.status_code in (401, 403), f"got {r.status_code}")

    # 6. Add to cart (auth required, user_id taken from JWT)
    print("6. Add to cart")
    r = requests.post(
        f"{BASE_URL}/cart/add/",
        headers=auth,
        json={'product_data': {'product_id': str(product_id or '1'), 'name': 'E2E Widget',
                               'price': 199.99, 'quantity': 1}, 'quantity': 1},
    )
    check("add to cart returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # 6b. Anonymous cart access rejected
    r = requests.get(f"{BASE_URL}/cart/by_user/")
    check("anonymous cart access rejected (401/403)", r.status_code in (401, 403), f"got {r.status_code}")

    # 7. Review cart
    print("7. Review cart")
    r = requests.get(f"{BASE_URL}/cart/by_user/", headers=auth)
    check("review cart returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # 8. Create order
    print("8. Create order")
    r = requests.post(
        f"{BASE_URL}/orders/",
        headers=auth,
        json={'items': [{'product_id': product_id or 1, 'quantity': 1, 'price': '199.99'}],
              'total_amount': '199.99'},
    )
    check("create order returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

    # 9. Notifications consumed from Kafka (user.registered, order.created)
    print("9. Check notification logs (Kafka consumed)")
    time.sleep(3)  # give the consumer a moment
    r = requests.get(f"{BASE_URL}/notifications/", headers=auth)
    check("notifications endpoint returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # Summary
    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===\n")
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
