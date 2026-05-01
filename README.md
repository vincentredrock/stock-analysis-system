# Stock Analysis System

A full-stack Taiwan stock market data platform with JWT authentication, real-time quotes, historical price charts, and personalized watchlists.

## Overview

- **Backend**: FastAPI (Python 3.12) + SQLAlchemy + Alembic + PostgreSQL
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS + Zustand + TanStack Query
- **Auth**: JWT access/refresh tokens with blacklist logout
- **Data**: Taiwan stock data powered by `twstock`
- **Scheduler**: APScheduler for daily historical price sync

## Features

- **User Authentication** — register, login, logout, token refresh
- **Stock Search** — search TWSE/TPEx stocks by symbol or name
- **Real-time Quotes** — fetch live stock quotes
- **Historical Prices** — view OHLCV historical data with date range filtering
- **Watchlists** — create personal watchlists and track stock quotes
- **Daily Sync** — automatic background sync of historical prices (configurable)
- **Responsive UI** — modern SPA built with React and Tailwind CSS

## Project Structure

```
.
├── app/                        # FastAPI backend
│   ├── main.py                 # Application entry point
│   ├── config.py               # Pydantic settings
│   ├── database.py             # SQLAlchemy engine & session
│   ├── models.py               # Database models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── security.py             # Password hashing & JWT utils
│   ├── dependencies.py         # FastAPI dependencies
│   ├── scheduler.py            # Background job scheduler
│   ├── routers/
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── stocks.py           # Stock data endpoints
│   │   └── watchlists.py       # Watchlist endpoints
│   └── services/
│       └── stock_data.py       # Taiwan stock data service
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── pages/              # Page components
│   │   ├── components/         # Shared components
│   │   ├── api/                # API clients
│   │   ├── stores/             # Zustand state stores
│   │   ├── types/              # TypeScript types
│   │   └── lib/                # Utilities
│   └── dist/                   # Production build output
├── tests/                      # Backend test suite (pytest)
├── alembic/                    # Database migrations
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── Dockerfile                  # Container image
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+

### 1. Database Setup

Create a PostgreSQL database and set the `postgres` user password:

```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '1111';"
sudo -u postgres psql -c "CREATE DATABASE stock_analysis;"
```

Update `.env`:

```env
DATABASE_URL=postgresql://postgres:1111@localhost:5432/stock_analysis
SECRET_KEY=your-secret-key-here
```

Run migrations:

```bash
python3 -m alembic upgrade head
```

### 2. Backend Setup

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

API docs will be available at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies API to localhost:8000)
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 4. Production Build

```bash
cd frontend
npm run build
```

The FastAPI backend will automatically serve the built frontend from `frontend/dist/`.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users` | Create a new user |
| GET | `/api/v1/users/me` | Get current user profile |
| POST | `/api/v1/sessions` | Create a session and get tokens |
| DELETE | `/api/v1/sessions/current` | Delete the current session |
| POST | `/api/v1/token-refreshes` | Rotate a refresh token and get a new token pair |

### Stocks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/stocks?q={query}` | List or search stocks by symbol/name |
| GET | `/api/v1/stocks/{symbol}` | Get stock details |
| GET | `/api/v1/stocks/{symbol}/quotes/latest` | Get latest quote |
| GET | `/api/v1/stocks/{symbol}/prices` | Get historical prices |
| POST | `/api/v1/stocks/{symbol}/sync` | Trigger historical price sync |

### Watchlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/watchlists` | List user's watchlists |
| POST | `/api/v1/watchlists` | Create a watchlist |
| GET | `/api/v1/watchlists/{id}` | Get watchlist details |
| DELETE | `/api/v1/watchlists/{id}` | Delete a watchlist |
| POST | `/api/v1/watchlists/{id}/items` | Add stock to watchlist |
| DELETE | `/api/v1/watchlists/{id}/items/{symbol}` | Remove stock from watchlist |
| GET | `/api/v1/watchlists/{id}/quotes` | Get quotes for watchlist stocks |

## Testing

Run the backend test suite:

```bash
python3 -m pytest tests/ -v
```

The project includes 125+ tests covering authentication, security, stocks, watchlists, and schema validation.

## Docker

Build and run with Docker:

```bash
docker build -t stock-analysis .
docker run -p 8080:8080 --env-file .env stock-analysis
```

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | random | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | * | Allowed CORS origins |
| `STOCK_DAILY_SYNC_ENABLED` | true | Enable daily price sync |
| `STOCK_DAILY_SYNC_HOUR` | 16 | Daily sync hour (24h) |
| `STOCK_DAILY_SYNC_MINUTE` | 30 | Daily sync minute |

Frontend builds use these Vite variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_ORIGIN` | same origin | Backend origin, for example `https://backend.example.com` |
| `VITE_API_PREFIX` | `/api/v1` | API path prefix appended to `VITE_API_ORIGIN` |
| `VITE_API_URL` | — | Backward-compatible API base. If it omits `/api/v1`, the frontend appends `VITE_API_PREFIX`. |

## Tech Stack

**Backend**
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL (psycopg2)
- python-jose + bcrypt
- APScheduler
- twstock

**Frontend**
- React 19
- TypeScript
- Vite
- Tailwind CSS
- Zustand (state management)
- TanStack Query (data fetching)
- React Hook Form + Zod (forms & validation)
- React Router v7
- Lightweight Charts
- Lucide React
- Sonner (toasts)

## License

MIT
