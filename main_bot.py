import asyncio
from telethon import TelegramClient, events
from telegram import Bot
import json
import os
import config
from message_cleaner import clean_message, remove_specific_ad_block
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

def extract_red_alert_summary(text):
    import re
    # Detect if this is a Red Alert message
    if "צבע אדום" not in text:
        return None
    # Extract date/time
    date_time_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}:\d{2})", text)
    date_time = f"{date_time_match.group(1)} {date_time_match.group(2)}" if date_time_match else ""
    # Extract main regions (lines starting with • and ending with colon)
    regions = re.findall(r"•\s*([^:]+):", text)
    regions_str = ", ".join(regions) if regions else "אזורים לא ידועים"
    # Extract instruction (look for 'היכנסו למרחב המוגן' or similar)
    instruction_match = re.search(r"היכנסו למרחב המוגן[^\n]*", text)
    instruction = instruction_match.group(0) if instruction_match else ""
    # Build summary
    summary = f"🚨 צבע אדום (Red Alert){' - ' + date_time if date_time else ''}\nאזורים עיקריים: {regions_str}"
    if instruction:
        summary += f"\n{instruction}"
    return summary

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
    # Only allow alerts from פיקוד העורף, and only allow news from other channels
    pikud_haoref_id = -1001441886157
    is_pikud_haoref = (channel_id == pikud_haoref_id)
    cleaned_alert = clean_message(original_text if original_text else "")
    is_alert = cleaned_alert != remove_specific_ad_block(original_text)
    # If the message is just an ad (fully removed), skip sending and skip media
    ad_only = cleaned_alert.strip() == ''
    if ad_only:
        print(f"Skipping ad-only message (and media) from channel_id: {channel_id}")
        last_message_ids[channel_id] = message.id
        save_last_message_ids()
        return
    if is_pikud_haoref:
        if not is_alert:
            print(f"Skipping non-alert from פיקוד העורף: {channel_id}")
            last_message_ids[channel_id] = message.id
            save_last_message_ids()
            return
    else:
        if is_alert:
            print(f"Skipping alert from non-authoritative channel: {channel_id}")
            last_message_ids[channel_id] = message.id
            save_last_message_ids()
            return
    cleaned_text = cleaned_alert.strip()

    # Convert cleaned_text and translated_text from Markdown to Telegram HTML
    cleaned_text_html = markdown_to_telegram_html(cleaned_text) if cleaned_text else ""

    # Get channel name for footer (move this up before sending)
    try:
        entity = await telethon_client.get_entity(channel_id)
        channel_name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or str(channel_id)
    except Exception:
        channel_name = str(channel_id)

    # Add פיקוד העורף footer if relevant
    pikud_haoref_ids = {-1001441886157}
    pikud_haoref_names = {"פיקוד העורף", "Home Front Command"}
    is_pikud_haoref = (channel_id in pikud_haoref_ids) or (str(channel_name).strip() in pikud_haoref_names)
    pikud_footer = "\n\nהודעה זו התקבלה מפיקוד העורף"
    cleaned_text_with_footer = cleaned_text + pikud_footer if is_pikud_haoref else cleaned_text
    cleaned_text_html = markdown_to_telegram_html(cleaned_text_with_footer) if cleaned_text_with_footer else ""

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
            translated_text = translate(cleaned_text_with_footer, from_lang="he", to_lang="en") if is_pikud_haoref else translate(cleaned_text, from_lang="he", to_lang="en")
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
    elif len(sys.argv) > 1 and sys.argv[1] == 'full_test':
        # Full bot logic test mode (loop)
        import sys
        import config
        from message_cleaner import clean_message, remove_specific_ad_block
        channel_map = {}
        for idx, cid in enumerate(config.SOURCE_CHANNEL_ENTITIES):
            name = None
            if idx < len(config.SOURCE_CHANNEL_USERNAMES):
                name = config.SOURCE_CHANNEL_USERNAMES[idx]
            channel_map[str(idx+1)] = (cid, name)
        print("\nFull bot test mode. Ctrl+C to exit.")
        try:
            while True:
                print("\nAvailable channels:")
                for num, (cid, name) in channel_map.items():
                    print(f"{num}. {name or cid} (ID: {cid})")
                choice = input("\nSelect a channel by number: ").strip()
                if choice not in channel_map:
                    print("Invalid choice. Try again.")
                    continue
                channel_id, channel_name = channel_map[choice]
                print(f"\nPaste your test message for {channel_name or channel_id} (end with Ctrl+D):")
                input_text = sys.stdin.read()
                print("\n--- Original ---\n" + input_text)
                # Deduplication check
                if is_similar_to_recent(input_text):
                    print("\n[SKIPPED] Similar to recent message (deduplication). Would NOT be sent.")
                    continue
                # Alert logic (same as in handler)
                pikud_haoref_id = -1001441886157
                is_pikud_haoref = (channel_id == pikud_haoref_id)
                cleaned_alert = clean_message(input_text)
                is_alert = cleaned_alert != remove_specific_ad_block(input_text)
                if is_pikud_haoref:
                    if is_alert:
                        print("\n[SENT] This alert WOULD be sent (פיקוד העורף, alert type).\n")
                        print("--- After cleaning ---\n" + cleaned_alert)
                        RECENT_MESSAGES.append({"text": input_text, "timestamp": time.time()})
                    else:
                        print("\n[SKIPPED] Not an alert (פיקוד העורף, but not alert type). Would NOT be sent.")
                else:
                    if is_alert:
                        print("\n[SKIPPED] Alert, but not from פיקוד העורף. Would NOT be sent.")
                    else:
                        print("\n[SENT] This news WOULD be sent (regular news from other channel).\n")
                        print("--- After cleaning ---\n" + cleaned_alert)
                        RECENT_MESSAGES.append({"text": input_text, "timestamp": time.time()})
        except KeyboardInterrupt:
            print("\nTest ended by user.")
        sys.exit(0)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
