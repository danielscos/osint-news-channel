import asyncio
from telethon import TelegramClient, events
from telegram import Bot
import json
import os
import config
from message_cleaner import remove_specific_ad_block, fix_triple_asterisks
from translator import translate
import re
import time
from difflib import SequenceMatcher
import string

LAST_MESSAGE_IDS_FILE = 'last_message_ids.json'
last_message_ids = {}

# Store recent messages for deduplication
RECENT_MESSAGES = []  # List of dicts: {"text": ..., "timestamp": ...}
RECENT_WINDOW_SECONDS = 300  # 5 minutes
SIMILARITY_THRESHOLD = 0.92  # 92% similar or more is considered duplicate

def load_last_message_ids():
    global last_message_ids
    if os.path.exists(LAST_MESSAGE_IDS_FILE):
        with open(LAST_MESSAGE_IDS_FILE, 'r') as f:
            try:
                last_message_ids = json.load(f)
                last_message_ids = {int(k): v for k, v in last_message_ids.items()}
            except json.JSONDecodeError:
                print("last_message_ids.json is empty or corrupted. Starting fresh.")
                last_message_ids = {}
    else:
        print("last_message_ids.json not found. Starting fresh.")
        last_message_ids = {}

def save_last_message_ids():
    with open(LAST_MESSAGE_IDS_FILE, 'w') as f:
        json.dump(last_message_ids, f)

if not isinstance(config.TELEGRAM_BOT_TOKEN, str) or not config.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be a non-empty string in config.py")
if not isinstance(config.TELETHON_API_ID, int) or config.TELETHON_API_ID is None:
    raise ValueError("TELETHON_API_ID must be a non-empty integer in config.py")
if not isinstance(config.TELETHON_API_HASH, str) or not config.TELETHON_API_HASH:
    raise ValueError("TELETHON_API_HASH must be a non-empty string in config.py")

telegram_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
telethon_client = TelegramClient('session_name', config.TELETHON_API_ID, config.TELETHON_API_HASH)

def markdown_to_telegram_html(text):
    # Bold: **text** or __text__ -> <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Italic: *text* or _text_ -> <i>text</i>
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    # Links: [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[(.+?)\]\((https?://[^\s]+)\)', r'<a href="\2">\1</a>', text)
    return text

def normalize_text(text):
    # Lowercase, remove punctuation, collapse whitespace
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = ' '.join(text.split())
    return text

def is_similar_to_recent(text):
    now = time.time()
    # Remove old messages from RECENT_MESSAGES
    global RECENT_MESSAGES
    RECENT_MESSAGES = [msg for msg in RECENT_MESSAGES if now - msg["timestamp"] < RECENT_WINDOW_SECONDS]
    norm_text = normalize_text(text)
    for msg in RECENT_MESSAGES:
        norm_recent = normalize_text(msg["text"])
        similarity = SequenceMatcher(None, norm_text, norm_recent).ratio()
        if similarity >= SIMILARITY_THRESHOLD:
            return True
    return False

