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

from TechVJ.bot import TechVJBot
from TechVJ.util.keepalive import ping_server
from TechVJ.bot.clients import initialize_clients

print("### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###", flush=True)
TechVJBot.start()
loop = asyncio.get_event_loop()


async def start():
    # Start web server immediately so Koyeb/Render health check passes without waiting for Telegram/DB
    try:
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, int(PORT)).start()
        logging.info(f"Web server started immediately on {bind_address}:{PORT}")
    except Exception as w_err:
        logging.warning(f"Failed to start web server upfront: {w_err}")

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
    temp.MAIN_BOT = TechVJBot
    temp.GDBOT = TechVJBot
    temp.ME = me.id
    temp.GDBOT_ID = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    try:
        from plugins.botoff import is_bot_active
        temp.BOT_STATUS[me.id] = await is_bot_active(me.id)
    except Exception:
        temp.BOT_STATUS[me.id] = True
    logging.info(f"GDBOT (Main Management Bot): Loaded @{me.username} ({me.id}).")

    # Start and restore dynamic Delivery Bots from MongoDB (Max 2 Delivery Bots)
    try:
        from utils import restart_all_delivery_bots
        await restart_all_delivery_bots()
    except Exception as e:
        logging.error(f"Error restoring delivery bots: {e}", exc_info=True)


    try:
        from plugins.series import start_cleanup_schedulers
        start_cleanup_schedulers(TechVJBot)
        from utils import start_telegram_watchdog
        start_telegram_watchdog(TechVJBot)
        from database.series_db import backfill_super_movie_normalized_names, load_super_button_emojis_cache, load_distribution_channel_cache, load_super_filter_cache
        asyncio.create_task(backfill_super_movie_normalized_names())
        asyncio.create_task(load_super_button_emojis_cache())
        asyncio.create_task(load_distribution_channel_cache())
        asyncio.create_task(load_super_filter_cache())
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
    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
