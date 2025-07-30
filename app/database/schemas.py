from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Annotated
from pydantic import EmailStr
from enums import EventTypeEnum
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    login: str
    password: str

class OrganizerCreate(BaseModel):
    name: str
    login: str
    password: str
    email: EmailStr

class OrganizerResponse(OrganizerCreate):
    password: Annotated[str, Field(exclude=True)]
    id: int
    is_superuser: bool
    is_active: bool

class EventCreate(BaseModel):
    title: str
    desc: str
    type: str | EventTypeEnum # EventTypeEnum
    date_time: datetime
    location: str

class EventUpdate(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None
    type: Optional[str] = None
    date_time: Optional[datetime] = None
    location: Optional[str] = None

class EventResponse(EventCreate):
    id: int
    organizer_id: int   