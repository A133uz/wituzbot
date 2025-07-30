from fastapi import FastAPI, Request, Depends, HTTPException, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, Session

from ..database.database import get_async_db, get_sync_db
from ..database.config import settings
from ..database.models import Organizer, Event, Registration

from datetime import datetime, timedelta
from typing import Optional, Annotated

from .utils import *



app = FastAPI(title="Event Admin Panel")



# Templates setup
templates = Jinja2Templates(directory="templates")

# Static files (for CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

security = HTTPBearer(auto_error=False)




# Dependency to get current organizer
def get_current_organizer(request: Request, db: Session = Depends(get_sync_db),
                          creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Organizer]:
    
    token = request.cookies.get("access_token")
    
    if not token and creds:
        token = creds.credentials
        
    if not token:
        return
    
    payload = verify_token(token)
    if not payload:
        return
    
    organizer_id = payload.get("sub")
    if not organizer_id:
        return
    
    organizer = db.query(Organizer).filter(Organizer.id == organizer_id).first()
    if not organizer or not organizer.is_active:
        return
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
    login: Annotated[str, Form()],
    password: Annotated[str, Form()],
    remember: Annotated[bool, Form()] = False,
    db: Session = Depends(get_sync_db)
):
    if not login or not password:
        flash_message(request, "Please fill in all fields.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    # Find organizer by login
    organizer = db.query(Organizer).filter(Organizer.login == login).first()
    
    if not organizer:
        flash_message(request, "Invalid username or password.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    if not organizer.is_active:
        flash_message(request, "Your account has been deactivated. Please contact an administrator.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    if not verify_password(password, organizer.password_hash):
        flash_message(request, "Invalid username or password.", "error")
        return RedirectResponse(url="/login", status_code=302)
    
    # Create access token
    access_token_expires = timedelta(hours=settings.access_token_expire_hours if remember else 1)
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
        max_age=int(access_token_expires.total_seconds()) if remember else None
    )
    
    flash_message(request, f"Welcome back, {organizer.name}!", "success")
    return response


@app.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    flash_message(request, "You have been logged out successfully.", "success")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_organizer = Depends(get_current_organizer)
):
    # Replace with actual database queries
    query = select(Event).where(Event.organizer_id == current_organizer.id).options(
        selectinload(Event.registrations)
    )
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Calculate statistics in Python, not in template
    now = datetime.datetime.now()
    total_events = len(events)
    upcoming_events = [e for e in events if e.date_time > now]
    upcoming_events_count = len(upcoming_events)
    
    # Calculate total registrations
    total_registrations = sum(len(event.registrations) for event in events)
    
    # Calculate recent registrations (last 30 days)
    thirty_days_ago = datetime.datetime.now() - timedelta(days=30)
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
            "now": now
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_organizer" : current_organizer,
        "events": events,
        "total_events": total_events,
        "upcoming_events_count": upcoming_events_count,
        "total_registrations": total_registrations,
        "recent_registrations": recent_registrations,
        "now": now
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
    title: str = Form(...),
    desc: str = Form(...),
    event_type: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    location: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    try:
        # Combine date and time
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # Create new event - replace with actual database operation
        new_event = Event(
            title=title,
            desc=desc,
            type=event_type,
            date_time=event_datetime,
            location=location,
            organizer_id=organizer.id
        )
        
        db.add(new_event)
        await db.commit()
    
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    except ValueError:
        return templates.TemplateResponse("create_event.html", {
            "request": request,
            "organizer": organizer,
            "error": "Invalid date/time format"
        })

@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    # Replace with actual database queries
    
    res = await db.execute(select(Event)
                           .filter(Event.id == event_id, Event.organizer_id == organizer.id)
                           .options(
                               selectinload(Event.registrations).selectinload(Registration.user)
                           ))
    
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    
    # Mock data - replace with real queries
    #event = {
    #    "id": event_id,
    #    "title": "Tech Conference 2025",
    #    "desc": "A comprehensive tech conference covering latest trends",
    #    "date_time": datetime(2025, 8, 15, 10, 0),
    #    "location": "Tech Center",
    #    "type": "conference"
    #}
    #
    #registrations = [
    #    {
    #        "id": 1,
    #        "user": {
    #            "name": "John",
    #            "surname": "Doe",
    #            "email": "john@example.com",
    #            "org": "Tech Corp"
    #        },
    #        "created_at": datetime(2025, 7, 20, 15, 30)
    #    },
    #    {
    #        "id": 2,
    #        "user": {
    #            "name": "Jane",
    #            "surname": "Smith",
    #            "email": "jane@example.com",
    #            "org": "Innovation Ltd"
    #        },
    #        "created_at": datetime(2025, 7, 21, 9, 15)
    #    }
    #]
    
    return templates.TemplateResponse("event_detail.html", {
        "request": request,
        "organizer": organizer,
        "event": event,
        "registrations": event.registrations
    })

@app.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    # Replace with actual database query
    
    res = await db.execute(select(Event).filter(Event.id == event_id, Event.organizer_id == organizer.id))

    event = res.scalar_one_or_none()
    
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Mock data
    # event = {
    #     "id": event_id,
    #     "title": "Tech Conference 2025",
    #     "desc": "A comprehensive tech conference covering latest trends",
    #     "date_time": datetime(2025, 8, 15, 10, 0),
    #     "location": "Tech Center",
    #     "type": "conference"
    # }
    
    return templates.TemplateResponse("event_edit.html", {
        "request": request,
        "organizer": organizer,
        "event": event
    })

@app.post("/events/{event_id}/edit")
async def edit_event(
    request: Request,
    event_id: int,
    title: str = Form(...),
    desc: str = Form(...),
    event_type: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    location: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    try:
        event_datetime = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # Update event - replace with actual database operation
        
        res = await db.execute(select(Event).filter(Event.id == event_id, Event.organizer_id == organizer.id))
    
        event = res.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event.title = title
        event.desc = desc
        event.type = event_type
        event.date_time = event_datetime
        event.location = location
        await db.commit()
        
        return RedirectResponse(url=f"/events/{event_id}", status_code=status.HTTP_302_FOUND)
    
    except ValueError:
        # Handle error - you might want to reload the form with error message
        return RedirectResponse(url=f"/events/{event_id}/edit", status_code=status.HTTP_302_FOUND)

@app.post("/events/{event_id}/delete")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    
    # Delete event - replace with actual database operation
    res = await db.execute(select(Event).filter(Event.id == event_id, Event.organizer_id == organizer.id))
    
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found") 
    await db.delete(event)
    await db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)


@app.get("/organizers/create", response_class=HTMLResponse)
async def create_organizer_form(request: Request, organizer = Depends(require_superuser)):
    return templates.TemplateResponse("create_admin.html", {
        "request": request,
        "organizer": organizer
    })

@app.post("/organizers/create")
async def create_organizer(
    request: Request,
    name: Annotated[str, Form()],
    login: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirmPassword: Annotated[str, Form()],
    is_superuser: Annotated[bool, Form()] = False,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    # Validation
    if not all([name, login, email, password, confirmPassword]):
        flash_message(request, "Please fill in all required fields.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    if password != confirmPassword:
        flash_message(request, "Passwords do not match.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    if len(password) < 8:
        flash_message(request, "Password must be at least 8 characters long.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    # Check if login already exists
    res_org = await db.execute(select(Organizer).filter(Organizer.login == login))
    existing_organizer = res_org.first()
    if existing_organizer:
        flash_message(request, "Username already exists. Please choose a different one.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    # Check if email already exists
    res_email = await db.execute(select(Organizer).filter(Organizer.email == email))
    existing_email = res_email.first()
    if existing_email:
        flash_message(request, "Email already exists. Please use a different email.", "error")
        return RedirectResponse(url="/organizers/create", status_code=302)
    
    # Create new admin
    password_hash = get_password_hash(password)
    new_admin = Organizer(
        name=name,
        login=login,
        email=email,
        password_hash=password_hash,
        is_superuser=is_superuser,
        is_active=True
    )
    
    try:
        db.add(new_admin)
        await db.commit()
        flash_message(request, f'Admin "{name}" created successfully!', "success")
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        db.rollback()
        flash_message(request, "An error occurred while creating the admin. Please try again.", "error")
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
        "messages": messages
    })

@app.post("/organizers/{admin_id}/edit")
async def edit_admin(
    organizer_id: int,
    request: Request,
    name: Annotated[str, Form()],
    login: Annotated[str, Form()],
    email: Annotated[str, Form()],
    changePassword: Annotated[bool, Form()] = False,
    password: Annotated[str, Form()] = "",
    confirmPassword: Annotated[str, Form()] = "",
    is_active: Annotated[bool, Form()] = False,
    is_superuser: Annotated[bool, Form()] = False,
    current_organizer: Organizer = Depends(require_superuser),
    db: AsyncSession = Depends(get_async_db)
):
    res = await db.execute(select(Organizer).filter(Organizer.id == organizer_id))
    organizer = res.first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Validation
    if not all([name, login, email]):
        flash_message(request, "Please fill in all required fields.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Check if login already exists (excluding current admin)
    res_exists = await db.execute(select(Organizer).filter(
        Organizer.login == login,
        Organizer.id != organizer_id
    ))
    existing_organizer = res_exists.first()
    if existing_organizer:
        flash_message(request, "Username already exists. Please choose a different one.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Check if email already exists (excluding current admin)
    exist_email_query = await db.execute(select(Organizer).filter(
        Organizer.email == email,
        Organizer.id != organizer_id
    ))
    existing_email = exist_email_query.first()
    if existing_email:
        flash_message(request, "Email already exists. Please use a different email.", "error")
        return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Password validation if changing password
    if changePassword:
        if not password or not confirmPassword:
            flash_message(request, "Please provide both password fields.", "error")
            return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
        
        if password != confirmPassword:
            flash_message(request, "Passwords do not match.", "error")
            return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
        
        if len(password) < 8:
            flash_message(request, "Password must be at least 8 characters long.", "error")
            return RedirectResponse(url=f"/organizers/{organizer_id}/edit", status_code=302)
    
    # Update admin
    organizer.name = name
    organizer.login = login
    organizer.email = email
    organizer.is_active = is_active
    organizer.is_superuser = is_superuser
    
    if changePassword:
        organizer.password_hash = get_password_hash(password)
    
    try:
        await db.commit()
        flash_message(request, f'Admin "{name}" updated successfully!', "success")
        return RedirectResponse(url="/dashboard", status_code=302)
    except Exception as e:
        db.rollback()
        flash_message(request, "An error occurred while updating the admin. Please try again.", "error")
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
        
    


    

