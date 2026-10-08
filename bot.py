# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Clone Code Credit : YT - @Tech_VJ / TG - @VJ_Bots / GitHub - @VJBots

import sys, os, glob, importlib, importlib.util, logging, logging.config, pytz, asyncio
from pathlib import Path

# Prevent creation of __pycache__ folders and .pyc files
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("cinemagoer").setLevel(logging.ERROR)

from pyrogram import Client, idle
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from Script import script 
from datetime import date, datetime 
from aiohttp import web
from plugins import web_server
from plugins.clone import restart_bots

from TechVJ.bot import TechVJBot, ChildBot
from TechVJ.util.keepalive import ping_server
from TechVJ.bot.clients import initialize_clients

print("### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###", flush=True)
TechVJBot.start()
if ChildBot:
    print("### STARTING NORMAL FILTER CHILD BOT (BOT_TOKEN2) ###", flush=True)
    try:
        ChildBot.start()
    except Exception as ce:
        print(f"### CHILD BOT SYNC START NOTICE: {ce} ###", flush=True)
loop = asyncio.get_event_loop()


async def start():
    print('\n')
    print('### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###', flush=True)
    logging.warning('### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###')
    print('Initializing Your Bot')
    bot_info = await TechVJBot.get_me()
    await initialize_clients()
    if ON_HEROKU:
        asyncio.create_task(ping_server())
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
    me = await TechVJBot.get_me()
    temp.BOT = TechVJBot
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    logging.info("MAIN BOT: Super Filter handlers loaded.")
    if ChildBot:
        try:
            if not getattr(ChildBot, "is_connected", False):
                print("### CONNECTING CHILD BOT ASYNC ###", flush=True)
                await ChildBot.start()
            from child_plugins import register_child_handlers
            register_child_handlers(ChildBot)

            child_me = await ChildBot.get_me()
            temp.CHILD_BOT = ChildBot
            temp.CHILD_ME = child_me.id
            temp.CHILD_U_NAME = child_me.username
            temp.CHILD_B_NAME = child_me.first_name

            # Inspect actual registered handlers
            handler_count = 0
            handler_names = []
            if hasattr(ChildBot, "dispatcher") and hasattr(ChildBot.dispatcher, "groups"):
                for g_id, g_handlers in ChildBot.dispatcher.groups.items():
                    for h in g_handlers:
                        handler_count += 1
                        fn_name = getattr(getattr(h, "callback", None), "__name__", str(h))
                        handler_names.append(fn_name)

            logging.info(f"CHILD BOT NORMAL HANDLERS REGISTERED: {handler_count} on @{child_me.username} ({', '.join(handler_names)})")
            print(f"### CHILD BOT RUNNING AS @{child_me.username} (NORMAL HANDLERS: {handler_count}) ###", flush=True)
        except Exception as ce:
            logging.error(f"Failed to initialize Child Bot: {ce}", exc_info=True)
            print(f"### FAILED TO INITIALIZE CHILD BOT: {ce} ###", flush=True)


    try:
        from plugins.series import start_cleanup_schedulers
        start_cleanup_schedulers(TechVJBot)
        from utils import start_telegram_watchdog
        start_telegram_watchdog(TechVJBot)
        from database.series_db import backfill_super_movie_normalized_names
        asyncio.create_task(backfill_super_movie_normalized_names())
    except Exception as e:
        logging.warning(f"Failed to start cleanup schedulers or migrations: {e}")
    logging.info(script.LOGO)
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    try:
        await TechVJBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
    except:
        print("Make Your Bot Admin In Log Channel With Full Rights")
    for ch in CHANNELS:
        try:
            k = await TechVJBot.send_message(chat_id=ch, text="**Bot Restarted**")
            await k.delete()
        except:
            print("Make Your Bot Admin In File Channels With Full Rights")
    try:
        k = await TechVJBot.send_message(chat_id=AUTH_CHANNEL, text="**Bot Restarted**")
        await k.delete()
    except:
        print("Make Your Bot Admin In Force Subscribe Channel With Full Rights")
    if CLONE_MODE == True:
        print("Restarting All Clone Bots.......")
        await restart_bots()
        print("Restarted All Clone Bots.")
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, int(PORT)).start()
    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
