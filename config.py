import os
from dotenv import load_dotenv
load_dotenv()

# --- API Keys (loaded from .env) ---

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_telethon_api_id = os.getenv("TELETHON_API_ID")
if _telethon_api_id is None:
    raise ValueError("TELETHON_API_ID environment variable is not set")
TELETHON_API_ID = int(_telethon_api_id)
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH")

# --- Bot Configuration ---

SOURCE_CHANNEL_ENTITIES = [
    -1002726720354,
]

SOURCE_CHANNEL_USERNAMES = [
    "test_channel_osint",
]

TARGET_CHANNELS = {
    "en": {"id": -1002745106845, "name": "OSINT News - English"},
    "he": {"id": -1002677930861, "name": "OSINT News - Hebrew"}
}
