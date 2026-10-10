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


multi_clients = {}
work_loads = {}


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
ChildBot = None

__all__ = [
    "TechVJBot",
    "ChildBot",
    "TechVJXBot",
    "multi_clients",
    "work_loads"
]

