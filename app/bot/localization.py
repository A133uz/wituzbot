"""
Lightweight localization layer for the main Telegram bot.
Supports English (en), Russian (ru), and Uzbek Latin (uz).
"""

from typing import Optional, Dict, Any
from enum import Enum
import json


class Language(str, Enum):
    """Supported languages."""
    EN = "en"
    RU = "ru"
    UZ = "uz"


# Message catalogs for each language
MESSAGES = {
    Language.EN: {
        # Registration flow
        "reg_welcome": "Welcome! Let's meet! {question}",
        "reg_name": "What's your first name?\n\n<b>Example:</b> Alisher",
        "reg_surname": "What's your last name?\n\n<b>Example:</b> Valiyev",
        "reg_organization": "Where do you work/study?\n\n<b>Example:</b> Amity University",
        "reg_complete": "You have been successfully registered!",
        
        # Menu items
        "menu_browse": "📅 Browse Events",
        "menu_registrations": "📝 My Registrations",
        "menu_profile": "👤 My Profile",
        "menu_contacts": "Contacts",
        
        # Event descriptions
        "event_no_description": "No description available",
        "event_translate_missing": "(Translation not available - showing English)",
        
        # Greetings and responses
        "welcome_back": "Welcome back!",
        "problem_faced": "I faced a problem",
        "bug_report_msg": "🐛 <b>Found a Bug? We Want to Hear About It!</b>\n\nPlease contact our feedback bot: @womenintechuz_fb_bot\nRegistration will restart.",
        
        # Event browsing
        "no_events": "No upcoming events at the moment",
        "no_registrations": "You haven't registered for any event yet",
        "event_type_online": "online",
        "event_type_in_person": "in person",
        "event_datetime_format": "%d.%m.%Y at %H:%M",
        
        # Profile
        "profile_header": "👤 <b>Your Profile</b>",
        "profile_first_name": "📝 <b>First Name:</b> {name}",
        "profile_last_name": "📝 <b>Last Name:</b> {surname}",
        "profile_organization": "🏢 <b>Organization:</b> {organization}",
        "profile_language": "🌐 <b>Language:</b> {language}",
        "profile_update_name": "Update First Name",
        "profile_update_surname": "Update Last Name",
        "profile_update_org": "Update Organization",
        "profile_update_language": "Change Language",
        
        # Profile update prompts
        "update_name_prompt": "Please, enter your new first name:",
        "update_surname_prompt": "Please, enter your new last name:",
        "update_org_prompt": "Please, enter your new organization:",
        "profile_updated": "Profile data updated successfully!",
        
        # Registration buttons
        "btn_register": "📝 Register",
        "btn_registered": "✅ Registered",
        "btn_unregister": "❌ Unregister",
        "btn_skip": "Skip",
        
        # Registration flow messages
        "already_registered": "You are already registered for this event!",
        "registration_successful": "✅ Registration successful!",
        "registration_already_exists": "You are already registered for this event!",
        "registration_error_constraint": "❌ Registration failed due to database constraint.",
        "registration_error_validation": "❌ Validation error during registration.",
        "registration_error_unknown": "❌ An error occurred during registration.",
        "unregistration_successful": "✅ Successfully unregistered!",
        "unregistration_error_constraint": "❌ Failed to unregister due to database constraint.",
        "unregistration_error_validation": "❌ Validation error during unregistration.",
        "unregistration_error_unknown": "❌ An error occurred while unregistering.",
        
        # Event registration questions
        "email_prompt": "Please enter your email address.",
        "custom_question_prompt": "📝 {question}\n\nSend your answer.",
        
        # Validation errors (generic)
        "error_empty_value": "❌ Value cannot be empty. Please try again:",
        "error_invalid_field": "❌ Invalid field. Please start over.",
        
        # Contacts
        "contacts_msg": "🐛 <b>Found a Bug? We Want to Hear About It!</b>\n\nIf you've encountered any issues or bugs while using our service, please don't hesitate to report them! Your feedback helps us improve.\n\n📝 <b>How to report:</b>\nSend a message to our feedback bot: @womenintechuz_fb_bot \n\nYou can send:\n• Text descriptions of the problem\n• Screenshots or videos showing the issue\n\nWe appreciate your help in making our service better! 🙏",
        
        # Language selection
        "select_language": "🌐 Select your language:",
        "language_en": "English",
        "language_ru": "Русский",
        "language_uz": "Uzbek",
        "language_changed": "Language changed to {language}",
        
        # Event reminders
        "reminder_header": "🔔 Event Reminder!",
        "reminder_event_title": "📝",
        "reminder_starting_at": "📅 <b>Starting at</b>",
        "reminder_description": "📄 <b>Description:</b>",
        "reminder_location": "📍 <b>Location:</b>",
        "reminder_countdown": "⏰ <i>This event starts in approximately {hours} {hours_text}!</i>",
    },
    Language.RU: {
        # Registration flow
        "reg_welcome": "Добро пожаловать! Давайте познакомимся! {question}",
        "reg_name": "Как вас зовут? (Имя)\n\n<b>Пример:</b> Алишер",
        "reg_surname": "Ваша фамилия?\n\n<b>Пример:</b> Валиев",
        "reg_organization": "Где вы учитесь или работаете?\n\n<b>Пример:</b> Amity University",
        "reg_complete": "Вы успешно зарегистрированы!",
        
        # Menu items
        "menu_browse": "📅 Просмотр событий",
        "menu_registrations": "📝 Мои регистрации",
        "menu_profile": "👤 Мой профиль",
        "menu_contacts": "Контакты",
        
        # Greetings and responses
        "welcome_back": "С возвращением!",
        "problem_faced": "У меня проблема",
        "bug_report_msg": "🐛 <b>Нашли баг? Мы хотим об этом узнать!</b>\n\nПожалуйста, напишите нашему боту отзывов: @womenintechuz_fb_bot\nРегистрация начнется заново.",
        
        # Event browsing
        "no_events": "На данный момент нет предстоящих событий",
        "no_registrations": "Вы еще не зарегистрированы ни на одно событие",
        "event_type_online": "онлайн",
        "event_type_in_person": "очно",
        "event_datetime_format": "%d.%m.%Y в %H:%M",
        
        # Profile
        "profile_header": "👤 <b>Ваш профиль</b>",
        "profile_first_name": "📝 <b>Имя:</b> {name}",
        "profile_last_name": "📝 <b>Фамилия:</b> {surname}",
        "profile_organization": "🏢 <b>Организация:</b> {organization}",
        "profile_language": "🌐 <b>Язык:</b> {language}",
        "profile_update_name": "Обновить имя",
        "profile_update_surname": "Обновить фамилию",
        "profile_update_org": "Обновить организацию",
        "profile_update_language": "Изменить язык",
        
        # Profile update prompts
        "update_name_prompt": "Пожалуйста, введите ваше новое имя:",
        "update_surname_prompt": "Пожалуйста, введите вашу новую фамилию:",
        "update_org_prompt": "Пожалуйста, введите вашу новую организацию:",
        "profile_updated": "Данные профиля успешно обновлены!",
        
        # Registration buttons
        "btn_register": "📝 Зарегистрироваться",
        "btn_registered": "✅ Зарегистрирован",
        "btn_unregister": "❌ Отменить регистрацию",
        "btn_skip": "Пропустить",
        
        # Registration flow messages
        "already_registered": "Вы уже зарегистрированы на это событие!",
        "registration_successful": "✅ Регистрация успешна!",
        "registration_already_exists": "Вы уже зарегистрированы на это событие!",
        "registration_error_constraint": "❌ Регистрация не удалась из-за ошибки базы данных.",
        "registration_error_validation": "❌ Ошибка валидации при регистрации.",
        "registration_error_unknown": "❌ Произошла ошибка при регистрации.",
        "unregistration_successful": "✅ Успешно отменена регистрация!",
        "unregistration_error_constraint": "❌ Не удалось отменить регистрацию из-за ошибки базы данных.",
        "unregistration_error_validation": "❌ Ошибка валидации при отмене регистрации.",
        "unregistration_error_unknown": "❌ Произошла ошибка при отмене регистрации.",
        
        # Event registration questions
        "email_prompt": "Пожалуйста, введите ваш адрес электронной почты.",
        "custom_question_prompt": "📝 {question}\n\nОтправьте ваш ответ.",
        
        # Validation errors (generic)
        "error_empty_value": "❌ Значение не может быть пустым. Пожалуйста, попробуйте снова:",
        "error_invalid_field": "❌ Неверное поле. Пожалуйста, начните заново.",
        
        # Contacts
        "contacts_msg": "🐛 <b>Нашли баг? Мы хотим об этом узнать!</b>\n\nЕсли вы столкнулись с какими-либо проблемами или ошибками при использовании нашего сервиса, пожалуйста, не стесняйтесь сообщить о них! Ваш отзыв помогает нам улучшить сервис.\n\n📝 <b>Как сообщить об ошибке:</b>\nОтправьте сообщение нашему боту отзывов: @womenintechuz_fb_bot \n\nВы можете отправить:\n• Текстовое описание проблемы\n• Скриншоты или видео, демонстрирующие проблему\n\nМы ценим вашу помощь в улучшении нашего сервиса! 🙏",
        
        # Language selection
        "select_language": "🌐 Выберите свой язык:",
        "language_en": "English",
        "language_ru": "Русский",
        "language_uz": "Uzbek",
        "language_changed": "Язык изменен на {language}",
        
        # Event reminders
        "reminder_header": "🔔 Напоминание о событии!",
        "reminder_event_title": "📝",
        "reminder_starting_at": "📅 <b>Начинается в</b>",
        "reminder_description": "📄 <b>Описание:</b>",
        "reminder_location": "📍 <b>Место:</b>",
        "reminder_countdown": "⏰ <i>Это событие начнется примерно через {hours} {hours_text}!</i>",
    },
    Language.UZ: {
        # Registration flow
        "reg_welcome": "Xush kelibsiz! Tanishuv boshlansin! {question}",
        "reg_name": "Sizning ismingiz nima?\n\n<b>Misol:</b> Alisher",
        "reg_surname": "Sizning familyangiz nima?\n\n<b>Misol:</b> Valiyev",
        "reg_organization": "Siz qayerda o'qiyapsiz yoki ishlaysiz?\n\n<b>Misol:</b> Amity University",
        "reg_complete": "Siz muvaffaqiyatli ro'yxatdan o'tdingiz!",
        
        # Menu items
        "menu_browse": "📅 Tadbirlarni ko'rish",
        "menu_registrations": "📝 Mening ro'yxatlar",
        "menu_profile": "👤 Mening profil",
        "menu_contacts": "Aloqalar",
        
        # Greetings and responses
        "welcome_back": "Xush kelibsiz!",
        "problem_faced": "Menga muammo bor",
        "bug_report_msg": "🐛 <b>Xatoni topdingizmi? Biz bu haqida bilishni xohlaymiz!</b>\n\nIltimos, ushbu robotga yozing: @womenintechuz_fb_bot\nRo'yxatdan o'tish qayta boshlandi.",
        
        # Event browsing
        "no_events": "Hozirda hech qanday tadbir yo'q",
        "no_registrations": "Siz hali hech qanday tadbir uchun ro'yxatdan o'tmadingiz",
        "event_type_online": "onlayn",
        "event_type_in_person": "oflayn",
        "event_datetime_format": "%d.%m.%Y da %H:%M",
        
        # Profile
        "profile_header": "👤 <b>Sizning profilingiz</b>",
        "profile_first_name": "📝 <b>Ism:</b> {name}",
        "profile_last_name": "📝 <b>Familya:</b> {surname}",
        "profile_organization": "🏢 <b>Tashkilot:</b> {organization}",
        "profile_language": "🌐 <b>Til:</b> {language}",
        "profile_update_name": "Ismni o'zgartirish",
        "profile_update_surname": "Familyani o'zgartirish",
        "profile_update_org": "Tashkilotni o'zgartirish",
        "profile_update_language": "Tilni o'zgartirish",
        
        # Profile update prompts
        "update_name_prompt": "Iltimos, yangi ismingizni kiriting:",
        "update_surname_prompt": "Iltimos, yangi familyangizni kiriting:",
        "update_org_prompt": "Iltimos, yangi tashkilotingizni kiriting:",
        "profile_updated": "Profil ma'lumotlari muvaffaqiyatli yangilandi!",
        
        # Registration buttons
        "btn_register": "📝 Ro'yxatdan o'tish",
        "btn_registered": "✅ Ro'yxatdan o'tgan",
        "btn_unregister": "❌ Bekorini qilish",
        "btn_skip": "O'tkazib yuborish",
        
        # Registration flow messages
        "already_registered": "Siz bu tadbir uchun allaqachon ro'yxatdan o'tgansiz!",
        "registration_successful": "✅ Ro'yxatdan o'tish muvaffaqiyatli!",
        "registration_already_exists": "Siz bu tadbir uchun allaqachon ro'yxatdan o'tgansiz!",
        "registration_error_constraint": "❌ Ro'yxatdan o'tish bazada xatoga uchradi.",
        "registration_error_validation": "❌ Ro'yxatdan o'tish paytida tekshirish xatosi.",
        "registration_error_unknown": "❌ Ro'yxatdan o'tish paytida xato yuz berdi.",
        "unregistration_successful": "✅ Ro'yxatdan o'tish muvaffaqiyatli bekorildi!",
        "unregistration_error_constraint": "❌ Ro'yxatdan o'tishni bazada xatoga uchradi.",
        "unregistration_error_validation": "❌ Ro'yxatdan o'tishni bekorini qilish paytida tekshirish xatosi.",
        "unregistration_error_unknown": "❌ Ro'yxatdan o'tishni bekorini qilish paytida xato yuz berdi.",
        
        # Event registration questions
        "email_prompt": "Iltimos, email manzilingizni kiriting.",
        "custom_question_prompt": "📝 {question}\n\nJavob bering.",
        
        # Validation errors (generic)
        "error_empty_value": "❌ Qiymat bo'sh bo'lishi mumkin emas. Iltimos, qayta urinib ko'ring:",
        "error_invalid_field": "❌ Noto'g'ri maydon. Iltimos, qayta boshlang.",
        
        # Contacts
        "contacts_msg": "🐛 <b>Xatoni topdingizmi? Biz bu haqida bilishni xohlaymiz!</b>\n\nAgar siz xizmatimizdan foydalanishda qandaydir muammolar yoki xatolarni uchrashgan bo'lsangiz, iltimos, ularga xabar bering! Sizning fikringiz bizga xizmatni yaxshilashga yordam beradi.\n\n📝 <b>Xato haqida qanday xabar berish kerak:</b>\nShu botga xabar yuboring: @womenintechuz_fb_bot \n\nSiz quyidagilarni yuborishi mumkin:\n• Muammoning matn tavsifi\n• Muammoni ko'rsatuvchi skrinshot yoki video\n\nBizning xizmatni yaxshilashda yordam berganingiz uchun tashakkur! 🙏",
        
        # Language selection
        "select_language": "🌐 Tilni tanlang:",
        "language_en": "English",
        "language_ru": "Русский",
        "language_uz": "Uzbek",
        "language_changed": "Til o'zgartirildi: {language}",
        
        # Event reminders
        "reminder_header": "🔔 Tadbir haqida eslatma!",
        "reminder_event_title": "📝",
        "reminder_starting_at": "📅 <b>Boshlanadi</b>",
        "reminder_description": "📄 <b>Tavsif:</b>",
        "reminder_location": "📍 <b>Joylashuv:</b>",
        "reminder_countdown": "⏰ <i>Bu tadbir taxminan {hours} {hours_text} ichida boshlanadi!</i>",
    },
}


