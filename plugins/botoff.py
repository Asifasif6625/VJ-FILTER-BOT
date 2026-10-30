import asyncio
import logging
from pyrogram import Client, filters, enums
from info import ADMINS
from utils import (
    is_bot_active,
    set_bot_active,
    is_bot_active_in_memory,
    is_bot_serving_public,
    get_active_public_bot_id,
    temp
)

logger = logging.getLogger(__name__)

MAINTENANCE_STICKER_ID = "CAACAgIAAxkBAAESIaBq5My_ixto286jugnjHphoYUbZNAACyxQAAt2wUUlMYGw0MqQdYT0E"


async def _auto_delete_maintenance_bundle(client: Client, chat_id: int, message_ids: list[int], delay: int = 40):
    """Deletes the maintenance notice, sticker, and the triggering user message after delay seconds."""
    await asyncio.sleep(delay)
    valid_ids = [m for m in message_ids if m]
    if not valid_ids:
        return
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=valid_ids)
    except Exception as e:
        logger.debug(f"[MAINTENANCE DELETE] Could not delete messages {valid_ids} in chat {chat_id}: {e}")


@Client.on_message(filters.command(["botoff", "bot_off"]) & filters.user(ADMINS), group=-10)
async def cmd_botoff(client: Client, message):
    """Admin command to turn the receiving bot OFF."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        b_info = await client.get_me()
        bot_id = b_info.id
    bot_username = getattr(getattr(client, "me", None), "username", "Bot")
    
    await set_bot_active(bot_id, False)
    logger.info(f"[BOT POWER] Bot @{bot_username} ({bot_id}) turned OFF by admin {message.from_user.id}")

    active_id = get_active_public_bot_id()
    active_mention = "None (All Bots OFF)"
    if active_id:
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        active_mention = f"@{active_u}"
    
    await message.reply_text(
        f"🔴 <b>Bot @{bot_username} is now turned OFF.</b>\n\n"
        f"• This bot will now <b>ONLY</b> respond to Admins.\n"
        f"• Active public bot is now: <b>{active_mention}</b>\n"
        f"• Use <code>/boton</code> on this bot to turn it back ON.",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["boton", "bot_on"]) & filters.user(ADMINS), group=-10)
async def cmd_boton(client: Client, message):
    """Admin command to turn the receiving bot ON."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        b_info = await client.get_me()
        bot_id = b_info.id
    bot_username = getattr(getattr(client, "me", None), "username", "Bot")
    
    await set_bot_active(bot_id, True)
    logger.info(f"[BOT POWER] Bot @{bot_username} ({bot_id}) turned ON by admin {message.from_user.id}")

    active_id = get_active_public_bot_id()
    active_mention = f"@{bot_username}"
    if active_id:
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        active_mention = f"@{active_u}"
    
    await message.reply_text(
        f"🟢 <b>Bot @{bot_username} is now turned ON.</b>\n\n"
        f"• Active public bot is now: <b>{active_mention}</b>",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["botstatus", "bot_status"]) & filters.user(ADMINS), group=-10)
