import asyncio
from telethon import TelegramClient, events
from telegram import Bot
from telegram.constants import ParseMode
import json
import os
import config
from message_cleaner import remove_specific_ad_block, fix_triple_asterisks

LAST_MESSAGE_IDS_FILE = 'last_message_ids.json'
last_message_ids = {}

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
    # html_text is just cleaned_text now
    # Get channel name for footer
    try:
        entity = await telethon_client.get_entity(channel_id)
        channel_name = getattr(entity, 'title', None) or getattr(entity, 'username', None) or str(channel_id)
    except Exception:
        channel_name = str(channel_id)
    # Only forward to the Hebrew channel
    target_channel_info = config.TARGET_CHANNELS["he"]
    target_channel_id = target_channel_info["id"]
    final_caption = f"<b>News:</b>\n{cleaned_text}\n\n(<i>{channel_name}</i>)"
    if not cleaned_text.strip() and not media_file_path:
        print("Skipping empty message after cleaning.")
        last_message_ids[channel_id] = message.id
        save_last_message_ids()
        return
    try:
        if media_file_path:
            with open(media_file_path, 'rb') as f:
                if message.photo:
                    await telegram_bot.send_photo(
                        chat_id=target_channel_id,
                        photo=f,
                        caption=final_caption,
                        parse_mode="HTML"
                    )
                elif message.video:
                    await telegram_bot.send_video(
                        chat_id=target_channel_id,
                        video=f,
                        caption=final_caption,
                        parse_mode="HTML"
                    )
        elif cleaned_text.strip():
            await telegram_bot.send_message(
                chat_id=target_channel_id,
                text=final_caption,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error forwarding message: {e}")
    finally:
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