def get_language_from_telegram_code(tg_language_code: Optional[str]) -> Language:
    """
    Map Telegram language code to supported language.
    Falls back to English if not recognized.
    """
    if not tg_language_code:
        return Language.EN
    
    code_lower = tg_language_code.lower()
    if code_lower.startswith("ru"):
        return Language.RU
    elif code_lower.startswith("uz"):
        return Language.UZ
    
    return Language.EN


def t(key: str, lang = Language.EN, **kwargs) -> str:
    """
    Translate a message key to the specified language.
    Supports string formatting via kwargs.
    Accepts both Language enum and string language codes (en, ru, uz).
    Falls back to English if key or language not found.
    Includes hard fallback for reminder-specific keys.
    """
    # Normalize language input: accept both Language enum and string codes
    if isinstance(lang, str):
        try:
            lang = Language(lang)
        except (ValueError, KeyError):
            lang = Language.EN
    elif not isinstance(lang, Language):
        lang = Language.EN
    
    # Hard fallback map for reminder-specific keys in case catalog is out of sync
    reminder_fallbacks = {
        Language.EN: {
            "reminder_header": "🔔 Event Reminder!",
            "reminder_event_title": "📝",
            "reminder_starting_at": "📅 <b>Starting at</b>",
            "reminder_description": "📄 <b>Description:</b>",
            "reminder_location": "📍 <b>Location:</b>",
            "reminder_countdown": "⏰ <i>This event starts in approximately {hours} {hours_text}!</i>",
        },
        Language.RU: {
            "reminder_header": "🔔 Напоминание о событии!",
            "reminder_event_title": "📝",
            "reminder_starting_at": "📅 <b>Начинается в</b>",
            "reminder_description": "📄 <b>Описание:</b>",
            "reminder_location": "📍 <b>Место:</b>",
            "reminder_countdown": "⏰ <i>Это событие начнется примерно через {hours} {hours_text}!</i>",
        },
        Language.UZ: {
            "reminder_header": "🔔 Tadbir haqida eslatma!",
            "reminder_event_title": "📝",
            "reminder_starting_at": "📅 <b>Boshlanadi</b>",
            "reminder_description": "📄 <b>Tavsif:</b>",
            "reminder_location": "📍 <b>Joylashuv:</b>",
            "reminder_countdown": "⏰ <i>Bu tadbir taxminan {hours} {hours_text} ichida boshlanadi!</i>",
        },
    }
    
    # Try to get from catalog first
    catalog = MESSAGES.get(lang, MESSAGES[Language.EN])
    message = catalog.get(key)
    
    # If not found in catalog, check hard fallback for reminder keys
    if message is None:
        fallback_map = reminder_fallbacks.get(lang, reminder_fallbacks[Language.EN])
        message = fallback_map.get(key)
    
    # Final fallback to English catalog or hard fallback
    if message is None:
        en_catalog = MESSAGES.get(Language.EN, {})
        message = en_catalog.get(key)
    
    # Last resort: hard fallback English reminder or missing key marker
    if message is None:
        message = reminder_fallbacks[Language.EN].get(key, f"[MISSING: {key}]")
    
    if kwargs:
        try:
            return message.format(**kwargs)
        except KeyError as e:
            return f"[FORMAT ERROR: {message}] ({e})"
    
    return message


def get_display_language_name(lang: Language) -> str:
    """Get the display name for a language in its own language."""
    names = {
        Language.EN: "English",
        Language.RU: "Русский",
        Language.UZ: "Uzbek",
    }
    return names.get(lang, lang.value)


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
        # Fallback for legacy single-string descriptions (from before migration)
        return {
            "en": desc_json if isinstance(desc_json, str) else "",
            "ru": "",
            "uz": "",
        }


def get_description_for_language(desc_json: Optional[str], language: Language) -> str:
    """
    Extract the description for a specific language with fallback to English.
    
    Args:
        desc_json: JSON string containing all descriptions
        language: Language enum ('en', 'ru', 'uz')
    
    Returns:
        The description in the requested language, or English, or empty string.
    """
    deserialized = deserialize_description(desc_json)
    
    # Try the requested language first
    if language.value in deserialized and deserialized[language.value]:
        return deserialized[language.value]
    
    # Fall back to English
    if deserialized.get("en"):
        return deserialized["en"]
    
    # Fall back to first non-empty translation
    for lang_key in ["ru", "uz"]:
        if deserialized.get(lang_key):
            return deserialized[lang_key]
    
    return t("event_no_description", Language.EN)
