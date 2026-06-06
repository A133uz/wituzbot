"""
Helpers for serializing and deserializing multilingual event descriptions.
Descriptions are stored as JSON: {"en": "...", "ru": "...", "uz": "..."}
"""

import json
from typing import Dict, Optional


def serialize_description(desc_en: str, desc_ru: str = "", desc_uz: str = "") -> str:
    """
    Serialize language-specific descriptions into a JSON payload.
    
    Args:
        desc_en: English description (required)
        desc_ru: Russian description (optional)
        desc_uz: Uzbek description (optional)
    
    Returns:
        JSON string with keys: en, ru, uz
    """
    payload = {
        "en": desc_en.strip() if desc_en else "",
        "ru": desc_ru.strip() if desc_ru else "",
        "uz": desc_uz.strip() if desc_uz else "",
    }
    return json.dumps(payload, ensure_ascii=False)


def deserialize_description(desc_json: Optional[str]) -> Dict[str, str]:
    """
    Deserialize a JSON description payload into individual language fields.
    
    Args:
        desc_json: JSON string or None
    
    Returns:
        Dictionary with keys: en, ru, uz. Missing keys default to empty string.
    """
    if not desc_json:
        return {"en": "", "ru": "", "uz": ""}
    
    try:
        data = json.loads(desc_json)
        return {
            "en": data.get("en", ""),
            "ru": data.get("ru", ""),
            "uz": data.get("uz", ""),
        }
    except (json.JSONDecodeError, TypeError):
        # Fallback for legacy single-string descriptions
        return {
            "en": desc_json if isinstance(desc_json, str) else "",
            "ru": "",
            "uz": "",
        }


def get_description_for_language(desc_json: Optional[str], language: str) -> str:
    """
    Extract the description for a specific language with fallback to English.
    
    Args:
        desc_json: JSON string containing all descriptions
        language: Language code ('en', 'ru', 'uz')
    
    Returns:
        The description in the requested language, or English, or empty string.
    """
    deserialized = deserialize_description(desc_json)
    
    # Try the requested language first
    if language in deserialized and deserialized[language]:
        return deserialized[language]
    
    # Fall back to English
    if deserialized.get("en"):
        return deserialized["en"]
    
    # Fall back to first non-empty translation
    for lang_key in ["ru", "uz"]:
        if deserialized.get(lang_key):
            return deserialized[lang_key]
    
    return ""
