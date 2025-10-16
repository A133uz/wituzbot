env for admin panel:
```
secret_key=your_secret_key
algorithm=encryption_algorithm
access_token_expire_hours=24

admin_name=SuperAdmin
admin_login=admin
admin_email=admin@example.com
admin_pass=admin123
admin_is_superuser=True
admin_is_active=True 
```

env for bots:
```
#for main bot
tg_token=your_tg_token

#for feedback bot
tg_token=your_tg_token

admin_chat_id=your_chat_id
```

main env:
```
redis_url=redis://localhost:6379/0

db_host=localhost
db_port=5432
db_user=your-user
db_pass=your-password
db_name=your-name
```