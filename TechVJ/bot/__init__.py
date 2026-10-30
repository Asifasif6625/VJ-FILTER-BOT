# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os, asyncio
from os import environ
from pyrogram import Client, types
from pyrogram.errors import FloodWait
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from aiohttp import web


multi_clients = {}
work_loads = {}


class TechVJXBot(Client):

    def __init__(self, name=SESSION, bot_token=BOT_TOKEN, in_memory=False):
        super().__init__(
            name=name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=bot_token,
            workers=150,
            plugins={"root": "plugins"},
            sleep_threshold=5,
            in_memory=in_memory,
        )

    async def set_self(self):
        temp.BOT = self
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int = 100000,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        batch_size = 200
        while current <= limit:
            new_diff = min(batch_size, (limit - current) + 1)
            if new_diff <= 0:
                break
            batch_ids = list(range(current, current + new_diff))
            current += new_diff
            try:
                messages = await self.get_messages(chat_id, batch_ids)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                messages = await self.get_messages(chat_id, batch_ids)
            except Exception:
                continue
            if not messages:
                continue
            for message in messages:
                yield message
      
TechVJBot = TechVJXBot(name=SESSION, bot_token=BOT_TOKEN)
Bot2 = None
if BOT_TOKEN2:
    Bot2 = TechVJXBot(name=CHILD_SESSION, bot_token=BOT_TOKEN2)
ChildBot = Bot2

__all__ = [
    "TechVJBot",
    "Bot2",
    "ChildBot",
    "TechVJXBot",
    "multi_clients",
    "work_loads"
]
