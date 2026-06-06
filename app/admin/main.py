from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

import pytz
from starlette.middleware.sessions import SessionMiddleware

from .utils import *

import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent)) 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, Session

from database.database import get_async_db, get_sync_db, get_sync_session
from .config import AdminSettings
from database.models import Organizer, Event, EventReminder, Registration, async_main
from database.schemas import EventCreate, EventUpdate, OrganizerCreate, OrganizerUpdate, LoginRequest
from .init_admin import create_initial_superuser
from utils.description_helpers import serialize_description, deserialize_description
from utils.logging_config import configure_logging, get_logger
from utils.metrics import get_metrics, COUNTER_ADMIN_STARTS
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta


sys.path.append(str(Path(__file__).parent.parent.parent)) 
from reminder_system  import schedule_reminder, update_reminder, cancel_all_event_reminders
from typing import Optional
import logging
import uvicorn


# Configure centralized logging for admin service
configure_logging(service_name='admin')
logger = get_logger(__name__)
settings = AdminSettings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Admin panel starting...")
    get_metrics().increment(COUNTER_ADMIN_STARTS)
    
    await async_main()
    await create_initial_superuser()
    logger.info("✅ Admin panel ready")
    yield
    logger.info("👋 Admin panel shutting down...")

app = FastAPI(title="Event Admin Panel", lifespan=lifespan)



# Templates setup
templates = Jinja2Templates(directory="templates")

# Static files (for CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(CORSMiddleware, 
                   allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                )

security = HTTPBearer(auto_error=False)

s3_service = S3Service()

def schedule_reminder_bg(event_id: int, reminder_config: dict):
    """Background task to schedule reminder"""
    try:
        with get_sync_session() as sync_db:
            sync_event = sync_db.query(Event).filter(Event.id == event_id).first()
            if sync_event:
                existing_reminder = sync_db.query(EventReminder).filter(
                    EventReminder.event_id == event_id,
                    EventReminder.is_sent == False
                ).first()
                
                if existing_reminder:
                    logger.info(f"Found existing reminder {existing_reminder.id} for event {event_id}, updating...")
                    task_id = update_reminder(existing_reminder.id, reminder_config, sync_db)
                else:
                    task_id = schedule_reminder(sync_event, reminder_config, sync_db)
                
                if task_id:
                    logger.info(f"✅ Reminder scheduled for event {event_id}")
                else:
                    logger.info(f"ℹ️ No reminder needed for event {event_id}")
    except Exception as e:
        logger.error(f"Failed to schedule reminder for event {event_id}: {e}")

