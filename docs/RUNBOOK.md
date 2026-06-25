# EuroGrant AI Runbook

## Service Architecture
- Frontend: Next.js 16 (App Router)
- Backend: FastAPI (Python 3.12)
- Database: PostgreSQL 15
- Cache/Queue: Redis (Celery)

## Routine Operations
### Starting the environment
`docker compose up -d`

### Viewing logs
`docker compose logs -f [backend|frontend|worker|beat|db|redis]`

### Database Migrations
Create: `docker compose exec backend alembic revision --autogenerate -m "msg"`
Apply: `docker compose exec backend alembic upgrade head`

## Emergency Operations
### Application Down / Unresponsive
1. Check container status: `docker compose ps`
2. Check backend logs: `docker compose logs --tail=100 backend`
3. Restart backend if stuck: `docker compose restart backend`

### Database Corruption / Rollback
1. See `scripts/restore_db.sh` to restore from a backup.
2. Example: `./scripts/restore_db.sh backup_xyz.sql`

## Monitoring & Alerts
Metrics are exposed on `/metrics`.
Prometheus and Alertmanager can be started using the `infra` profile.
`docker compose --profile infra up -d`
