# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
from os import environ
from pyrogram import Client, types
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from aiohttp import web


class TechVJXBot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=150,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def set_self(self):
        temp.BOT = self
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1
      
TechVJBot = TechVJXBot()

class TechVJChildBot(Client):

    def __init__(self, bot_token=None):
        raw_token = bot_token or environ.get('BOT_TOKEN2', globals().get('BOT_TOKEN2', '')) or ""
        token2 = str(raw_token).strip().strip('"').strip("'")
        sess_name = (environ.get('CHILD_SESSION', globals().get('CHILD_SESSION', 'TechVJChildBot')) or "TechVJChildBot").strip()
        super().__init__(
            name=sess_name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token2,
            workers=100,
            plugins={"root": "child_plugins"},
            sleep_threshold=5,
        )

# ChildBot instance initialized when BOT_TOKEN2 is present
_bot_token2 = (environ.get('BOT_TOKEN2', globals().get('BOT_TOKEN2', '')) or "").strip().strip('"').strip("'")
ChildBot = TechVJChildBot(bot_token=_bot_token2) if _bot_token2 else None


multi_clients = {}
work_loads = {}

__all__ = [
    "TechVJBot",
    "ChildBot",
    "TechVJXBot",
    "TechVJChildBot",
    "multi_clients",
    "work_loads"
]

