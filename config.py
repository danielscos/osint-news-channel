import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# --- API Keys (loaded from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_telethon_api_id = os.getenv("TELETHON_API_ID")
if _telethon_api_id is None:
    raise ValueError("TELETHON_API_ID environment variable is not set")
TELETHON_API_ID = int(_telethon_api_id)
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH")

# --- Bot Configuration ---

# List of numerical IDs for the news channels you want to monitor.
# YOU WILL POPULATE THIS LATER IN Step 5 of the "First Run" instructions.
SOURCE_CHANNEL_ENTITIES = [
    -1002164860351,
    -1002261999576,  # מלחמת ישראל איראן🇮🇷💥🇮🇱
    -1001745841781,  # 24X6 NEWS ISRAEL
    -1001309313432,  # חדשות הקוסמוס
] # Example: [-1001234567890, -1009876543210]

# List of usernames for the news channels you want to monitor (for cleaning mentions).
# YOU WILL POPULATE THIS LATER IN Step 5.
SOURCE_CHANNEL_USERNAMES = [
    "חדשות לפני כולם בטלגרם",
    "מלחמת ישראל איראן",
    "24X6 NEWS ISRAEL",
    "חדשות הקוסמוס",
] # Example: ["bbcnews", "reuters"]

# Dictionary of your target Telegram channels where translated news will be sent.
# Replace the 'id' with the actual numerical ID of your Telegram channels.
# You get these IDs by forwarding a message from your channel to @JsonDumpBot or @GetMyID_bot.
# Remember channel IDs are large negative numbers (e.g., -1001234567890).
#
# IMPORTANT: Create these channels in Telegram first.
# Make sure your BOT (the one from BotFather) is an ADMIN in these target channels
# with "Post Messages" permission.
TARGET_CHANNELS = {
    "en": {"id": -1002745106845, "name": "OSINT News - English"}, # <-- REPLACE THIS ID
    "he": {"id": -1002677930861, "name": "OSINT News - Hebrew"}    # Add more languages/channels as needed
}