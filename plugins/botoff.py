import asyncio
import logging
from pyrogram import Client, filters, enums
from info import ADMINS
from utils import temp

logger = logging.getLogger(__name__)


def is_bot_active_in_memory(bot_id: int) -> bool:
    """Instant, zero-latency in-memory check for bot power state."""
    if not bot_id:
        return True
    if not hasattr(temp, "BOT_STATUS") or not isinstance(temp.BOT_STATUS, dict):
        return True
    return bool(temp.BOT_STATUS.get(int(bot_id), True))


def get_active_public_bot_id():
    """
    Determines which single bot is currently designated to serve the public.
    Rule:
    1. Bot 1 is primary. If Bot 1 is ON, Bot 1 serves the public.
    2. If Bot 1 is OFF, Bot 2 serves the public (if Bot 2 is ON).
    3. If both are OFF, returns None (maintenance mode).
    """
    b1_id = getattr(temp, "ME", None) or getattr(temp, "ME1", None)
    b2_id = getattr(temp, "ME2", None) or getattr(temp, "CHILD_ME", None)

    if b1_id and is_bot_active_in_memory(b1_id):
        return b1_id

    if b2_id and is_bot_active_in_memory(b2_id):
        return b2_id

    return None


def is_bot_serving_public(bot_id: int) -> bool:
    """Returns True if this specific bot is the active public bot."""
    if not bot_id:
        return True
    active_id = get_active_public_bot_id()
    if active_id is None:
        return False
    return int(bot_id) == int(active_id)


async def is_bot_active(bot_id: int) -> bool:
    """Checks whether the specified bot is ON (True) or OFF (False)."""
    if not bot_id:
        return True
    if not hasattr(temp, "BOT_STATUS") or not isinstance(temp.BOT_STATUS, dict):
        temp.BOT_STATUS = {}
    bid = int(bot_id)
    if bid in temp.BOT_STATUS:
        return temp.BOT_STATUS[bid]
    try:
        from database.users_chats_db import db
        if hasattr(db, "get_bot_status"):
            status = await db.get_bot_status(bid)
            temp.BOT_STATUS[bid] = status
            return status
        return True
    except Exception:
        return True


async def set_bot_active(bot_id: int, is_active: bool):
    """Sets whether the specified bot is ON (True) or OFF (False)."""
    if not hasattr(temp, "BOT_STATUS") or not isinstance(temp.BOT_STATUS, dict):
        temp.BOT_STATUS = {}
    bid = int(bot_id)
    temp.BOT_STATUS[bid] = is_active
    try:
        from database.users_chats_db import db
        if hasattr(db, "set_bot_status"):
            await db.set_bot_status(bid, is_active)
    except Exception as e:
        logger.error(f"[SET BOT STATUS ERROR] {e}")

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
        try:
            b_info = await client.get_me()
            bot_id = b_info.id
        except Exception:
            bot_id = getattr(temp, "ME", None)
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
        f"• Non-admins sending /start or any message will receive the maintenance notice + sticker (auto-deleted in 40s).\n"
        f"• Active public bot is now: <b>{active_mention}</b>\n"
        f"• Use <code>/boton</code> on this bot to turn it back ON.",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["boton", "bot_on"]) & filters.user(ADMINS), group=-10)
async def cmd_boton(client: Client, message):
    """Admin command to turn the receiving bot ON."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        try:
            b_info = await client.get_me()
            bot_id = b_info.id
        except Exception:
            bot_id = getattr(temp, "ME", None)
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
    2. If this receiving bot is turned OFF via /botoff:
       Halt propagation, send maintenance notice + sticker, auto-delete in 40s.
    3. If this receiving bot is ON but in standby mode (other bot is active public bot):
       Halt propagation, send standby redirect notice + sticker, auto-delete in 40s.
    4. Otherwise, allow message to proceed to normal handlers.
    """
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    admins_list = [int(a) for a in ADMINS if str(a).lstrip("-").isdigit()]
    if user_id in admins_list or str(user_id) in [str(a) for a in ADMINS]:
        return  # Admins always pass through!

    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        try:
            b_info = await client.get_me()
            bot_id = b_info.id
        except Exception:
            bot_id = getattr(temp, "ME", None)

    # 1. Direct Power Check: Is THIS receiving bot ON or OFF?
    bot_active = await is_bot_active(bot_id)
    if not bot_active:
        # This bot is turned OFF with /botoff!
        message.stop_propagation()
        notice_text = (
            "⚠️ <b>This bot is currently unavailable due to maintenance.</b>\n\n"
            "<i>Please try again later.</i>\n\n"
            "<i>🕐 This message will be deleted in 40 seconds.</i>"
        )
    elif not is_bot_serving_public(bot_id):
        # This bot is in standby backup mode (other bot is serving public)
        message.stop_propagation()
        active_id = get_active_public_bot_id()
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        notice_text = (
            f"⚠️ <b>This bot is currently in standby backup mode.</b>\n\n"
            f"👉 <b>Please search and get files here:</b> @{active_u}\n\n"
            f"<i>🕐 This message will be deleted in 40 seconds.</i>"
        )
    else:
        # This bot is ON and actively serving the public: proceed!
        return

    to_delete = [message.id]

    # 1. Send maintenance sticker
    try:
        stk = await client.send_sticker(
            chat_id=message.chat.id,
            sticker=MAINTENANCE_STICKER_ID
        )
        if stk:
            to_delete.append(stk.id)
    except Exception as se:
        logger.warning(f"[MAINTENANCE] Sticker send skipped or failed: {se}")

    # 2. Send maintenance notice text
    try:
        txt = await client.send_message(
            chat_id=message.chat.id,
            text=notice_text,
            parse_mode=enums.ParseMode.HTML
        )
        if txt:
            to_delete.append(txt.id)
    except Exception as te:
        logger.warning(f"[MAINTENANCE] Error sending notice text: {te}")

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
    admins_list = [int(a) for a in ADMINS if str(a).lstrip("-").isdigit()]
    if user_id in admins_list or str(user_id) in [str(a) for a in ADMINS]:
        return

    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        try:
            b_info = await client.get_me()
            bot_id = b_info.id
        except Exception:
            bot_id = getattr(temp, "ME", None)

    bot_active = await is_bot_active(bot_id)
    if not bot_active:
        query.stop_propagation()
        try:
            await query.answer("⚠️ This bot is currently unavailable due to maintenance.", show_alert=True)
        except Exception:
            pass
        return

    if not is_bot_serving_public(bot_id):
        query.stop_propagation()
        active_id = get_active_public_bot_id()
        b1_id = getattr(temp, "ME", None)
        active_u = getattr(temp, "U_NAME", "Bot 1") if active_id == b1_id else getattr(temp, "U_NAME2", "Bot 2")
        try:
            await query.answer(f"⚠️ This bot is in standby. Please use @{active_u}.", show_alert=True)
        except Exception:
            pass
        return
