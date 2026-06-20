# Medication Inventory

Manage medications, suppliers, and orders. Export orders as PDF.

Built with Django, PostgreSQL, Docker.

---

## Deployment Setup

### Prerequisites

- Docker (v20+)
- Docker Compose (v2+)

### 1. Create a directory on your server

```bash
mkdir medication-inventory && cd medication-inventory
```

### 2. Download the deployment compose file

Copy [`deploy/docker-compose.yml`](deploy/docker-compose.yml) from this repository into the directory.

### 3. Create `.env`

Copy [`deploy/.env.example`](deploy/.env.example) to `.env` and adjust the values:

⚠️ You **must** change `DJANGO_SECRET_KEY`. Change `POSTGRES_PASSWORD` if the database port is exposed.

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 4. Start

```bash
docker compose pull
docker compose up -d
```

First start automatically runs migrations, collects static files, and creates a default admin account.

### 5. Access

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | Application |
| `http://localhost:8000/admin/` | Admin panel |

### 6. Default admin account

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

Change immediately:

```bash
docker compose exec web python manage.py changepassword admin
```

---

## Management

### Common operations

| Action | Command |
|--------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f web` |
| Update | `docker compose pull && docker compose up -d` |
| Django shell | `docker compose exec web python manage.py shell` |
| Create superuser | `docker compose exec web python manage.py createsuperuser` |
| Change password | `docker compose exec web python manage.py changepassword <username>` |

### Backup & Restore

| Action | Command |
|--------|---------|
| Create backup | `docker compose exec web python manage.py backup_db` |
| Create compressed backup | `docker compose exec web python manage.py backup_db --compress` |
| List backups | `docker compose exec web python manage.py list_backups` |
| Restore from file | `docker compose exec web python manage.py restore_db /app/backups/<filename>` |
| Restore (no prompt) | `docker compose exec web python manage.py restore_db /app/backups/<filename> --no-confirm` |

Backup files are stored in `./data/backups/` on the host.

### Scheduled backups

1. Go to `/admin/` → **Backup Settings**
2. Set **Schedule** to Daily / Weekly / Monthly
3. Set **Retention days** (0 = keep forever)
4. Save

A cron job inside the container checks hourly whether a backup is due.

---

## Local Development

```bash
git clone <repository-url>
cd medication-inventory
cp .env.example .env   # edit values
docker compose up --build
```

---

## Data directory

All persistent data is stored in bind mounts:

```
./data/
├── postgres/       ← Database files
├── backups/        ← Backup .sql/.sql.gz files
└── staticfiles/    ← Collected static files
```

---

## Health Check

```bash
curl http://localhost:8000/health/
```

Returns `{"status": "ok"}`.

---

## Disclaimer

This software is provided for organizational purposes only (inventory tracking, order management). It is **not** a medical device and must not be used for clinical decision-making.

Use at your own risk. The authors accept no liability for loss of data, incorrect orders, or any other damages arising from the use of this software. Always verify orders independently before submission to suppliers.