@telethon_client.on(events.NewMessage(chats=config.SOURCE_CHANNEL_ENTITIES))
async def handle_new_source_message(event):
    message = event.message
    channel_id = message.peer_id.channel_id if hasattr(message.peer_id, 'channel_id') else None
    print(f"Received message from channel_id: {channel_id}")  # Debug print
    if not channel_id:
        print(f"Skipping message from unknown peer type: {type(message.peer_id).__name__}")
        return
    if channel_id in last_message_ids and message.id <= last_message_ids[channel_id]:
        print(f"Skipping already processed message {message.id}")
        return
    original_text = message.text
    print(f"Original text: {original_text}")  # Debug print
    media_file_path = None
    downloads_dir = 'downloads'
    os.makedirs(downloads_dir, exist_ok=True)
    if message.photo:
        media_file_path = os.path.join(downloads_dir, f"photo_{message.id}.jpg")
        try:
            await message.download_media(file=media_file_path)
        except Exception as e:
            print(f"Error downloading photo: {e}")
            media_file_path = None
    elif message.video:
        media_file_path = os.path.join(downloads_dir, f"video_{message.id}.mp4")
        try:
            await message.download_media(file=media_file_path)
        except Exception as e:
            print(f"Error downloading video: {e}")
            media_file_path = None
    if not original_text and not media_file_path:
        last_message_ids[channel_id] = message.id
        save_last_message_ids()
        return
    # First, fix triple asterisks, then clean ads
    cleaned_text = remove_specific_ad_block(fix_triple_asterisks(original_text if original_text else ""))
    cleaned_text = cleaned_text.strip()

    # Convert cleaned_text and translated_text from Markdown to Telegram HTML
    cleaned_text_html = markdown_to_telegram_html(cleaned_text) if cleaned_text else ""

    # Get channel name for footer (move this up before sending)
    try:
        entity = await telethon_client.get_entity(channel_id)
        channel_name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or str(channel_id)
    except Exception:
        channel_name = str(channel_id)

    final_caption = f"<b>News:</b>\n{cleaned_text_html}\n\n(<i>{channel_name}</i>)"

    # Send Hebrew message immediately
    hebrew_media_sent = False
    target_channel_info_he = config.TARGET_CHANNELS["he"]
    target_channel_id_he = target_channel_info_he["id"]
    try:
        if media_file_path:
            with open(media_file_path, 'rb') as f:
                if message.photo:
                    await telegram_bot.send_photo(
                        chat_id=target_channel_id_he,
                        photo=f,
                        caption=final_caption,
                        parse_mode="HTML"
                    )
                    hebrew_media_sent = True
                elif message.video:
                    await telegram_bot.send_video(
                        chat_id=target_channel_id_he,
                        video=f,
                        caption=final_caption,
                        parse_mode="HTML"
                    )
                    hebrew_media_sent = True
        elif cleaned_text.strip():
            await telegram_bot.send_message(
                chat_id=target_channel_id_he,
                text=final_caption,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error forwarding message to Hebrew channel: {e}")

    # Translate and send to English channel (if translation is available)
    translated_text = ""
    translated_text_html = ""
    if cleaned_text:
        try:
            translated_text = translate(cleaned_text, from_lang="he", to_lang="en")
            translated_text_html = markdown_to_telegram_html(translated_text) if translated_text else ""
        except Exception as e:
            print(f"Translation error: {e}")
            translated_text = ""
            translated_text_html = ""

    if translated_text:
        target_channel_info_en = config.TARGET_CHANNELS["en"]
        target_channel_id_en = target_channel_info_en["id"]
        final_caption_en = f"<b>News (EN):</b>\n{translated_text_html}\n\n(<i>{channel_name}</i>)"
        try:
            if media_file_path and hebrew_media_sent:
                with open(media_file_path, 'rb') as f:
                    if message.photo:
                        await telegram_bot.send_photo(
                            chat_id=target_channel_id_en,
                            photo=f,
                            caption=final_caption_en,
                            parse_mode="HTML"
                        )
                    elif message.video:
                        await telegram_bot.send_video(
                            chat_id=target_channel_id_en,
                            video=f,
                            caption=final_caption_en,
                            parse_mode="HTML"
                        )
            else:
                await telegram_bot.send_message(
                    chat_id=target_channel_id_en,
                    text=final_caption_en,
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Error forwarding message to English channel: {e}")

    # Only delete the media file after both sends
    if media_file_path and os.path.exists(media_file_path):
        try:
            os.remove(media_file_path)
        except Exception as e:
            print(f"Error removing media file: {e}")

    last_message_ids[channel_id] = message.id
    save_last_message_ids()

async def main():
    print("Loading last processed message IDs...")
    load_last_message_ids()
    print("Authenticating Telethon client...")
    await telethon_client.start()
    print("Telethon client connected.")
    print("Bot is listening for new messages in configured source channels...")
    await telethon_client.run_until_disconnected()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'dedup_test':
        print("Deduplication test mode. Type messages, Ctrl+D to end.")
        try:
            while True:
                print("\nEnter message:")
                msg = sys.stdin.readline()
                if not msg:
                    break
                msg = msg.strip()
                if not msg:
                    continue
                if is_similar_to_recent(msg):
                    print("[SKIPPED] Similar to recent message.")
                else:
                    print("[SENT] Message accepted.")
                    RECENT_MESSAGES.append({"text": msg, "timestamp": time.time()})
        except KeyboardInterrupt:
            print("\nTest ended by user.")
        sys.exit(0)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
