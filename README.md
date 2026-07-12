# Ecommerce Backend — Microservices Platform

A production-grade, event-driven e-commerce backend built with Django REST
Framework, decomposed into six independently deployable microservices that
communicate synchronously through an API gateway and asynchronously through
Apache Kafka.

Built as the Capstone Project for the Scaler Neovarsity – Woolf MS in
Computer Science (Backend Specialization).

---

## Architecture

```
                                   Client
                                     |
                                     v
                              nginx API Gateway
                                     |
        +---------+---------+--------+------+-------------+----------------+
        |         |         |               |             |                |
        v         v         v               v             v                v
  userservice cartservice productservice orderservice paymentservice notificationservice
        |         |         |               |             |                |
      MySQL    MongoDB    MySQL +         MySQL         MySQL            MySQL
        |      + Redis   Elasticsearch      |             |                |
        |         |      + Redis            |             |                |
        |         |         |               |             |                |
        +---------+---------+------> Apache Kafka <----+-------------------+
                          (async events between services)
```

Each service owns its own database — there is no shared schema between
services. Client-facing communication goes through the nginx gateway;
cross-service workflows (e.g. "confirm an order once payment succeeds") are
driven entirely by Kafka events, so services stay decoupled and can fail or
scale independently.

| Service | Port | Database(s) | Responsibility |
|---|---|---|---|
| **userservice** | MySQL | Registration, OAuth2 + JWT login, profile, password change |
| **cartservice** | MongoDB, Redis | Shopping cart CRUD, cached reads, checkout event |
| **productservice** | MySQL, Elasticsearch, Redis | Product/category catalog, search, cached reads |
| **orderservice** | MySQL | Order creation, tracking, auto-confirm via Kafka |
| **paymentservice** | MySQL | Stripe/Razorpay integration, webhooks, refunds |
| **notificationservice** | MySQL | Kafka consumer → email notifications, audit log |
| **nginx** (gateway) | Single entry point, routes by URL prefix |

## Authentication

Login uses an OAuth2 password grant (`django-oauth-toolkit`) and additionally
issues a short-lived **JWT** (HS256, 1-hour expiry) carrying `user_id`,
`email`, and `role`. The OAuth2 token is the standards-compliant credential
returned to clients; the JWT is what every downstream service verifies
**locally**, without a database round-trip, using a shared `JWT_SECRET_KEY`.

## Event-Driven Workflow

| Event (Kafka topic) | Producer | Consumer(s) | Effect |
|---|---|---|---|
| `user.registered` | userservice | notificationservice | Welcome email |
| `cart.checkout` | cartservice | orderservice | Begin order from cart |
| `order.created` | orderservice | notificationservice | Order confirmation email |
| `order.status.updated` | orderservice | notificationservice | Status update email |
| `payment.completed` | paymentservice | orderservice, notificationservice | Order → `CONFIRMED`; receipt email |
| `payment.failed` | paymentservice | orderservice, notificationservice | Order → `CANCELLED`; failure email |

## Tech Stack

- **API framework:** Django REST Framework
- **Relational DB:** MySQL 8.0 (one logical database per service)
- **Document DB:** MongoDB 7 (cart service)
- **Cache:** Redis 7 (product + cart read caching)
- **Message broker:** Apache Kafka (+ Zookeeper)
- **Search:** Elasticsearch 8 (product full-text search, with DB fallback)
- **Auth:** OAuth2 (django-oauth-toolkit) + JWT (PyJWT)
- **Gateway:** nginx
- **Payments:** Stripe, Razorpay
- **Containerization:** Docker, Docker Compose

## Repository Structure

```
├── docker-compose.yml        # orchestrates all infra + services
├── nginx/
│   └── nginx.conf            # API gateway routing
├── scripts/
│   ├── mysql-init.sql        # creates the 5 per-service MySQL databases
│   └── e2e_test.py           # full user-journey test against the gateway
├── userservice/
│   ├── authservice/          # app: models, views, serializers, kafka_producer, authentication
│   ├── userservice/          # Django project: settings, urls, wsgi
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── cartservice/                # same per-service layout
├── productservice/             # same per-service layout
├── orderservice/               # same per-service layout
├── paymentservice/             # same per-service layout
└── notificationservice/        # same per-service layout
```

Every service is self-contained: its own Django project, app, Dockerfile,
`requirements.txt`, and `.env.example`. This lets each one be built,
deployed, and scaled independently of the others.

## Getting Started

### Prerequisites

- Docker Desktop
- Ports free on the host: `80`, `2181`, `3307`, `6379`, `9092`, `9200`,
  `27017`, and `8001`–`8006` (MySQL is mapped to host port **3307**, not
  3306, to avoid clashing with a locally installed MySQL instance)

### Run the full stack

```bash
docker compose up --build -d
docker compose ps        # all 15 containers should be Up/healthy
```

This starts: MySQL, MongoDB, Redis, Zookeeper, Kafka, Elasticsearch, all six
microservices, the order-service and notification-service Kafka consumers,
and the nginx gateway.

### Verify it's up

```bash
curl http://localhost/health             # nginx gateway
curl http://localhost:8001/health/       # userservice
curl http://localhost:8003/health/       # productservice
```

### Run the end-to-end test

```bash
python scripts/e2e_test.py
```

Walks the full user journey through the gateway: signup → OAuth2/JWT login →
token validation → browse/create products → add to cart → place order →
notifications — and prints a PASS/FAIL summary per step.

## Running Unit Tests

Each service has its own virtual environment and test suite (pytest +
pytest-django). From a service directory:

```bash
cd userservice
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
pytest
```

Repeat per service (`cartservice`, `productservice`, `orderservice`,
`paymentservice`, `notificationservice`). 88 unit tests pass across all six
services in total.

## API Entry Points (via the gateway, `http://localhost`)

| Prefix | Routed to | Example |
|---|---|---|
| `/auth/*` | userservice | `POST /auth/signup/`, `POST /auth/validate/` |
| `/o/*` | userservice | `POST /o/token/` (OAuth2 + JWT login) |
| `/products/*`, `/categories/*` | productservice | `GET /products/`, `GET /products/search/?q=...` |
| `/cart/*` | cartservice | `POST /cart/add/`, `GET /cart/by_user/` |
| `/orders/*` | orderservice | `POST /orders/`, `GET /orders/{id}/tracking/` |
| `/payments/*` | paymentservice | `POST /payments/initiate/`, webhooks |
| `/notifications/*` | notificationservice | `GET /notifications/` |

Each service also exposes its own health check directly on its host port for
testing outside the gateway: `GET /health/` on userservice, cartservice,
productservice, orderservice, and paymentservice (8001–8005); `GET
/api/notifications/health/` on notificationservice (8006).

## Configuration

Every service reads its configuration from a `.env` file (see each
service's `.env.example` for the required variables — database credentials,
`JWT_SECRET_KEY` (must be identical across all services), Kafka bootstrap
servers, and, for `paymentservice`, the Stripe/Razorpay API keys). In
`docker-compose.yml`, infrastructure hostnames (MySQL, Mongo, Redis, Kafka,
Elasticsearch) are overridden to their container network names automatically.

## Project Report

The full Applied Software Project Report (architecture, database schema,
class diagrams, feature deep-dive with performance benchmarking, and AWS
deployment design) was written separately per the Woolf report template and
submitted alongside this repository as a PDF.
