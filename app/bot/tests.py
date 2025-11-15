import pytest
import re
import logging
from pydantic import EmailStr
import phonenumbers
from .validators import (
    validate_name_or_surname,
    validate_org,
    validate_email,
    validate_phone
)

# --- NAME OR SURNAME ---

@pytest.mark.parametrize("value", [
    "Alice",
    "O'Connor",
    "Jean-Paul",
    "Mary Jane",
    "Dr. Smith",
    "Test".ljust(25, "x"),
])
def test_validate_name_or_surname_valid(value):
    assert validate_name_or_surname(value, "Name") == value.strip()

@pytest.mark.parametrize("value", [
    "",
    "   ",
    "a"*26, # Too long
    "B1ll",
    "Smith!", # Illegal char
    "<script>",
    "Юлия", # Non-latin chars if not allowed
])
def test_validate_name_or_surname_invalid(value):
    with pytest.raises(ValueError):
        validate_name_or_surname(value, "Name")

# --- ORG ---

@pytest.mark.parametrize("value", [
    "ACME Corp",
    "University of Science",
    "My School",
    "My Startup".ljust(100,"x"),
])
def test_validate_org_valid(value):
    assert validate_org(value) == value.strip()

@pytest.mark.parametrize("value", [
    "",
    " "*10,
    "A"*101,
    "<img src=x onerror=alert(1)>",
])
def test_validate_org_invalid(value):
    with pytest.raises(ValueError):
        validate_org(value)

# --- EMAIL ---

@pytest.mark.parametrize("value", [
    "alice@example.com",
    "bob.smith99@domain.co.uk",
    "foo@bar.io",
])
def test_validate_email_valid(value):
    assert validate_email(value) == value.strip()

@pytest.mark.parametrize("value", [
    "",
    "not-an-email",
    "foo@bar",
    "a"*101 + "@example.com",
    "foo@example.com<script>",
])
def test_validate_email_invalid(value):
    with pytest.raises(ValueError):
        validate_email(value)

# --- PHONE ---

@pytest.mark.parametrize("value", [
    "+998901234567",
    "+7 999 999-99-99",
    "+49 301234567",
    "+447911123456",   # UK mobile
    "+12025550116",
    "+998(90)1234567",
    "+7-999-9999999",
])
def test_validate_phone_valid(value):
    normalized = validate_phone(value)
    assert normalized.startswith("+")
    assert re.match(r"^\+\d{10,15}$", normalized)  # E.164 format

@pytest.mark.parametrize("value", [
    "998901234567",          # missing +
    "+123abc456789",         # letters
    "+",                     # too short
    "+99890123",             # too short for Uzbekistan
    "+7000000000<script>",   # XSS
    "+998901234567"*10,      # way too long
    "++998901234567",        # double plus
    "00123456789",           # European 00 prefix but missing country
    "",
    "   ",
])
def test_validate_phone_invalid(value):
    with pytest.raises(ValueError):
        validate_phone(value)

# --- LOGGING OVERRIDE FOR TESTS ---
@pytest.fixture(autouse=True)
def reset_logger(caplog):
    caplog.set_level(logging.DEBUG)
