## For Docker:
```
docker compose run --rm admin alembic revision --autogenerate -m "initial migration"
docker compose up -d --build
docker compose restart
```

## env for admin panel:
```
SECRET_KEY=your_secret_key
ALGORITHM=encryption_algorithm
ACCESS_TOKEN_EXPIRE_HOURS=24

ADMIN_NAME=SuperAdmin
ADMIN_LOGIN=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASS=admin123
ADMIN_IS_SUPERUSER=True
ADMIN_IS_ACTIVE=True 

CORS_ALLOWED_ORIGINS=your_origins
```

## env for bots:
```
#for main bot
TG_TOKEN=your_tg_token

#for feedback bot
TG_TOKEN=your_tg_token

ADMIN_CHAT_ID=your_chat_id
```

## main env:
```
REDIS_URL=redis://redis:6379/0 #for docker. if running locally, instead of redis -> localhost

DB_HOST=localhost
DB_PORT=5432
DB_USER=your-user
DB_PASS=your-password
DB_NAME=your-name

POSTGRES_DB=${DB_NAME}         
POSTGRES_USER=${DB_USER}       
POSTGRES_PASSWORD=${DB_PASS} 
```