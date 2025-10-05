from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from .enums import EventTypeEnum
from utils.form_helpers import as_form
import re

#User Schemas

class UserBase(BaseModel):
    """Base user schema with common fields"""
    name: str = Field(..., min_length=1, max_length=25, description="User's first name")
    surname: str = Field(..., min_length=1, max_length=25, description="User's surname")
    email: EmailStr = Field(..., max_length=100, description="User's email address")
    org: str = Field(..., min_length=1, max_length=100, description="User's organization/workplace")

    @field_validator('name', 'surname', 'org')
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Strip whitespace and validate not empty"""
        if not v or not v.strip():
            raise ValueError('This field cannot be empty or contain only spaces')
        stripped = v.strip()
        if len(stripped) < 1:
            raise ValueError('This field must contain at least 1 character')
        return stripped

    @field_validator('name', 'surname')
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate name contains only letters and common characters"""
        v = v.strip()
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, apostrophes, and periods')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user (bot registration)"""
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")

    @field_validator('telegram_id')
    @classmethod
    def validate_telegram_id(cls, v: int) -> int:
        """Validate telegram_id is within reasonable bounds"""
        if v <= 0:
            raise ValueError('Telegram ID must be positive')
        if v > 9999999999:  # Max reasonable Telegram ID
            raise ValueError('Invalid Telegram ID')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    name: Optional[str] = Field(None, min_length=1, max_length=25)
    surname: Optional[str] = Field(None, min_length=1, max_length=25)
    email: Optional[EmailStr] = Field(None, max_length=100)
    org: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator('name', 'surname', 'org')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace if value provided"""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError('Field cannot be empty if provided')
            return stripped
        return v


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    telegram_id: int

    model_config = {"from_attributes": True}


class UserWithRegistrations(UserResponse):
    """Schema for user with their event registrations"""
    registrations: List["RegistrationResponse"] = []

    model_config = {"from_attributes": True}
    
# Organizer Schemas

class OrganizerBase(BaseModel):
    """Base organizer schema"""
    name: str = Field(..., min_length=1, max_length=25, description="Organizer's name")
    login: str = Field(..., min_length=3, max_length=50, description="Username for login")
    email: EmailStr = Field(..., max_length=100, description="Organizer's email")

    @field_validator('name', 'login')
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Strip whitespace and validate not empty"""
        if not v or not v.strip():
            raise ValueError('This field cannot be empty')
        return v.strip()

    @field_validator('login')
    @classmethod
    def validate_login_format(cls, v: str) -> str:
        """Ensure login contains only valid characters"""
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Login can only contain letters, numbers, underscores, and hyphens')
        if v[0].isdigit():
            raise ValueError('Login cannot start with a number')
        return v.lower()  # Normalize to lowercase


class OrganizerCreate(OrganizerBase):
    """Schema for creating a new organizer"""
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")
    confirmPassword: str = Field(..., description="Password confirmation")
    is_superuser: bool = Field(default=False, description="Grant superuser privileges")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure password and confirmPassword match"""
        if self.password != self.confirmPassword:
            raise ValueError('Passwords do not match')
        return self


class OrganizerUpdate(OrganizerBase):
    """Schema for updating an organizer"""
    changePassword: bool = Field(default=False, description="Change password flag")
    password: Optional[str] = Field(None, min_length=8, max_length=128, description="New password")
    confirmPassword: Optional[str] = Field(None, description="Confirm new password")
    is_active: bool = Field(default=True, description="Account active status")
    is_superuser: bool = Field(default=False, description="Superuser privileges")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength if provided"""
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not re.search(r'[a-z]', v):
                raise ValueError('Password must contain at least one lowercase letter')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Password must contain at least one uppercase letter')
            if not re.search(r'\d', v):
                raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def validate_password_change(self):
        """Validate password fields when changing password"""
        if self.changePassword:
            if not self.password or not self.confirmPassword:
                raise ValueError('Both password fields are required when changing password')
            if self.password != self.confirmPassword:
                raise ValueError('Passwords do not match')
        return self


class OrganizerResponse(OrganizerBase):
    """Schema for organizer response (no password)"""
    id: int
    is_superuser: bool
    is_active: bool

    model_config = {"from_attributes": True}


class OrganizerWithEvents(OrganizerResponse):
    """Schema for organizer with their events"""
    events: List["EventResponse"] = []

    model_config = {"from_attributes": True}
    
# Event Schemas

