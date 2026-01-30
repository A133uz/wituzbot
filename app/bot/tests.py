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
    "Alexey",                            # Latin
    "Екатерина",                         # Cyrillic
    "Жан-Поль",                          # Cyrillic with hyphen
    "O'Connor",                          # Apostrophe
    "Джон Смит",                         # Cyrillic + space
    "Anna-Marie.",                       # Latin, hyphen, period
    "Ибрагимов-Смит",                    # Cyrillic, hyphen
    "Мария.",                            # Cyrillic, period
    "María",                             # Latin with accent (accept if allowed)
    "Джон-С.",                           # Cyrillic, hyphen, period 
    "Nuriddin",                          # Uzbek Latin
])
def test_validate_name_or_surname_valid(value):
    assert validate_name_or_surname(value, "Name") == value.strip()

@pytest.mark.parametrize("value", [
    "",                                  # Empty
    " "*3,                               # Only spaces
    "A"*26,                              # Latin, too long
    "А"*26,                              # Cyrillic, too long
    "Smith123",                          # Digits in name (invalid!)
    "Ибрагимов!",                        # Exclamation
    "<Сергей>",                          # HTML
    "|Alex|",                            # Pipe symbol
    "Мария#",                            # Hash symbol
    "🦄John",                            # Emoji
    "Smith_",                            # Underscore (if not allowed)
    "См@рт",                             # @ Symbol
])
def test_validate_name_or_surname_invalid(value):
    with pytest.raises(ValueError):
        validate_name_or_surname(value, "Name")

# ------------------- Organization -------------------

@pytest.mark.parametrize("value", [
    "Эко-Химия",                     # Cyrillic + hyphen
    "ООО Комфорт",                   # Cyrillic, spaces
    "Ventures & Co.",                # Ampersand, dot
    "Tashkent Institute",            # Latin
    "University of Нью-Йорк",        # Mixed
    "ООО «Рога и Копыта»",           # Russian quotes (add to regex if you want)
    "Instituto №1",                  # Number sign (add to regex if you support it)
    "OOO (Рога и Копыта), Ltd.",     # Parentheses, comma, dot
    "Институт 13",                   # Digits
    "Test & Partners (Uzbekistan)",  # Mix, parentheses, ampersand
    "Uzbek Tiles, Ltd.",             # Comma, dot
])
def test_validate_org_valid(value):
    assert validate_org(value) == value.strip()

@pytest.mark.parametrize("value", [
    "",                                  # Empty string
    "   ",                               # Just spaces
    "A"*101,                             # Too long
    "<HeadCorp>",                        # HTML tags
    "My*Organization",                   # Disallowed symbol
    "Орг@название",                      # Disallowed symbol
    "|Институт|",                        # Pipes
    "ООО #1",                            # Hash (unless you allow)
    "Институт →",                        # Arrow (disallowed, unless added)
    "Институт🙂",                         # Emoji
    "Company%",                          # Percent
])
def test_validate_org_invalid(value):
    with pytest.raises(ValueError):
        validate_org(value)

# ------------------- Email -------------------

@pytest.mark.parametrize("email", [
    "user@example.com",
    "имя@пример.рф",                     # Cyrillic domain (IDN, valid in pydantic EmailStr with punycode support)
    "foo.bar-baz_99@test-domain.io",
    "john.smith@uni.edu",
    "test.email+alias@gmail.com",
])
def test_validate_email_valid(email):
    assert validate_email(email) == email.strip()

@pytest.mark.parametrize("email", [
    "",                                  # Empty
    "user@",                             # No domain
    "user@example",                      # No TLD
    "user@.com",                         # Leading dot
    "a"*101 + "@test.com",               # Too long
    "foo@bar.com<script>",               # Injected HTML
    "no-at-symbol.com",                  # Missing at
    "foo bar@example.com",               # Space inside
])
def test_validate_email_invalid(email):
    with pytest.raises(ValueError):
        validate_email(email)

# ------------------- Phone (strict E.164: must start with +, digits only, optional allow normalization) -------------------
@pytest.mark.parametrize("phone", [
    "+998901234567",               # Uzbekistan mobile
    "+7 495 123-45-67",            # Russia, Moscow (format with spaces/dashes)
    "+1-202-555-0138",             # US
    "+49 30 123456",               # Germany, Berlin
    "+44 20 7946 0958",            # UK, London
    "+862112345678",               # China, Beijing
    "+91 98765 43210",             # India
    "+90 (212) 555 1234",          # Turkey
    "+33 1 23 45 67 89",           # France
    "+61 3 9123 4567",             # Australia
    "+55 11 91234-5678",           # Brazil
    "+39 06 123456",               # Italy
    "+82 2-2123-4567",             # Korea, Seoul
    "+86 138-1234-5678",           # China, Mobile
    "+375 29 1234567",             # Belarus
    "+49(0)30123456",              # Germany with (0) (should be normalized)
    "+1 (800) 555-0199",           # US toll-free
    "+234 803 123 4567",           # Nigeria
    "+998 (90) 123-45-67",         # Uzbekistan, formatted
    "+7(999)999-99-99",            # Russia, formatted
])
def test_validate_phone_valid(phone):
    res = validate_phone(phone)
    assert res.startswith("+")
    assert res.replace("+", "").isdigit()
    assert 10 <= len(res.replace("+", "")) <= 15

# ------ Invalid phone numbers (should always raise) ------
@pytest.mark.parametrize("phone", [
    "",                            # Empty
    "    ",                        # Only spaces
    "+",                           # Just plus sign
    "998901234567",                # No plus (invalid if not normalized)
    "++998901234567",              # Double plus
    "+99890123456789012345",       # Too long
    "+99890",                      # Too short
    "+123-abc-4567",               # Letters 
    "+49-99/123456",               # Slash
    "+44 (12) 34 56",              # Too short for UK
    "+1 (555) !!0199",             # Punctuation
    "+1(800) 555-0199!",           # Exclamation
    "+1-202-555-0138 extra",       # Suffix
    "+86 138-1234-567812345",      # Too long for CN mobile
    "+1234567890🙂",               # Emoji
    "+7@999@9999999",              # At-symbols
    "00123456789",                 # Old Europe format (unless you accept auto-conversion)
    "+7(999)999-99-99 script",     # Script injected
    "+",                           # Too short
    "+abc",                        # Only letters
    "+123-456-789-012345",         # Broken groupings, too long
])
def test_validate_phone_invalid(phone):
    with pytest.raises(ValueError):
        validate_phone(phone)

# --- LOGGING OVERRIDE FOR TESTS ---
@pytest.fixture(autouse=True)
def reset_logger(caplog):
    caplog.set_level(logging.DEBUG)
