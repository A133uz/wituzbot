import re
from pydantic import EmailStr
import phonenumbers
from phonenumbers import NumberParseException
import logging

logger = logging.getLogger(__name__)

def validate_name_or_surname(value: str, field_name: str) -> str:
    """Validate name/surname fields"""
    value = value.strip()
    if not value or len(value) < 1:
        raise ValueError(f'{field_name} cannot be empty')
    if len(value) > 25:
        raise ValueError(f'{field_name} cannot exceed 25 characters')
    if not re.match(r"^[a-zA-Z\u0400-\u04FF\s\-'\.]+$", value):
        raise ValueError(f'{field_name} can only contain letters, spaces, hyphens, apostrophes, and periods')
    return value

def validate_org(value: str) -> str:
    """Validate organization field"""
    value = value.strip()
    if not value or len(value) < 1:
        raise ValueError('Organization cannot be empty')
    if len(value) > 100:
        raise ValueError('Organization cannot exceed 100 characters')
    if not re.match(r"^[a-zA-Z\u0400-\u04FF0-9\s\-\.&(),]+$", value):
        raise ValueError('Organization can only contain standard characters')
    return value

def validate_email(value: str) -> str:
    """Validate email field"""
    value = value.strip()
    try:
        EmailStr._validate(value)
    except Exception:
        raise ValueError('Please enter a valid email address')
    if len(value) > 100:
        raise ValueError('Email cannot exceed 100 characters')
    return value

def validate_phone(value: str) -> str:
    """Validate phone number and return E.164 format"""
    value = value.strip()
    logger.info(f"Phone validation start: original='{value}'")
    
    if not value.startswith("+"):
        formatted_value = "+" + value
    else:
        formatted_value = value

    normalized = re.sub(r'[\s\-\(\)]', '', formatted_value)

    if not re.match(r'^\+\d+$', normalized):
        logger.warning(f"Rejected phone (invalid format): '{normalized}'")
        raise ValueError("❌ Please share your phone number in international format (one '+' followed by digits, e.g., +998901234567).")

    try:
        parsed = phonenumbers.parse(normalized, None)
        logger.info(f"Parsed phone: raw='{normalized}', region='{parsed.country_code}'")
        if not phonenumbers.is_valid_number(parsed):
            logger.warning(f"Invalid phone number (phonenumbers check failed): '{normalized}'")
            raise ValueError('❌ Invalid phone number')
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        logger.info(f"Valid phone, E.164 format: '{e164}'")
        return e164
    except Exception as exc:
        logger.error(f"Phone parse fail [{normalized}]: {exc}")
        raise ValueError('❌ Phone number must be in international format (e.g., +49..., +7..., +998...)')