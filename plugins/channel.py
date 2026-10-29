# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging
from pyrogram import Client, filters
from info import CHANNELS, SDATABASE_CHANNEL
from database.ia_filterdb import save_file

logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio

listen_channels = []
for ch in (list(CHANNELS) + ([SDATABASE_CHANNEL] if SDATABASE_CHANNEL else [])):
    if ch:
        try:
            listen_channels.append(int(ch))
        except (ValueError, TypeError):
            listen_channels.append(str(ch))

@Client.on_message(filters.chat(listen_channels) & media_filter)
async def media(bot, message):
    try:
        media_attr = getattr(message.media, "value", str(message.media)) if message.media else "document"
        media_obj = getattr(message, str(media_attr), None)
        if not media_obj:
            return
        media_obj.caption = message.caption
        media_obj.chat_id = message.chat.id
        media_obj.message_id = message.id
        logger.info(f"[CHANNEL FILE] Received in chat {message.chat.id} msg {message.id}: {getattr(media_obj, 'file_name', 'media')}")
        await save_file(media_obj)
    except Exception as e:
        logger.exception(f"[CHANNEL FILE ERROR] chat={message.chat.id} msg={message.id}: {e}")
