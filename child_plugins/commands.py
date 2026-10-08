import time
import datetime
import html
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from info import ADMINS, BOT_TOKEN2
from database.users_chats_db import db
from utils import broadcast_messages, broadcast_messages_group, temp

@Client.on_message(filters.command("start") & filters.incoming)
async def child_start_handler(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    if len(message.command) > 1:
        data = message.command[1]
        
        # 1. Normal Filter Deeplink Flow (/start norm_...)
        if data.startswith("norm_"):
            norm_key = data.split("_", 1)[1]
            from plugins.pm_filter import process_normal_filter_deeplink
            await process_normal_filter_deeplink(client, message, norm_key, user_id=message.from_user.id)
            return

        # 2. Getme Normal Search Deeplink (/start getme_...)
        if data.startswith("getme_"):
            search_query = data.split("getme_", 1)[1].replace("_", " ").strip()
            if search_query:
                from database.ia_filterdb import get_search_results
                from plugins.pm_filter import render_normal_grouped_results
                files, _, _ = await get_search_results(message.chat.id, search_query.lower(), max_results=100, offset=0, filter=True)
                if files:
                    rendered = await render_normal_grouped_results(client=client, message=message, query_text=search_query, files=files)
                    if rendered:
                        return
                await message.reply_text(f"<b>No files found in database for '<i>{html.escape(search_query)}</i>'</b>", parse_mode=enums.ParseMode.HTML)
            return

    # Plain /start welcome message
    mention = message.from_user.mention if message.from_user else "User"
    welcome_text = (
        f"<b>👋 Hello {mention},</b>\n\n"
        "Welcome to the <b>Normal Filter Bot</b>.\n\n"
        "Search for any movie or series name in this chat or in connected groups to find available files."
    )
    await message.reply_text(welcome_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command("about") & filters.incoming)
async def child_about_handler(client: Client, message: Message):
    about_text = (
        "<b>🤖 Normal Filter Bot</b>\n\n"
        "This bot is dedicated to <b>Normal / Legacy Movie & Series Filter</b> searches with instant file delivery.\n\n"
        "<b>Powered by:</b> @KingVJ01"
    )
    await message.reply_text(about_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command("help") & filters.incoming)
async def child_help_handler(client: Client, message: Message):
    help_text = (
        "<b>📖 How to Search:</b>\n\n"
        "1. Send the title of the movie or series in this chat or in connected groups.\n"
        "2. Select your desired version from the file list buttons.\n"
        "3. Open the bot and click <b>⌯⌲ Get All File</b> to receive your files."
    )
    await message.reply_text(help_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def child_pm_broadcast(client: Client, message: Message):
    b_msg = await client.ask(chat_id=message.from_user.id, text="Now Send Me Your Broadcast Message")
    try:
        users = await db.get_all_users()
        sts = await message.reply_text('Broadcasting your messages...')
        start_time = time.time()
        total_users = await db.total_users_count()
        done = 0
        blocked = 0
        deleted = 0
        failed = 0
        success = 0
        async for user in users:
            if 'id' in user:
                pti, sh = await broadcast_messages(int(user['id']), b_msg)
                if pti:
                    success += 1
                elif pti == False:
                    if sh == "Blocked":
                        blocked += 1
                    elif sh == "Deleted":
                        deleted += 1
                    elif sh == "Error":
                        failed += 1
                done += 1
                if not done % 20:
                    await sts.edit(f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}")    
            else:
                done += 1
                failed += 1
                if not done % 20:
                    await sts.edit(f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}")    
    
        time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
        await sts.edit(f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}")
    except Exception as e:
        print(f"Child Broadcast Error: {e}")


@Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS))
async def child_broadcast_group(client: Client, message: Message):
    b_msg = await client.ask(chat_id=message.from_user.id, text="Now Send Me Your Broadcast Message")
    groups = await db.get_all_chats()
    sts = await message.reply_text('Broadcasting your messages To Groups...')
    start_time = time.time()
    total_groups = await db.total_chat_count()
    done = 0
    failed = 0
    success = 0
    async for group in groups:
        pti, sh = await broadcast_messages_group(int(group['id']), b_msg)
        if pti:
            success += 1
        elif sh == "Error":
            failed += 1
        done += 1
        if not done % 20:
            await sts.edit(f"Broadcast in progress:\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nSuccess: {success}")    
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nSuccess: {success}")
