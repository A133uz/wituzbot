
import asyncio
from app.database import requests as rqsts



async def create_superuser():
    # Create admin using service
    admin = await rqsts.create_organizer(
        username="admin",
        email="admin@example.com",
        name="Adminchik",
        password="admin123",
        is_superuser=True
    )
    
    if admin:
        print("✅ Superuser created successfully!")
        print("👤 Username: admin")
        print("🔑 Password: admin123")
        print("⚠️ Please change the password after first login!")
    else:
        print("❌ Failed to create superuser!")

if __name__ == "__main__":
    asyncio.run(create_superuser())