class EventBase(BaseModel):
    """Base event schema with common fields"""
    title: str = Field(..., min_length=3, max_length=100, description="Event title")
    desc: str = Field(..., min_length=10, description="Event description")
    type: EventTypeEnum = Field(..., description="Event type/category")
    location: str = Field(..., min_length=3, max_length=100, description="Event location")

    @field_validator('title', 'desc', 'location')
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Strip whitespace and ensure not empty"""
        if not v or not v.strip():
            raise ValueError('This field cannot be empty')
        return v.strip()


class EventCreate(EventBase):
    """Schema for creating an event via admin panel (form data)"""
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Event date (YYYY-MM-DD)")
    time: str = Field(..., pattern=r'^\d{2}:\d{2}$', description="Event time (HH:MM in 24-hour format)")

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format and ensure it's not in the past"""
        try:
            event_date = datetime.strptime(v, '%Y-%m-%d').date()
            if event_date < datetime.now().date():
                raise ValueError('Event date cannot be in the past')
            return v
        except ValueError as e:
            if 'does not match format' in str(e):
                raise ValueError('Date must be in YYYY-MM-DD format')
            raise

    @field_validator('time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate time format"""
        try:
            time_obj = datetime.strptime(v, '%H:%M').time()
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24-hour clock)')


class EventUpdate(EventBase):
    """Schema for updating an event"""
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    time: str = Field(..., pattern=r'^\d{2}:\d{2}$')

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format"""
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format')


class EventResponse(EventBase):
    """Schema for event response"""
    id: int
    date_time: datetime
    organizer_id: int
    celery_task_id: Optional[str] = None
    reminder_sent: bool = False

    model_config = {"from_attributes": True}


class EventWithRegistrations(EventResponse):
    """Schema for event with all registrations"""
    registrations: List["RegistrationWithUser"] = []

    model_config = {"from_attributes": True}


class EventWithOrganizer(EventResponse):
    """Schema for event with organizer details"""
    organizer: OrganizerResponse

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """Schema for event list (bot usage)"""
    id: int
    title: str
    date_time: datetime
    location: str
    type: str
    registrations_count: int = 0

    model_config = {"from_attributes": True}
    
# Registration Schemas

class RegistrationBase(BaseModel):
    """Base registration schema"""
    user_id: int = Field(..., gt=0, description="User's Telegram ID")
    event_id: int = Field(..., gt=0, description="Event ID")


class RegistrationCreate(RegistrationBase):
    """Schema for creating a registration"""
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Registration timestamp")

    @field_validator('user_id', 'event_id')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Ensure IDs are positive"""
        if v <= 0:
            raise ValueError('ID must be positive')
        return v


class RegistrationResponse(RegistrationBase):
    """Schema for registration response"""
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RegistrationWithUser(RegistrationResponse):
    """Schema for registration with user details"""
    user: UserResponse

    model_config = {"from_attributes": True}


class RegistrationWithEvent(RegistrationResponse):
    """Schema for registration with event details"""
    event: EventResponse

    model_config = {"from_attributes": True}


class RegistrationWithDetails(RegistrationResponse):
    """Schema for registration with full user and event details"""
    user: UserResponse
    event: EventResponse

    model_config = {"from_attributes": True}


class RegistrationCheckRequest(BaseModel):
    """Schema for checking if user is registered for event"""
    user_id: int = Field(..., gt=0)
    event_id: int = Field(..., gt=0)


class RegistrationCheckResponse(BaseModel):
    """Schema for registration check response"""
    is_registered: bool
    registration_date: Optional[datetime] = None
    
# Auth Schemas

class LoginRequest(BaseModel):
    """Schema for login request"""
    login: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=1, description="Password")
    remember: bool = Field(default=False, description="Remember me checkbox")

    @field_validator('login', 'password')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace and validate not empty"""
        if not v or not v.strip():
            raise ValueError('This field cannot be empty')
        return v.strip()


class TokenResponse(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Schema for JWT token payload"""
    sub: str  # organizer_id
    exp: datetime
    
class EventListForBot(BaseModel):
    """Schema for event list displayed in bot"""
    id: int
    title: str
    date_time: datetime
    location: str
    type: str
    is_registered: bool = False

    model_config = {"from_attributes": True}
    
# Error Schemas

class ErrorDetail(BaseModel):
    """Schema for error detail"""
    loc: List[str] = Field(..., description="Location of error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    status_code: int


class ValidationErrorResponse(BaseModel):
    """Schema for validation error response"""
    detail: List[ErrorDetail]


class SuccessResponse(BaseModel):
    """Schema for generic success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None
    
# Some utility schemas

class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum number of records to return")


class EventFilters(BaseModel):
    """Schema for event filtering"""
    type: Optional[EventTypeEnum] = None
    organizer_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = Field(None, max_length=100)


# Update forward references
UserWithRegistrations.model_rebuild()
OrganizerWithEvents.model_rebuild()
EventWithRegistrations.model_rebuild()
EventWithOrganizer.model_rebuild()
RegistrationWithUser.model_rebuild()
RegistrationWithEvent.model_rebuild()
RegistrationWithDetails.model_rebuild()

EventCreate = as_form(EventCreate)
EventUpdate = as_form(EventUpdate)
OrganizerCreate = as_form(OrganizerCreate)
OrganizerUpdate = as_form(OrganizerUpdate)
LoginRequest = as_form(LoginRequest)