# Dependency to get current organizer
async def get_current_organizer(request: Request, db: Session = Depends(get_async_db),
                          creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Organizer:
    
    token = request.cookies.get("access_token")
    
    if not token and creds:
        token = creds.credentials
        
    if not token:
        raise HTTPException(  
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(  
            status_code=401,
            detail="Invalid or expired token"
        )
    
    organizer_id = int(payload.get("sub"))
    if not organizer_id:
        raise HTTPException(  
            status_code=401,
            detail="Invalid token payload"
        )
    
    result = await db.execute(
        select(Organizer).where(Organizer.id == organizer_id)
    )
    organizer = result.scalar_one_or_none()
    if not organizer or not organizer.is_active:
        raise HTTPException(  
            status_code=401,
            detail="Organizer not found"
        )
    return organizer
    
async def require_auth(organizer: Organizer = Depends(get_current_organizer)):
    if not organizer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return organizer

async def require_superuser(current_organizer: Organizer = Depends(require_auth)):
    """Dependency that requires superuser privileges"""
    if not current_organizer.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_organizer

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors gracefully"""
    error_messages = []
    for error in exc.errors():
        field = error['loc'][-1] if error['loc'] else 'unknown'
        error_messages.append(f"{field}: {error['msg']}")
    
    flash_message(request, f"Validation failed: {'; '.join(error_messages)}", "error")
    
    # Redirect back to the form
    referer = request.headers.get('referer', '/')
    return RedirectResponse(url=referer, status_code=302) 
    

@app.get("/health")
async def health_check():
    """Health check endpoint with metrics snapshot."""
    metrics = get_metrics().get_all()
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "summary": {
            "bot_starts": metrics.get("app:bot:starts:total", 0),
            "registrations_success": metrics.get("app:registrations:success:total", 0),
            "registrations_failed": metrics.get("app:registrations:failed:total", 0),
            "reminders_sent": metrics.get("app:reminders:sent:total", 0),
            "reminders_failed": metrics.get("app:reminders:failed:total", 0),
        }
    })

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    messages = get_flash_messages(request)
    return templates.TemplateResponse("login.html", 
                                      {"request": request,
                                       "msgs": messages})

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest = Depends(),
    db: Session = Depends(get_sync_db)
):
    if not credentials:
        flash_message(request, "Please fill in all fields.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    # Find organizer by login
    organizer = db.query(Organizer).filter(Organizer.login == credentials.login).first()
    
    if not organizer:
        flash_message(request, "Invalid username or password.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    if not organizer.is_active:
        flash_message(request, "Your account has been deactivated. Please contact an administrator.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    if not verify_password(credentials.password, organizer.password_hash):
        flash_message(request, "Invalid username or password.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    # Create access token
    access_token_expires = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS if credentials.remember else 1)
    access_token = create_access_token(
        data={"sub": str(organizer.id)}, expires_delta=access_token_expires
    )
    
    # Set cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=int(access_token_expires.total_seconds()) if credentials.remember else None
    )
    
    flash_message(request, f"Welcome back, {organizer.name}!", "success")
    return response


@app.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    flash_message(request, "You have been logged out successfully.", "success")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_organizer = Depends(get_current_organizer)
):
    
    query = select(Event).options(
        selectinload(Event.registrations)
    )
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    
    now = datetime.now()
    total_events = len(events)
    upcoming_events = [e for e in events if e.date_time > now]
    upcoming_events_count = len(upcoming_events)
    
    # Calculate total registrations
    total_registrations = sum(len(event.registrations) for event in events)
    
    # Calculate recent registrations (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_registrations = 0
    for event in events:
        for reg in event.registrations:
            if reg.created_at and reg.created_at > thirty_days_ago:
                recent_registrations += 1
                
    if current_organizer.is_superuser:
        res = await db.execute(select(Organizer))
        organizers = res.scalars().all()
        total_organizers = len(organizers)
    
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "current_organizer" : current_organizer,
            "organizers": organizers,
            "events": events,
            "total_events": total_events,
            "upcoming_events_count": upcoming_events_count,
            "total_registrations": total_registrations,
            "total_organizers": total_organizers,
            "recent_registrations": recent_registrations,
            "now": now,
            "form_data" : {}
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_organizer" : current_organizer,
        "events": events,
        "total_events": total_events,
        "upcoming_events_count": upcoming_events_count,
        "total_registrations": total_registrations,
        "recent_registrations": recent_registrations,
        "now": now,
        "form_data" : {}
    })

@app.get("/events/create", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    organizer = Depends(get_current_organizer)
):
    return templates.TemplateResponse("create_event.html", {
        "request": request,
        "organizer": organizer
    })

@app.post("/events/create")
async def create_event(
    request: Request,
    bg_task: BackgroundTasks,
    event_data: EventCreate = Depends(),
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer),
    image: UploadFile = File(None)
):
    try:
        event_datetime = datetime.strptime(f"{event_data.date} {event_data.time}", "%Y-%m-%d %H:%M")
        logger.info(f"📝 Parsed input: {event_datetime}")

        tashkent_tz = pytz.timezone('Asia/Tashkent')
        event_datetime_tashkent = tashkent_tz.localize(event_datetime)
        logger.info(f"🌍 Tashkent time: {event_datetime_tashkent}")

        event_datetime_utc = event_datetime_tashkent.astimezone(timezone.utc)
        logger.info(f"🌐 UTC time: {event_datetime_utc}")

        utc_naive = event_datetime_utc.replace(tzinfo=None)
        logger.info(f"💾 Storing as naive UTC: {utc_naive}")
        
        image_url = None
        if image and image.filename:
            image_url = await s3_service.upload_image(image)

        new_event = Event(
            title=event_data.title,
            desc=serialize_description(event_data.desc_en, event_data.desc_ru, event_data.desc_uz),
            type=event_data.type,
            date_time=utc_naive,
            location=event_data.location,
            image_url=image_url,
            registration_question=event_data.registration_question,
            requires_email=event_data.requires_email,
            organizer_id=organizer.id
        )

        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)

        logger.info(f"✅ Event saved with date_time: {new_event.date_time}")
        
        reminder_config = {
            'hours_before': event_data.reminder_hours_before,
            'message': event_data.reminder_message
        }
        
        bg_task.add_task(schedule_reminder_bg, new_event.id, reminder_config)
    
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        form = await request.form()
        form_dict = dict(form)
        logger.error(f"Create event error: {e}")
        return templates.TemplateResponse("create_event.html", {
            "request": request,
            "organizer": organizer,
            "error": str(e),
            "form_data" : form_dict
        })

@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    
    
    res = await db.execute(select(Event)
                           .filter(Event.id == event_id)
                           .options(
                               selectinload(Event.registrations).selectinload(Registration.user)
                           ))
    
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Deserialize description JSON for display
    event_descs = deserialize_description(event.desc)
    
    return templates.TemplateResponse("event_detail.html", {
        "request": request,
        "organizer": organizer,
        "event": event,
        "event_descs": event_descs,
        "registrations": event.registrations,
        "form_data" : {}
    })

@app.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    # Replace with actual database query
    
    res = await db.execute(select(Event).options(selectinload(Event.reminders)).filter(Event.id == event_id))

    event = res.scalar_one_or_none()
    
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Deserialize the description JSON for display in the form
    event_descs = deserialize_description(event.desc)
    
    return templates.TemplateResponse("event_edit.html", {
        "request": request,
        "organizer": organizer,
        "event": event,
        "event_descs": event_descs,
        "form_data": {}
    })

@app.post("/events/{event_id}/edit")
async def edit_event(
    request: Request,
    event_id: int,
    bg_task: BackgroundTasks,
    event_data: EventUpdate = Depends(),
    db: AsyncSession = Depends(get_async_db),
    image: UploadFile = File(None),
    remove_image: bool = Form(False),
    organizer = Depends(get_current_organizer)
):
    try:
        # Parse input
        event_datetime_naive = datetime.strptime(f"{event_data.date} {event_data.time}", "%Y-%m-%d %H:%M")

        # Convert Tashkent → UTC (same as create endpoint)
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        event_datetime_tashkent = tashkent_tz.localize(event_datetime_naive)
        event_datetime_utc = event_datetime_tashkent.astimezone(timezone.utc)
        utc_naive = event_datetime_utc.replace(tzinfo=None)

        logger.info(f"Editing event {event_id}: {event_datetime_tashkent} → {utc_naive} UTC")

        # Get event
        res = await db.execute(select(Event).filter(Event.id == event_id))
        event = res.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # datetime_changed = event.date_time != utc_naive

        event.title = event_data.title
        event.desc = serialize_description(event_data.desc_en, event_data.desc_ru, event_data.desc_uz)
        event.type = event_data.type 
        event.date_time = utc_naive  
        event.location = event_data.location
        event.registration_question = event_data.registration_question
        event.requires_email = event_data.requires_email
        old_image_url = event.image_url

        if remove_image and old_image_url:
            s3_service.delete_image(old_image_url)
            event.image_url = None
        elif image and image.filename:
            if old_image_url:
                s3_service.delete_image(old_image_url)
            event.image_url = await s3_service.upload_image(image)

        await db.commit()
        await db.refresh(event)

        if event_data.reminder_hours_before or event_data.reminder_message is not None:
            reminder_config = {}
            if event_data.reminder_hours_before:
                reminder_config['hours_before'] = event_data.reminder_hours_before
            if event_data.reminder_message is not None:
                reminder_config['message'] = event_data.reminder_message

            bg_task.add_task(schedule_reminder_bg, event_id, reminder_config)

        return RedirectResponse(url=f"/events/{event_id}", status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        logger.error(f"Update event error: {e}", exc_info=True)
        raise
        # return RedirectResponse(url=f"/events/{event_id}/edit", status_code=status.HTTP_302_FOUND)

@app.post("/events/{event_id}/delete")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    
    # Delete event - replace with actual database operation
    res = await db.execute(select(Event).filter(Event.id == event_id))
    
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    def cancel_reminders_bg():
        try:
            cancel_all_event_reminders(event_id, get_sync_session())
        except Exception as e:
            logger.error(f"Failed to cancel reminders for event {event_id}: {e}")
            
    cancel_reminders_bg()
        
    s3_service.delete_image(event.image_url)
        
    await db.delete(event)
    await db.commit()
    
    logger.info(f"✅ Event {event_id} deleted")
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)


@app.get("/organizers/create", response_class=HTMLResponse)
async def create_organizer_form(request: Request, organizer = Depends(require_superuser)):
    return templates.TemplateResponse("create_admin.html", {
        "request": request,
        "organizer": organizer,
        "form_data": {}
    })

@app.post("/organizers/create")
async def create_organizer(
    request: Request,
    organizer_data: OrganizerCreate = Depends(),
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    res_org = await db.execute(
        select(Organizer).filter(Organizer.login == organizer_data.login)
    )
    if res_org.first():
        flash_message(request, "Username already exists.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    # Check if email exists
    res_email = await db.execute(
        select(Organizer).filter(Organizer.email == organizer_data.email)
    )
    if res_email.first():
        flash_message(request, "Email already exists.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    # Create organizer
    new_organizer = Organizer(
        name=organizer_data.name,
        login=organizer_data.login,
        email=organizer_data.email,
        password_hash=get_password_hash(organizer_data.password),
        is_superuser=organizer_data.is_superuser,
        is_active=True
    )
    
    try:
        db.add(new_organizer)
        await db.commit()
        flash_message(request, f"Admin '{organizer_data.name}' created successfully!", "success")
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating organizer: {e}")
        flash_message(request, "Failed to create admin.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)

@app.get("/organizers/{admin_id}/edit", response_class=HTMLResponse)
async def edit_admin_page(
    organizer_id: int,
    request: Request,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    res = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = res.first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    messages = get_flash_messages(request)
    return templates.TemplateResponse("edit_admin.html", {
        "request": request,
        "organizer": organizer,
        "messages": messages, 
        "form_data": {}
    })

@app.post("/organizers/{admin_id}/edit")
async def edit_admin(
    organizer_id: int,
    request: Request,
    organizer_data: OrganizerUpdate = Depends(),
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    res = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = res.scalar_one_or_none()
    
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Check if login exists (excluding current)
    res_exists = await db.execute(
        select(Organizer).filter(
            Organizer.login == organizer_data.login,
            Organizer.id != organizer_id
        )
    )
    if res_exists.first():
        flash_message(request, "Username already exists.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Check if email exists (excluding current)
    exist_email_query = await db.execute(
        select(Organizer).filter(
            Organizer.email == organizer_data.email,
            Organizer.id != organizer_id
        )
    )
    if exist_email_query.first():
        flash_message(request, "Email already exists.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Update organizer
    organizer.name = organizer_data.name
    organizer.login = organizer_data.login
    organizer.email = organizer_data.email
    organizer.is_active = organizer_data.is_active
    organizer.is_superuser = organizer_data.is_superuser
    
    if organizer_data.changePassword:
        organizer.password_hash = get_password_hash(organizer_data.password)
    
    try:
        await db.commit()
        flash_message(request, f"Admin '{organizer_data.name}' updated successfully!", "success")
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating organizer: {e}")
        flash_message(request, "Failed to update admin.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)

@app.post("/organizers/{organizer_id}/activate")
async def activate_admin(
    organizer_id: int,
    request: Request,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    query = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = query.first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if organizer.id == current_organizer.id:
        flash_message(request, "You cannot modify your own account status.", "error")
        return RedirectResponse(url="/dashboard", status_code=302)
    
    organizer.is_active = True
    
    try:
        await db.commit()
        flash_message(request, f'Admin "{organizer.name}" has been activated.', "success")
    except Exception as e:
        await db.rollback()
        flash_message(request, "An error occurred while activating the admin.", "error")
    
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/organizers/{organizer_id}/deactivate")
async def deactivate_admin(
    organizer_id: int,
    request: Request,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    query = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = query.first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if organizer.id == current_organizer.id:
        flash_message(request, "You cannot deactivate yourself.", "error")
        return RedirectResponse(url="/dashboard", status_code=302)
    
    organizer.is_active = False
    
    try:
        await db.commit()
        flash_message(request, f'Admin "{organizer.name}" has been deactivated.', "success")
    except Exception as e:
        await db.rollback()
        flash_message(request, "An error occurred while deactivating the admin.", "error")
    
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/organizers/{organizer_id}/delete")
async def delete_admin(
    organizer_id: int,
    request: Request,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    query = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = query.first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if organizer.id == current_organizer.id:
        flash_message(request, "You cannot delete yourself.", "error")
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Check if admin has events
    if organizer.events:
        flash_message(request, f'Cannot delete admin "{organizer.name}" because they have created events. Please transfer or delete their events first.', "error")
        return RedirectResponse(url="/dashboard", status_code=302)
    
    try:
        organizer_name = organizer.name
        await db.delete(organizer)
        await db.commit()
        flash_message(request, f'Admin "{organizer_name}" has been deleted.', "success")
    except Exception as e:
        await db.rollback()
        flash_message(request, "An error occurred while deleting the admin.", "error")
    
    return RedirectResponse(url="/dashboard", status_code=302)
        
    


# async def main():
#     await async_main()
#     await create_initial_superuser()
#     config = uvicorn.Config("app.admin.main:app", host="0.0.0.0", port=8000, reload=True)
#     server = uvicorn.Server(config)
#     await server.serve()
    
if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run("app.admin.main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("Admin panel has been stopped")

