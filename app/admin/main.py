from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database.database import get_async_db
from ..database.models import Organizer, Event, Registration, User
from datetime import datetime, timedelta
from typing import Optional
import hashlib

# Import your models here
# from your_models import User, Organizer, Event, Registration, Base

app = FastAPI(title="Event Admin Panel")



# Templates setup
templates = Jinja2Templates(directory="templates")

# Static files (for CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")



# Simple session management (in production, use proper session management)
class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, organizer_id: int) -> str:
        session_id = hashlib.md5(f"{organizer_id}{datetime.now()}".encode()).hexdigest()
        self.sessions[session_id] = organizer_id
        return session_id
    
    def get_organizer_id(self, session_id: str) -> Optional[int]:
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

session_manager = SessionManager()

# Dependency to get current organizer
def get_current_organizer(request: Request, db: AsyncSession = Depends(get_async_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    organizer_id = session_manager.get_organizer_id(session_id)
    if not organizer_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    
    # Replace with your actual query
    # organizer = db.query(Organizer).filter(Organizer.id == organizer_id).first()
    # if not organizer or not organizer.is_active:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organizer not found")
    
    # For now, return a mock organizer
    class MockOrganizer:
        def __init__(self):
            self.id = organizer_id
            self.name = "Admin User"
            self.is_superuser = True
    
    return MockOrganizer()

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_db)
):
    # In production, properly hash and verify password
    # organizer = db.query(Organizer).filter(Organizer.login == login).first()
    # if not organizer or not verify_password(password, organizer.password_hash):
    #     return templates.TemplateResponse("login.html", {
    #         "request": request, 
    #         "error": "Invalid credentials"
    #     })
    
    # Mock authentication - replace with real logic
    if login == "admin" and password == "password":
        session_id = session_manager.create_session(1)  # Mock organizer ID
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "Invalid credentials"
    })

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        session_manager.delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    organizer = Depends(get_current_organizer)
):
    # Replace with actual database queries
    query = select(Event).where(Event.organizer_id == organizer.id).options(
        selectinload(Event.registrations)
    )
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Calculate statistics in Python, not in template
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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
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
    
    res = await db.execute(select(Event).filter(Event.id == event_id, Event.organizer_id == organizer.id))
    
    event = res.first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    regs = await db.execute(select(Registration).join(User).filter(Registration.event_id == event_id))
    
    registrations = regs.all()
    
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
        "registrations": registrations
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

    event = res.first()
    
    
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
    
    return templates.TemplateResponse("edit_event.html", {
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
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # Update event - replace with actual database operation
        
        res = await db.execute(select(Event).filter(Event.id == event_id, Event.organizer_id == organizer.id))
    
        event = res.first()
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
    
    event = res.first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found") 
    db.delete(event)
    await db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)


    

