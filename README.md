# WomenInTech Event Bot — Project Overview

A multi-service application for managing community events. It consists of a
**Telegram bot** that lets users browse and register for events, a **FastAPI
admin panel** that organizers use to create and manage those events, a
**feedback bot** for collecting bug reports, and a **Celery worker** that
sends 24-hour reminder notifications via Telegram.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  admin       │  │  main-bot    │  │  feedback-bot     │ │
│  │  FastAPI     │  │  aiogram     │  │  aiogram          │ │
│  │  :8000       │  │              │  │                   │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘ │
│         │                 │                   │             │
│  ┌──────▼─────────────────▼───────────────────▼──────────┐ │
│  │              app/database  (shared layer)              │ │
│  │         SQLAlchemy models, schemas, requests           │ │
│  └──────────────────────────┬─────────────────────────────┘ │
│                             │                               │
│  ┌──────────────┐  ┌────────▼───────┐  ┌───────────────┐  │
│  │  celery-     │  │   PostgreSQL   │  │     Redis     │  │
│  │  worker      │  │   :5432        │  │   :6379       │  │
│  └──────────────┘  └────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
.
├── app/
│   ├── admin/              # FastAPI admin panel service
│   ├── bot/                # Main Telegram bot service
│   ├── database/           # Shared DB layer (models, schemas, queries)
│   ├── feedback_bot/       # Separate Telegram feedback bot
│   ├── migrations/         # Alembic migration environment
│   └── utils/              # Shared utility helpers
├── templates/              # Jinja2 HTML templates for the admin panel
├── static/                 # Static assets (CSS, JS, images) for the admin panel
├── reminder_system.py      # Celery app + reminder task definitions
├── docker-compose.yml
├── Dockerfile.base         # Shared base image (all Python deps)
├── Dockerfile.admin        # Admin panel image
├── Dockerfile.mainbot      # Main bot image
├── Dockerfile.feedback_bot # Feedback bot image
├── entrypoint.sh           # Runs Alembic migrations before starting admin
├── alembic.ini             # Alembic configuration
└── requirements.txt        # Python dependencies
```

---

## Module-by-Module Breakdown

### `app/database/` — Shared Data Layer

This package is imported by every service. Keep changes here careful — a
broken model affects all three services at once.

| File | Purpose |
|---|---|
| `database.py` | Creates both async (`psycopg`) and sync SQLAlchemy engines, session factories, and the `Base` declarative class. Exposes `get_async_db`, `get_sync_db`, and context-manager helpers used across services. |
| `models.py` | SQLAlchemy ORM models: `User`, `Organizer`, `Event`, `Registration`. Also defines `async_main()` which calls `create_all` for non-migration bootstrapping. The `Event` model has a `local_datetime` property that converts stored UTC to Asia/Tashkent. |
| `schemas.py` | Pydantic v2 schemas for validation and serialization. Includes `UserCreate`, `EventCreate`, `OrganizerCreate`, `RegistrationCreate`, and their `Response`/`Update` variants. The `as_form()` decorator is applied at the bottom to make `EventCreate`, `EventUpdate`, `OrganizerCreate`, `OrganizerUpdate`, and `LoginRequest` usable as FastAPI `Form` dependencies. |
| `requests.py` | Async database query functions used by the bot: `set_user`, `get_user`, `get_events`, `get_event_by_id`, `get_users_events_from_db`, `set_registration`, `check_user_registration`, `remove_registration`. All wrap `get_session()` and return plain values rather than raw ORM objects where possible. |
| `enums.py` | `EventTypeEnum` — a `str` + `enum.Enum` with values `online` and `in_person`. Using `str` as a mixin means SQLAlchemy can store it directly as a string column without needing a Postgres `ENUM` type. |
| `config.py` | `DatabaseSettings` (pydantic-settings) reads `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME`, `REDIS_URL` from `/app/.env.database`. Exposes `DATABASE_URL_asyncpg` and `DATABASE_URL_syncpg` as properties. |

---

### `app/admin/` — FastAPI Admin Panel

Serves the web UI that organizers use to manage events and accounts. Runs
behind `entrypoint.sh` which applies Alembic migrations on startup.

| File | Purpose |
|---|---|
| `main.py` | The FastAPI application. Defines all HTTP routes: login/logout, dashboard, event CRUD, organizer CRUD (superuser only). Uses `SessionMiddleware` for flash messages and cookie-based JWT auth. Background tasks (`BackgroundTasks`) trigger Celery reminder scheduling without blocking the HTTP response. |
| `config.py` | `AdminSettings` reads JWT secrets, initial superuser credentials, CORS origins, and AWS S3 credentials from `/app/.env.admin`. |
| `utils.py` | `S3Service` — async upload and sync delete of event images to AWS S3. `get_password_hash` / `verify_password` — bcrypt wrappers. `create_access_token` / `verify_token` — PyJWT helpers. `flash_message` / `get_flash_messages` — Starlette session-backed flash message helpers. |
| `init_admin.py` | `create_initial_superuser()` — called during app lifespan startup. Checks if any superuser exists; if not, creates one from `AdminSettings`. Prevents duplicate superusers on container restarts. |

**Auth flow:** Login POST → verify bcrypt hash → issue JWT → set `httponly`
cookie → subsequent requests read cookie in `get_current_organizer` dependency
→ decode JWT → load `Organizer` from DB.

---

### `app/bot/` — Main Telegram Bot

Handles user-facing interactions: registration onboarding, event browsing,
and event sign-up/cancellation.

| File | Purpose |
|---|---|
| `main.py` | Entry point. Creates `Bot` and `Dispatcher`, registers the router, starts long-polling. |
| `handlers.py` | All aiogram message and callback handlers. `RegistrationState` FSM collects name, surname, phone, and organization in sequence. `EventRegistrationState` FSM handles optional email and custom questions per event. Callback handlers manage `register_`, `unregister_`, `already_registered`, and `skip_field` actions. |
| `keyboards.py` | Keyboard factory functions. `create_registration_button` checks registration status and returns either a "Register" button or a "Registered / Unregister" pair. `bot_registration_kb` shows a contact-share button during phone collection. |
| `validators.py` | Pure-function validators used in handler FSM steps: `validate_name_or_surname`, `validate_org`, `validate_email`, `validate_phone`. Phone validation uses `phonenumbers` library and normalizes to E.164 format. These are intentionally separate from Pydantic schemas so they can return human-readable Telegram error messages. |
| `config.py` | `MainBotSettings` — reads `TG_TOKEN` from `/app/.env.mainbot`. |
| `tests.py` | `pytest` parametrized tests for all four validators, covering valid and invalid inputs including Cyrillic names, international phone formats, edge cases like emojis, and injected characters. |

---

### `app/feedback_bot/` — Feedback Telegram Bot

A minimal separate bot that receives user messages (text, photo, video) and
forwards them to a configured admin Telegram chat. Runs as its own container
with its own token so it stays decoupled from the main bot.

| File | Purpose |
|---|---|
| `main.py` | Entry point. Same pattern as the main bot — `Dispatcher`, `Bot`, start polling. |
| `handlers.py` | Two handlers: `/start` welcome message, and a catch-all that forwards any text, photo, or video to `ADMIN_CHAT_ID`. |
| `config.py` | `FeedbackBotSettings` — reads `TG_TOKEN` and `ADMIN_CHAT_ID` from `/app/.env.feedback_bot`. |

---

### `app/migrations/` — Alembic Migration Environment

| File | Purpose |
|---|---|
| `env.py` | Alembic environment script. Imports all models so autogenerate can detect schema changes. Reads DB URL from `DatabaseSettings`. Runs synchronous migrations (not async) via `create_engine` — this is intentional since Alembic's async support requires extra ceremony. |
| `script.py.mako` | Mako template for generated migration files. Standard Alembic default. |
| `versions/` | Auto-generated migration scripts (gitignored). |

---

### `app/utils/` — Shared Utilities

| File | Purpose |
|---|---|
| `form_helpers.py` | `as_form(cls)` decorator. Patches a Pydantic `BaseModel` so FastAPI can inject it from HTML form data (via `Form(...)`) rather than a JSON body. Works by replacing the function signature with `inspect.Parameter` objects derived from the model's fields. Applied to `EventCreate`, `OrganizerCreate`, etc. at the bottom of `schemas.py`. |

---

### `reminder_system.py` — Celery Reminder Scheduler

Standalone Celery application. Imported by both the admin panel (to schedule
tasks) and the celery-worker container (to execute them). Uses Redis as both
broker and result backend.

| Function / Task | Purpose |
|---|---|
| `send_reminder_task` | Bound Celery task. Loads the event from DB, checks it hasn't already been reminded and is still in the future, then calls `send_telegram_reminder`. Retries up to 3 times with exponential backoff on failure. Marks `event.reminder_sent = True` on success. |
| `send_telegram_reminder` | Async function (called via `asyncio.run` inside the Celery task). Creates a `Bot` instance, formats a reminder message, and sends it to every registered user's Telegram chat. |
| `schedule_reminder` | Called after event creation. Computes `event_datetime - 24h` and schedules `send_reminder_task` with `apply_async(eta=...)`. Stores the Celery task ID on the event so it can be cancelled later. If the event is less than 24 hours away, no reminder is scheduled. |
| `update_event_and_reschedule` | Called after event edit if the datetime changed. Cancels the old task and calls `schedule_reminder` again. |
| `_cancel_reminder` | Revokes the Celery task by ID using `AsyncResult.revoke()`. Clears `celery_task_id` on the event. |

---

### `templates/` — Jinja2 HTML Templates

All templates extend `base.html` and use Bootstrap 5 + Font Awesome.

| Template | Purpose |
|---|---|
| `base.html` | Base layout. Loads Bootstrap CSS/JS, Font Awesome, and SheetJS (for Excel export). |
| `login.html` | Login form. POST to `/login`. |
| `dashboard.html` | Main admin view. Shows event list, registration counts, and (for superusers) organizer management table. |
| `create_event.html` | Event creation form with client-side validation. Supports image upload, optional registration question, and email requirement toggle. |
| `event_edit.html` | Event edit form. Pre-populates fields from the existing event object. Includes image removal checkbox. |
| `event_detail.html` | Event detail view with full registrations table. Includes CSV and Excel export (via SheetJS) implemented entirely in client-side JavaScript. |
| `create_admin.html` | Superuser-only form to create a new organizer. Includes real-time password strength indicator. |
| `edit_admin.html` | Superuser-only form to edit an existing organizer. Supports optional password change and account status toggle. |

---

### Docker & Infrastructure

| File | Purpose |
|---|---|
| `Dockerfile.base` | Two-stage build. Installs all Python dependencies in a builder stage, then copies only the installed packages into a slim runtime image. Also copies `app/bot`, `app/database`, `app/utils`, and `reminder_system.py` since these are needed by every service. |
| `Dockerfile.admin` | Extends the base image. Copies admin-specific files (`app/admin`, `templates`, migrations). Uses `entrypoint.sh` to run Alembic before starting uvicorn. |
| `Dockerfile.mainbot` | Extends the base image. Runs `app.bot.main` directly. |
| `Dockerfile.feedback_bot` | Extends the base image. Copies `app/feedback_bot` and runs it directly. |
| `entrypoint.sh` | Runs `alembic upgrade head` unless `SKIP_MIGRATIONS=true`. The celery-worker sets this env var so it doesn't try to run migrations on worker startup. |
| `docker-compose.yml` | Defines all six services: `postgres`, `redis`, `redis-commander`, `admin`, `main-bot`, `feedback-bot`, `celery-worker`. The worker reuses `Dockerfile.admin` but overrides `CMD` with the Celery worker command. |
| `alembic.ini` | Alembic config. Points `script_location` at `app/migrations`. The `sqlalchemy.url` placeholder is overridden at runtime by `env.py`. |

---

## Environment Variables

### Root `.env` (shared by all services)
```
REDIS_URL=redis://redis:6379/0
DB_HOST=postgres
DB_PORT=5432
DB_USER=your_user
DB_PASS=your_password
DB_NAME=your_db_name
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASS}
```

### `app/admin/.env`
```
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=24
ADMIN_NAME=SuperAdmin
ADMIN_LOGIN=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASS=YourPass123
ADMIN_IS_SUPERUSER=True
ADMIN_IS_ACTIVE=True
CORS_ALLOWED_ORIGINS=http://localhost:8008
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
AWS_REGION=eu-north-1
```

### `app/bot/.env`
```
TG_TOKEN=your_main_bot_token
```

### `app/feedback_bot/.env`
```
TG_TOKEN=your_feedback_bot_token
ADMIN_CHAT_ID=your_telegram_chat_id
```

---

## Running the Project

### First-time setup

```bash
# 1. Build the shared base image first — all other images depend on it
docker build -t wituzbot-base:latest -f Dockerfile.base .

