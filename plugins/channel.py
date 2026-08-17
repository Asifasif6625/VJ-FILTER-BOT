# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client, filters
from info import CHANNELS, SDATABASE_CHANNEL
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video

listen_channels = list(CHANNELS)
if SDATABASE_CHANNEL and SDATABASE_CHANNEL not in listen_channels:
    listen_channels.append(SDATABASE_CHANNEL)

@Client.on_message(filters.chat(listen_channels) & media_filter)
async def media(bot, message):
    media = getattr(message, message.media.value, None)
    media.caption = message.caption
    await save_file(media)
