import os

def str_to_bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "on")

LOGIN_SYSTEM = str_to_bool(os.environ.get("LOGIN_SYSTEM", "true"))

if not LOGIN_SYSTEM:
    STRING_SESSION = os.environ.get("STRING_SESSION", "")
else:
    STRING_SESSION = None

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

ADMINS = int(os.environ.get("ADMINS", "6073523936"))

CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

DB_URI = os.environ.get("DB_URI", "")
DB_NAME = os.environ.get("DB_NAME", "savecontentbot")

WAITING_TIME = int(os.environ.get("WAITING_TIME", "10"))

ERROR_MESSAGE = str_to_bool(os.environ.get("ERROR_MESSAGE", "true"))
