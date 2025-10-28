# RentalHousing — Django/DRF backend

Полнофункциональный бэкенд для сервиса аренды жилья: объявления, бронирования, отзывы, модерирование, фильтрация по параметрам и статистика. Проект разворачивается в Docker, использует MySQL, авторизацию через JWT (access/refresh, поддержка httpOnly cookies) и предоставляет Swagger-документацию.

---

## ✨ Основные возможности

- **Аутентификация и роли**
  - Регистрация/вход по e-mail/логину и паролю.
  - JWT (access/refresh), поддержка httpOnly cookies.
  - Роли: `lessor` (арендодатель), `renter` (арендатор), `moderator` (модератор).
- **Объявления (Listings)**
  - CRUD, параметры: цена, комнаты, тип жилья, кол-во гостей, детские кроватки, кухня, парковка, питомцы, город/район.
  - Фильтры и сортировки:
    - `price_min/price_max` (>=, <=)
    - `rooms_min/rooms_max` (>=, <=)
    - `guests` → `max_guests__gte`
    - `baby_cribs` → `max_baby_crib__gte`
    - `has_kitchen`, `parking_available`, `pets_possible` (Choice/boolean)
    - `city`, `district`, `type_housing` (`iexact`)
    - Сортировка по `created_at`, `price`, `rooms`, `max_guests`.
  - Пагинация: **CursorPagination** (по умолчанию, 6 элементов/страница).
- **Бронирования (Bookings)**
  - Создание арендатором, последующее подтверждение арендодателем.
  - Статусы: `pending`, `approved`, `cancelled`, `completed`.
- **Отзывы (Reviews)**
  - Создать отзыв можно по завершённому бронированию.
  - Модерация (`is_valid`) доступна модераторам/админам.
  - Комментарий владельца (`owner_comment`) доступен арендодателю объявления.
- **Статистика**
  - `ListingView` — просмотры объявлений (user/session).
  - `ListingStats` — агрегаты по объявлению: `views_count`, `reviews_count`, `avg_rating`.
  - `SearchQuery` — фактические поисковые запросы (ключевые слова + JSON параметров).
  - `SearchQueryStats` — счётчики по ключевым словам.

---

## 🧱 Технологии

- **Python 3.12+/3.13**, **Django 5**, **Django REST Framework**
- **MySQL 8** (через `mysqlclient` или PyMySQL)
- **JWT**: `djangorestframework-simplejwt`
- **django-filter**, **drf-yasg** (Swagger/Redoc)
- **Docker/Docker Compose**, **Gunicorn**
- Тесты: **pytest / pytest-django**

---

## 🚀 Быстрый старт (локально через Docker)

1. Настройте `.env` (пример):
   ```env
   DJANGO_ENV=prod
   DEBUG=True
   SECRET_KEY=your-secret
   ALLOWED_HOSTS=your-host
   MYSQL=True
   MYSQL_HOST=your-mysql-host
   MYSQL_PORT=3306
   MYSQL_USER=your-user
   MYSQL_PASSWORD=your-password
   MYSQL_DATABASE=RentalHousing
   ```

2. Поднимите MySQL и бэкенд (пример `docker-compose.yml`):
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

3. Примените миграции и создайте суперпользователя (если нужно):
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

4. Откройте:
   - API: `http://localhost:8000/api/v1/`
   - Swagger: `http://localhost:8000/schema/swagger-ui/`
   - Redoc: `http://localhost:8000/schema/redoc/`

> **Важно:** если используете JWT в httpOnly cookies, логин/запросы проверяйте на одном и том же хосте/схеме (не смешивайте `localhost` и `127.0.0.1`; для `Secure`-кук нужен HTTPS).

---

## 🔑 Аутентификация (JWT)

- **Регистрация**: `POST /api/v1/auth/register/`
- **Логин**: `POST /api/v1/auth/login/` → выставляет `access_token`/`refresh_token` в httpOnly cookies (или вернёт токены в теле, если настроено).
- **Обновить access по refresh**: `POST /api/v1/auth/refresh/`
- **Выход**: `POST /api/v1/auth/logout/` (удаление кук, опционально — blacklist refresh).

