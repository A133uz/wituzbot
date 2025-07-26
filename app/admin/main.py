import os, uuid
from fastapi import FastAPI
from fastadmin import SqlAlchemyModelAdmin, WidgetType, action, register
from fastadmin import fastapi_app as admin_app
from contextlib import asynccontextmanager

from ..database.models import User, Organizer, Event, Registration, async_main
from ..database.enums import EventTypeEnum
from ..database import requests as rqsts
from ..database.database import get_session
from ..database.config import settings

os.environ.setdefault(settings.admin_user_model, "Organizer")
os.environ.setdefault(settings.admin_user_model_username_field, "username")
os.environ.setdefault(settings.admin_secret, "your-secret-key-change-this-immediately")
os.environ.setdefault(settings.admin_site_name, "Event Management System")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await async_main()
    print("✅ Database tables created successfully!")
    yield
    # Shutdown (if you need cleanup logic)
    print("🔄 Application shutting down...")

def create_app() -> FastAPI:
    """Factory function to create FastAPI app with lifespan"""
    app = FastAPI(
        title="Event Management API",
        lifespan=lifespan
    )
    
    # Mount FastAdmin
    app.mount("/admin", admin_app)
    
    return app

# Create app instance
app = create_app()

@register(Organizer, sqlalchemy_sessionmaker=get_session())
class OrganizerAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "login", "email", "name", "is_superuser")
    list_display_links = ("id", "login", "name")
    list_filter = ("is_superuser", "is_active")
    search_fields = ("id", "name", "email")
    ordering = ("id")
    
    fields = ("password_hash", "login", "name", "email", "is_superuser", "is_active")
    
    formfield_overrides = {
        "login" : (WidgetType.SlugInput, {"required" : True}),
        "password_hash" : (WidgetType.PasswordInput, {"passwordModalForm" : True}),
        "is_superuser" : (WidgetType.Switch, {}),
        "is_active" : (WidgetType.Switch, {}),     
    }
    
    verbose_name = "Organizer"
    verbose_name_plural = "Organizers"
    
    async def authenticate(self, login: str, password: str) -> uuid.UUID | int | None:
        """Delegate authentication to service"""
        return await rqsts.authenticate(login, password)
    
    async def change_password(self, id: uuid.UUID | int, password: str) -> None:
        """Delegate password change to service"""
        await rqsts.change_pw(id, password)
    

@register(Event, sqlalchemy_sessionmaker=get_session())
class EventAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "title", "desc", "type", "date_time", "location", "organizer")
    list_display_links = ("id", "title")
    list_filter = ("type",)
    search_fields = ("title", "desc")
    
    fields = ("id", "title", "desc", "type", "date_time", "location", "organizer")
    
    formfield_overrides = {
        "title" : (WidgetType.Input, {"required" : True}),
        "desc" : (WidgetType.TextArea, {}),
        "type" : (WidgetType.Select, {
            "choices" : [
                (EventTypeEnum.in_person.value, "in_person"),
                (EventTypeEnum.online.value, "online")
            ],
            "required" : True
        }),
        "date_time" : (WidgetType.DateTimePicker, {"required" : True}),      
    }
    
    verbose_name = "Event"
    verbose_name_plural = "Events"
    
@register(User, sqlalchemy_sessionmaker=get_session())
class UserAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "telegram_id", "name", "surname", "org")
    list_display_links = ("id", "name")
    search_fields = ("id", "name", "surname")
    
    fields = ("id", "telegram_id", "name", "surname", "org")
    readonly_fields = ("telegram_id")
    
    formfield_overrides = {
        "telegram_id": (WidgetType.InputNumber, {"readonly": True})
    }
    
    verbose_name = "User"
    verbose_name_plural = "Users"
    
@register(Registration, sqlalchemy_sessionmaker=get_session())
class RegistrationAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "user", "event", "created_at")
    list_display_links = ("id",)
    
    list_filter = ("created_at", "event_id")
    
    fields = ("user_id", "event_id")
    readonly_fields = ("created_at",)
    
    formfield_overrides = {
        "user_id": (WidgetType.AsyncSelect, {"required": True}),
        "event_id": (WidgetType.AsyncSelect, {"required": True})
    }
    
    verbose_name = "Registration"
    verbose_name_plural = "Registrations"
    
    

