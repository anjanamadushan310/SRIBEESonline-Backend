# SRIBEESonline FastAPI Backend

Modern, high-performance e-commerce API built with FastAPI.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

1. **Clone and navigate to the FastAPI backend:**
   ```bash
   cd fastapi_backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using Poetry (recommended)
   poetry install
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the server:**
   ```bash
   # Development mode with hot reload
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or use the Python entry point
   python -m app.main
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - Swagger Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📁 Project Structure

```
fastapi_backend/
├── alembic/                    # Database migrations
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config/                 # Configuration
│   │   ├── settings.py         # Pydantic settings
│   │   ├── database.py         # PostgreSQL setup
│   │   └── redis.py            # Redis setup
│   ├── core/                   # Core utilities
│   │   ├── security.py         # JWT & password hashing
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── api/                    # API routes
│   │   └── v1/
│   │       ├── router.py       # Main router
│   │       └── auth.py         # Auth endpoints
│   ├── services/               # Business logic
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── pyproject.toml              # Poetry config
├── requirements.txt            # Pip requirements
└── README.md
```

## 🔐 Authentication

The API uses JWT Bearer authentication:

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123", "fullName": "John Doe"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'

# Authenticated request
curl http://localhost:8000/api/v1/cart \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 📚 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/verify-email` | Verify email |
| POST | `/api/v1/auth/resend-verification` | Resend verification |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Reset password |
| POST | `/api/v1/auth/refresh-token` | Refresh tokens |
| POST | `/api/v1/auth/logout` | Logout user |

### Branch Routing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/branch/resolve` | Resolve address → branch, set session |
| GET | `/api/v1/branch/context` | Get current branch context |
| POST | `/api/v1/branch/clear` | Clear branch context |

### App Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/app/splash-config` | Get splash video URL (public, cached) |

### Location Discovery
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/locations/provinces` | List all provinces |
| GET | `/api/v1/locations/districts` | List districts by province |
| GET | `/api/v1/locations/post-offices` | List post offices by district |

### Marketing (Branch-Restricted)
| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/v1/marketing/inventory/{id}` | Update branch discount/price |

### Inventory Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/inventory/my-branch` | Branch products with overrides |
| PUT | `/api/v1/inventory/update-stock/{id}` | Update stock quantity |
| PUT | `/api/v1/inventory/update-pricing/{id}` | Update branch pricing |

### Search (AI-Powered)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search` | Semantic product search (Gemini + pgvector) |
| GET | `/api/v1/search/suggestions` | Autocomplete suggestions |
| GET | `/api/v1/search/popular` | Trending search queries |
| GET | `/api/v1/search/health` | Search service health check |

## 🔍 Semantic Search

The API includes AI-powered multilingual semantic search:

```bash
# Search in English
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "fresh organic apples"}'

# Search in Sinhala
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "රතු ඇපල් ගෙඩි"}'

# Search in Tamil
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "சிவப்பு ஆப்பிள்"}'
```

**Features:**
- 🧠 Gemini text-embedding-004 (768 dimensions)
- 🌐 Multilingual: English, Sinhala, Tamil, Singlish
- ⚡ pgvector for fast vector similarity search
- 🔄 Automatic fallback to keyword search
- 💾 Redis caching for embeddings & results

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## 🐳 Docker

```bash
# Start via Docker Compose (recommended)
docker compose up -d --build fastapi_backend

# View logs
docker compose logs -f fastapi_backend

# Access container shell
docker exec -it sribees_backend bash

# Restart after code changes
docker restart sribees_backend
```

### Docker Environment Variables

| Variable | Value (Local Dev) | Description |
|----------|-------------------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://sribees_user:sribees_password_123@postgres_db:5432/sribeesonline` | PostgreSQL connection |
| `REDIS_URL` | `redis://:sribees_redis_password@redis_cache:6379/0` | Redis connection |
| `S3_ENDPOINT_URL` | `http://s3-local:9000` | MinIO S3 endpoint (internal) |
| `S3_PUBLIC_URL_PREFIX` | `http://localhost:9000/sribees-assets` | Public S3 URL |
| `S3_EMULATOR_URL_PREFIX` | `http://10.0.2.2:9000/sribees-assets` | Android emulator S3 URL |

## 🗃️ SQL Migrations

Database migrations are stored in `fastapi_backend/migrations/` as numbered SQL files:

| Migration | Description |
|-----------|-------------|
| `001-010` | Core tables (users, products, orders, payments, notifications, variants, RBAC, search) |
| `011` | Post Office → Branch mapping, province/post_office columns on branches |
| `012` | Product discount fields (discount_percentage, discount_price, is_on_sale) |
| `013` | Branch inventory table (branch-specific price/stock overrides) |
| `014` | App settings table (splash video URL, runtime config) |

Run migrations:
```bash
# Inside the backend container
docker exec -i sribees_postgres psql -U sribees_user -d sribeesonline < migrations/011_create_post_office_branch_mapping.sql
```

---

## ⚙️ Configuration

All settings are managed via environment variables. See `.env.example` for available options.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `DEBUG` | Enable debug mode | false |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `REDIS_URL` | Redis connection URL | - |
| `JWT_SECRET_KEY` | JWT signing key | - |
| `GEMINI_API_KEY` | Google Gemini API key for embeddings | - |

## 📈 Performance

FastAPI is one of the fastest Python frameworks:

- **Async-first**: Full async/await support
- **Connection pooling**: Efficient database connections
- **Redis caching**: Fast data access
- **Pydantic v2**: High-performance validation

## 🔄 Migration from Express

This project is a migration from the Node.js/Express backend. Key differences:

| Express | FastAPI |
|---------|---------|
| TypeScript | Python type hints |
| Zod validation | Pydantic schemas |
| pg-promise | SQLAlchemy + asyncpg |
| ioredis | redis-py (async) |
| jsonwebtoken | python-jose |
| argon2 | passlib[argon2] |

## 📝 License

MIT License - See LICENSE file for details.

---

**SRIBEESonline Engineering Team** | February 17, 2026
