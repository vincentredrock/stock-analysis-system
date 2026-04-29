# 2026-04-29 Cloud Run and Neon Deployment

## Summary

Deployed the Stock Analysis System web app to Google Cloud Run and migrated the local PostgreSQL database to Neon.

## Google Cloud

- Project: `asahi-calpis`
- Region: `asia-southeast1`
- Cloud Run service: `stock-analysis`
- Live URL: `https://stock-analysis-6pmfrx4ppq-as.a.run.app`
- Ready revision: `stock-analysis-00002-5tm`
- Traffic: `100%`
- Artifact Registry repository: `stock-analysis`

## Secrets

The Neon database URL and JWT signing key are stored in Google Secret Manager.

- `database-url`: Cloud Run `DATABASE_URL`
- `secret-key`: Cloud Run `SECRET_KEY`

The local `neon_db_string.txt` file was deleted after the database URL was stored in Secret Manager.

## Database Migration

The local PostgreSQL database was migrated to Neon with `pg_dump` and `pg_restore`.

Post-migration verification:

- `users=1`
- `stocks=2301`
- `stock_prices=536236`
- Alembic revision: `9b3a1f2c4d5e`

Neon pooled connections did not provide a default schema search path, so the app and Alembic now set `search_path` to `public` after connecting.

## Container Changes

- The Docker image now builds the Vite frontend and copies `frontend/dist` into the runtime image.
- The runtime command starts only Uvicorn.
- Alembic migrations are no longer run on every container startup.
- The server uses Cloud Run's `PORT` environment variable with a fallback to `8080`.
- `.dockerignore` and `.gcloudignore` exclude local secrets, virtualenvs, node modules, generated frontend assets, and database dump files.

## Cloud Run Runtime Configuration

- `ENVIRONMENT=production`
- `DEBUG=false`
- `STOCK_DAILY_SYNC_ENABLED=false`
- `CORS_ORIGINS=*`
- `DATABASE_URL` from Secret Manager
- `SECRET_KEY` from Secret Manager

The in-process stock scheduler is disabled in Cloud Run to avoid duplicate background jobs when the service scales to multiple instances.

## Verification

- Backend tests: `216 passed`
- Frontend production build: successful
- Cloud Build image build and push: successful
- Cloud Run health check: `GET /health` returned `{"status":"healthy"}`

The `/stocks` endpoint returned `401` without authentication, which is expected because stock APIs require a logged-in user.

## Follow-Up

Rotate the Neon database password and add a fresh `database-url` secret version because an Alembic error traceback printed the database URL during deployment troubleshooting.
