# RentalHousing — Django/DRF Backend

A full‑featured backend for a rental housing service: listings, bookings, reviews, moderation, rich filtering and statistics. The project runs in Docker, uses MySQL, authenticates with JWT (access/refresh, httpOnly cookies supported), and ships interactive API docs (Swagger/Redoc).

---

## ✨ Features

- **Authentication & Roles**
  - Sign‑up / sign‑in via email/username & password.
  - JWT (access/refresh), optional httpOnly cookies.
  - Roles: `lessor` (host), `renter` (guest), `moderator`.
- **Listings**
  - CRUD with attributes: price, rooms, housing type, max guests, baby cribs, kitchen, parking, pets, city/district.
  - Filters & ordering:
    - `price_min` / `price_max` (>=, <=)
    - `rooms_min` / `rooms_max` (>=, <=)
    - `guests` → `max_guests__gte`
    - `baby_cribs` → `max_baby_crib__gte`
    - `has_kitchen`, `parking_available`, `pets_possible` (Choice/boolean)
    - `city`, `district`, `type_housing` (`iexact`)
    - Ordering by `created_at`, `price`, `rooms`, `max_guests`.
  - Pagination: **CursorPagination** (default, 6 items/page).
- **Bookings**
  - Created by renter, approved by lessor.
  - Statuses: `pending`, `approved`, `cancelled`, `completed`.
- **Reviews**
  - Can be created for completed bookings.
  - Moderation (`is_valid`) for moderators/admins.
  - Owner comment (`owner_comment`) for the listing owner.
- **Statistics**
  - `ListingView` — per‑listing views (user/session).
  - `ListingStats` — aggregates: `views_count`, `reviews_count`, `avg_rating`.
  - `SearchQuery` — actual search requests (keywords + params JSON).
  - `SearchQueryStats` — aggregated keyword counters.

---

## 🧱 Tech Stack

- **Python 3.12+/3.13**, **Django 5**, **Django REST Framework**
- **MySQL 8** (`mysqlclient`)
- **JWT** via `djangorestframework-simplejwt`
- **django-filter**, **drf-yasg** (Swagger/Redoc)
- **Docker / Docker Compose**, **Gunicorn**
- Tests: **pytest / pytest-django**

---

## 🚀 Quick Start (Docker)

1. Create `.env` (example):
   ```env
   DJANGO_ENV=prod
   DEBUG=True
   SECRET_KEY=your-secret
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   MYSQL=True
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=passw
   MYSQL_DATABASE=RentalHousing
   ```

2. Example `docker-compose.yml`:
   ```yaml
   version: "3.9"
   services:
     db:
       image: mysql:8
       environment:
         MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
         MYSQL_DATABASE: ${MYSQL_DATABASE}
       ports:
         - "3306:3306"
       volumes:
         - dbdata:/var/lib/mysql
     web:
       build: .
       env_file: .env
       depends_on:
         - db
       ports:
         - "8000:8000"
   volumes:
     dbdata:
   ```

3. Apply migrations and create a superuser (optional):
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

4. Open:
   - API: `http://localhost:8000/api/v1/`
   - Swagger: `http://localhost:8000/schema/swagger-ui/`
   - Redoc: `http://localhost:8000/schema/redoc/`

> **Note:** If you use JWT in httpOnly cookies, make requests against the **same host & scheme** you used for login (don’t mix `localhost` with `127.0.0.1`; `Secure` cookies require HTTPS).

---

## 🔑 Authentication (JWT)

- **Register**: `POST /api/v1/auth/register/`
- **Login**: `POST /api/v1/auth/login/` → sets `access_token` / `refresh_token` httpOnly cookies (or returns tokens in body if configured).
- **Refresh access**: `POST /api/v1/auth/refresh/`
- **Logout**: `POST /api/v1/auth/logout/` (clears cookies; optional refresh blacklist).

Example:
```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8000/api/v1/user/me/
```

---

## 🧭 Key Endpoints (excerpt)

- **Listings**
  - `GET /api/v1/listings/?price_min=50&price_max=150&rooms_min=2&guests=3&has_kitchen=true&city=Berlin&ordering=-created_at`
  - `POST /api/v1/listings/` — create (role `lessor`)
- **Bookings**
  - `POST /api/v1/bookings/` — create (role `renter`)
  - `POST /api/v1/bookings/{id}/approve/` — approve (role `lessor`)
- **Reviews**
  - `POST /api/v1/reviews/` — create for completed booking
  - `POST /api/v1/reviews/{id}/moderate-validate/` — set `is_valid=true/false` (moderator/admin)
  - `POST /api/v1/reviews/{id}/owner-comment` — set `owner_comment` (listing owner/admin)
  - `GET  /api/v1/reviews/{id}/` — detail (mind the trailing slash)
- **Statistics**
  - `ListingView` is recorded when a listing page is viewed.
  - `ListingStats` recalculated from views & reviews.
  - `SearchQuery` stores performed searches (keywords + params).
  - `SearchQueryStats` aggregates keyword counts.

---

## 📊 Seeding / Recompute Stats

Management command (example):
```bash
# generate views & searches, then recompute aggregates
python manage.py seed_stats
```

Or call functions in shell:
```python
from your_app.management.commands.seed_stats import (
    seed_listing_views, seed_search_queries,
    recompute_search_query_stats, recompute_listing_stats,
)

seed_listing_views(50)
seed_search_queries(25)
recompute_search_query_stats()
recompute_listing_stats()
```

---

## 🧪 Testing

- **pytest**:
  ```bash
  pip install pytest pytest-django
  # pytest.ini:
  # [pytest]
  # DJANGO_SETTINGS_MODULE = django_learn.settings
  # pythonpath = .
  pytest -q
  ```
- For integration tests with auth, send `Authorization: Bearer <access>` (or rely on cookies with a cookie→header middleware).

---

## 🐳 Dockerfile (build)

Based on `python:3.13-slim`, installs deps (`default-libmysqlclient-dev`, `pkg-config`, `build-essential`), runs Gunicorn:

```dockerfile
FROM python:3.13-slim
RUN apt-get update && apt-get install -y     default-libmysqlclient-dev pkg-config build-essential     && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "RentalHousing.wsgi:application", "--bind", "0.0.0.0:8000"]
```


---

## 🔧 Troubleshooting

- **`Authentication credentials were not provided.`**
  - Use the same host/scheme for login and API calls.
  - If tokens are in httpOnly cookies but DRF expects a header, add a cookie→header middleware or send `Authorization: Bearer`.
  - Use trailing slashes to avoid 301 redirects that may drop headers.
- **MySQL in Docker not reachable from host**
  - Expose port: `ports: "3306:3306"` and connect to `127.0.0.1:3306`.
  - Container→container: use service name (e.g., `db:3306`).
- **Installing `mysqlclient` on macOS (Apple Silicon)**
  - `brew install mysql-client pkg-config` and set `PKG_CONFIG_PATH`, `LDFLAGS`, `CPPFLAGS`.

---

## 📜 License

BSD-3-Clause (see `LICENSE` if provided).

---

## 📫 Contact

Questions / PRs / feedback — open an issue or reach out via the repository.
