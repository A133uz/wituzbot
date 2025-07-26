from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from pydantic import EmailStr
from enums import EventTypeEnum
from datetime import datetime

class UserBase(BaseModel):
    telegram_id: int
    name: str
    surname: str
    email: EmailStr
    org: str

class OrganizerBase(BaseModel):
    name: str
    login: str
    email: EmailStr

class EventBase(BaseModel):
    title: str
    desc: str
    type: EventTypeEnum
    date_time: datetime
    location: str

class RegistrationBase(BaseModel):
    user_id: int  # This will be telegram_id based on your FK
    event_id: int

# Create schemas (for input)
class UserCreate(UserBase):
    pass

class OrganizerCreate(OrganizerBase):
    password: str  # Include password for creation

class EventCreate(EventBase):
    pass

class RegistrationCreate(RegistrationBase):
    pass

# Update schemas (for partial updates)
class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[str] = None
    org: Optional[str] = None

class OrganizerUpdate(BaseModel):
    name: Optional[str] = None
    login: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None
    type: Optional[EventTypeEnum] = None
    date_time: Optional[datetime] = None
    location: Optional[str] = None

# Response schemas (for output) - exclude sensitive data
class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int

class OrganizerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    login: str
    email: str
    # Note: password excluded from response for security

class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    organizer_id: int

class RegistrationResponse(RegistrationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime

# Detailed response schemas with related data
class EventWithOrganizerResponse(EventResponse):
    organizer: OrganizerResponse

class RegistrationWithDetailsResponse(RegistrationResponse):
    user: UserResponse
    event: EventResponse

class UserWithRegistrationsResponse(UserResponse):
    registrations: List["RegistrationResponse"] = []

class EventWithRegistrationsResponse(EventResponse):
    registrations: List["RegistrationResponse"] = []    