Пример запроса с заголовком:
```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8000/api/v1/user/me/
```

---

## 🧭 Основные эндпоинты (выписка)

- **Listings**
  - `GET /api/v1/listings/?price_min=50&price_max=150&rooms_min=2&guests=3&has_kitchen=true&city=Berlin&ordering=-created_at`
  - `POST /api/v1/listings/` — создать объявление (роль `lessor`)
- **Bookings**
  - `POST /api/v1/bookings/` — создать бронирование (роль `renter`)
  - `POST /api/v1/bookings/{id}/approve/` — подтвердить (роль `lessor`)
- **Reviews**
  - `POST /api/v1/reviews/` — создать отзыв по завершённой броне
  - `POST /api/v1/reviews/{id}/moderate-validate/` — модерация (`is_valid=true/false`, роль `moderator/admin`)
  - `POST /api/v1/reviews/{id}/owner-comment` — комментарий владельца (владелец listing или admin)
  - `GET  /api/v1/reviews/{id}/` — детальный просмотр (не забудьте `/` на конце)
- **Статистика**
  - `ListingView` создаётся при показе карточки объявления.
  - `ListingStats` пересчитывается по просмотрам и отзывам.
  - `SearchQuery` сохраняет поисковые запросы (keywords + params).
  - `SearchQueryStats` агрегирует `keywords → count`.

---

## 📊 Наполнение и пересчёт статистики

Готовая команда-сидер (пример):

```bash
# создать N просмотров и поисковых запросов, затем пересчитать агрегаты
python manage.py seed_stats
```

Можно вызывать функции точечно (через Django shell):
```python
from your_app.management.commands.seed_stats import (
    seed_listing_views, seed_search_queries,
    recompute_search_query_stats, recompute_listing_stats,
)

seed_listing_views(n=50)
seed_search_queries(n=25)
recompute_search_query_stats()
recompute_listing_stats()
```

---

## 🧪 Тестирование

- **pytest**:
  ```bash
  pip install pytest pytest-django
  # pytest.ini:
  # [pytest]
  # DJANGO_SETTINGS_MODULE = django_learn.settings
  # pythonpath = .
  pytest -q
  ```
- Для интеграционных тестов с авторизацией используйте заголовок `Authorization: Bearer <access>` (или куки, если настроен middleware).

---

## 🐳 Dockerfile (сборка)

Проект собирается на `python:3.13-slim`, устанавливает зависимости (`mysqlclient` требует `default-libmysqlclient-dev`, `pkg-config`, `build-essential`), запускается через Gunicorn:

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

> Для HTTPS используйте реверс-прокси (Nginx/Caddy/Traefik) или AWS ALB с ACM-сертификатом.

---

## 🔧 Траблшутинг

- **`Authentication credentials were not provided.`**
  - Убедитесь, что используете **тот же хост** и **схему** для логина и запросов.
  - Если токены в httpOnly cookies, а DRF ждёт заголовок — добавьте middleware/кастомный аутентификатор или передавайте `Authorization: Bearer`.
  - Ходите по URL **со слэшем** (чтобы не терять заголовки на 301).
- **MySQL в Docker не виден с хоста**
  - Поднимите порт: `ports: "3306:3306"` и подключайтесь к `127.0.0.1:3306`.
  - Из контейнера к контейнеру — по имени сервиса (например, `db:3306`).
- **Установка `mysqlclient` на macOS (M1/M2)**
  - `brew install mysql-client pkg-config` и выставить `PKG_CONFIG_PATH`, `LDFLAGS`, `CPPFLAGS`.

---

## 📜 Лицензия

BSD-3-Clause (см. LICENSE, если приложено).

---

## 📫 Контакты

Вопросы/PR/обратная связь — создавайте issue или пишите в репозиторий проекта.