async def cmd_botstatus(client: Client, message):
    """Admin command to check status of both bots and public designation."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    curr_u = getattr(getattr(client, "me", None), "username", "ThisBot")
    
    b1_id = getattr(temp, "ME", None)
    b2_id = getattr(temp, "ME2", None) or getattr(temp, "CHILD_ME", None)
    
    b1_on = is_bot_active_in_memory(b1_id) if b1_id else None
    b2_on = is_bot_active_in_memory(b2_id) if b2_id else None
    
    b1_u = getattr(temp, "U_NAME", "Bot 1")
    b2_u = getattr(temp, "U_NAME2", "Bot 2") or getattr(temp, "CHILD_U_NAME", "Bot 2")
    
    active_id = get_active_public_bot_id()
    if active_id == b1_id:
        active_desc = f"@{b1_u} (Primary Active)"
    elif active_id == b2_id:
        active_desc = f"@{b2_u} (Failover Active)"
    else:
        active_desc = "🔴 None (All bots OFF - Maintenance Mode)"
    
    status_text = (
        f"🤖 <b>Dual-Bot System Status:</b>\n\n"
        f"• <b>Bot 1 (@{b1_u}):</b> {'🟢 ON' if b1_on else ('🔴 OFF' if b1_on is False else 'Not Connected')}\n"
        f"• <b>Bot 2 (@{b2_u}):</b> {'🟢 ON' if b2_on else ('🔴 OFF' if b2_on is False else 'Not Connected')}\n\n"
        f"🌐 <b>Current Public Bot:</b> <b>{active_desc}</b>\n\n"
        f"<i>Admins can use both bots at any time. Non-admin users are automatically served by the single active public bot.</i>"
    )
    await message.reply_text(status_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(group=-100)
async def maintenance_message_gate(client: Client, message):
    """
    High-priority message gate:
    1. Admins are exempt: can always use both bots.
    2. Non-admins are ONLY served by the designated active public bot.
    3. If this bot is not serving the public, halts message propagation,
       sends notification + sticker, and auto-deletes in 40 seconds.
    """
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if user_id in ADMINS:
        return  # Admins always pass through!

    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        bot_id = getattr(temp, "ME", None)

    # Check if this bot is currently designated to serve the public
    if is_bot_serving_public(bot_id):
        return  # This bot is active for public: proceed to normal handlers!

    # This bot is NOT serving the public: halt update propagation
    message.stop_propagation()

    # Determine message text based on situation
    active_id = get_active_public_bot_id()
    if active_id:
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        notice_text = (
            f"⚠️ <b>This bot is currently in standby backup mode.</b>\n\n"
            f"👉 <b>Please search and get files here:</b> @{active_u}\n\n"
            f"<i>🕐 This message will be deleted in 40 seconds.</i>"
        )
    else:
        notice_text = (
            "⚠️ <b>This bot is currently unavailable due to maintenance.</b>\n\n"
            "<i>Please try again later.</i>\n\n"
            "<i>🕐 This message will be deleted in 40 seconds.</i>"
        )

    to_delete = [message.id]

    # 1. Send notice text first to guarantee delivery
    try:
        txt = await message.reply_text(
            text=notice_text,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )
        if txt:
            to_delete.append(txt.id)
    except Exception as te:
        logger.warning(f"[MAINTENANCE] Error sending notice text: {te}")

    # 2. Try sending maintenance sticker (catch any bot-specific sticker rejection)
    try:
        stk = await message.reply_sticker(
            sticker=MAINTENANCE_STICKER_ID,
            reply_to_message_id=message.id
        )
        if stk:
            to_delete.append(stk.id)
    except Exception as se:
        logger.debug(f"[MAINTENANCE] Sticker send skipped: {se}")

    # 3. Schedule 40-second auto-deletion
    asyncio.create_task(
        _auto_delete_maintenance_bundle(
            client=client,
            chat_id=message.chat.id,
            message_ids=to_delete,
            delay=40
        )
    )


@Client.on_callback_query(group=-100)
async def maintenance_callback_gate(client: Client, query):
    """
    High-priority callback gate:
    Alerts non-admins if they click a button on a bot that is not active.
    """
    user_id = query.from_user.id if query.from_user else 0
    if user_id in ADMINS:
        return

    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        bot_id = getattr(temp, "ME", None)

    if is_bot_serving_public(bot_id):
        return

    query.stop_propagation()
    active_id = get_active_public_bot_id()
    if active_id:
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        alert_msg = f"⚠️ This bot is in standby. Please use @{active_u}."
    else:
        alert_msg = "⚠️ This bot is currently unavailable due to maintenance."

    try:
        await query.answer(alert_msg, show_alert=True)
    except Exception:
        pass