# 2. Generate the initial migration (only needed once, or after model changes)
docker compose run --rm admin alembic revision --autogenerate -m "initial migration"

# 3. Start everything
docker compose up -d --build
```

### Running tests

```bash
# From the project root
pytest app/bot/tests.py -v
```

### Useful URLs (local)

| Service | URL |
|---|---|
| Admin panel | http://localhost:8008 |
| Redis Commander | http://localhost:8085 |
| PostgreSQL | localhost:5435 |

---

## Known Issues / Things to Watch

- **`edit_admin.html`** has a typo: `organier` (missing `z`) is used in some
  places and `organizer` in others. The statistics section will throw a
  Jinja2 `UndefinedError` at runtime.
- **`dashboard.html`** iterates `{% for organizer in organizer %}` — the
  iterable should be `organizers` (plural), which is the variable passed from
  the view.
- **`remove_registration`** in `requests.py` has no fallback `return` when
  `reg` is `None` (i.e. trying to unregister from an event you're not in).
  The function returns `None` implicitly, which the caller doesn't handle.
- **`send_telegram_reminder`** calls `asyncio.run()` inside a Celery task.
  This works with the `solo` pool but will break if you ever switch to
  `prefork` or `gevent` workers. Consider using `celery[gevent]` with an
  async-native approach or a dedicated async task runner.
- **`event.local_datetime`** in templates assumes Asia/Tashkent timezone
  hardcoded in the model. If the project is ever deployed for a different
  timezone, this needs to be made configurable.