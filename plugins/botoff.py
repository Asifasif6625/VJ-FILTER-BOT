import os
import asyncio
import logging
from pyrogram import Client, filters, enums
from info import ADMINS
from utils import (
    temp,
    is_gdbot_client,
    get_all_delivery_bots,
    get_active_delivery_bot,
    get_delivery_bot_username,
    is_bot_active_in_memory,
    is_bot_active,
    set_bot_active,
    get_active_public_bot_id,
    is_bot_serving_public,
)

logger = logging.getLogger(__name__)

MAINTENANCE_STICKER_ID = "CAACAgIAAxkBAAESIaBq5My_ixto286jugnjHphoYUbZNAACyxQAAt2wUUlMYGw0MqQdYT0E"


def _check_env_bot_off(bot_id: int) -> bool:
    """Checks if environment variables have explicitly forced this bot OFF."""
    try:
        if os.environ.get("BOT_OFF", "").strip().lower() in ("true", "1", "yes"):
            return True
        b_id = getattr(temp, "ME", None) or getattr(temp, "GDBOT_ID", None)
        if b_id and int(bot_id) == int(b_id) and os.environ.get("GDBOT_OFF", "").strip().lower() in ("true", "1", "yes"):
            return True
    except Exception:
        pass
    return False


def is_bot_active_in_memory(bot_id: int) -> bool:
    """Instant, zero-latency in-memory check for bot power state."""
    if not bot_id:
        return True
    if not hasattr(temp, "BOT_STATUS") or not isinstance(temp.BOT_STATUS, dict):
        return not _check_env_bot_off(bot_id)
    bid = int(bot_id)
    if bid in temp.BOT_STATUS:
        return bool(temp.BOT_STATUS[bid])
    if _check_env_bot_off(bid):
        return False
    return True


async def is_bot_active(bot_id: int) -> bool:
    """Checks whether the specified bot is ON (True) or OFF (False)."""
    if not bot_id:
        return True
    if not hasattr(temp, "BOT_STATUS") or not isinstance(temp.BOT_STATUS, dict):
        temp.BOT_STATUS = {}
    bid = int(bot_id)
    if bid in temp.BOT_STATUS:
        return temp.BOT_STATUS[bid]

    if _check_env_bot_off(bid):
        temp.BOT_STATUS[bid] = False
        return False

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


async def _auto_delete_maintenance_bundle(client: Client, chat_id: int, message_ids: list[int], delay: int = 40):
    """Deletes the maintenance notice, sticker, and the triggering user message after delay seconds."""
    await asyncio.sleep(delay)
    valid_ids = [int(m) for m in message_ids if m]
    if not valid_ids:
        return
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=valid_ids)
    except Exception as e:
        logger.debug(f"[MAINTENANCE DELETE] Batch delete failed for {valid_ids} in chat {chat_id}: {e}")
        for mid in valid_ids:
            try:
                await client.delete_messages(chat_id=chat_id, message_ids=mid)
            except Exception:
                pass


@Client.on_message(filters.command(["botoff", "bot_off"]) & filters.user(ADMINS), group=-10)
async def cmd_botoff(client: Client, message):
    """
    Admin command to turn bot(s) OFF.
    Usage:
    /botoff       -> turns OFF this receiving bot
    /botoff all   -> turns OFF all connected bots
    """
    curr_# 1. Check if receiving client is GDBOT (Admin-Only Main Bot)
    if is_gdbot_client(client):
        # Non-admin messaged GDBOT -> Redirect to active Delivery Bot!
        del_u = get_delivery_bot_username()
        gdbot_uname = getattr(temp, "U_NAME", "")
        if del_u and del_u.lower() != gdbot_uname.lower():
            notice_text = (
                f"⚠️ <b>This bot is for Admin Management & Database operations.</b>\n\n"
                f"👉 <b>Please search and download movies from our Delivery Bot:</b>\n"
                f"@{del_u}\n\n"
                f"<i>🕐 This message will be deleted in 40 seconds.</i>"
            )
        else:
            notice_text = (
                "⚠️ <b>This bot is currently unavailable due to maintenance.</b>\n\n"
                "<i>Please try again later.</i>\n\n"
                "<i>🕐 This message will be deleted in 40 seconds.</i>"
            )
    else:
        # 2. Receiving client is a Delivery Bot!
        bot_id = getattr(getattr(client, "me", None), "id", None)
        bot_active = await is_bot_active(bot_id) if bot_id else True
        if not bot_active:
            active_id = get_active_public_bot_id()
            alt_bot = temp.DELIVERY_BOTS.get(active_id) if (active_id and hasattr(temp, "DELIVERY_BOTS")) else None
            alt_u = getattr(getattr(alt_bot, "me", None), "username", None) if alt_bot else None
            if alt_u and active_id != bot_id:
                notice_text = (
                    "⚠️ <b>This bot is currently under maintenance.</b>\n\n"
                    f"👉 <b>Please search and download movies from our active bot:</b>\n"
                    f"@{alt_u}\n\n"
                    "<i>🕐 This message will be deleted in 40 seconds.</i>"
                )
            else:
                notice_text = (
                    "⚠️ <b>This bot is currently unavailable due to maintenance.</b>\n\n"
                    "<i>Please try again later.</i>\n\n"
                    "<i>🕐 This message will be deleted in 40 seconds.</i>"
                )
        else:
            # Bot is ON! Allow search/filter traffic to pass directly!
            return

    if is_gdbot_client(client):
        del_u = get_delivery_bot_username()
        try:
            await query.answer(f"⚠️ This bot is for admins only. Please use @{del_u}.", show_alert=True)
        except Exception:
            pass
        query.stop_propagation()
        return

    bot_id = getattr(getattr(client, "me", None), "id", None)
    bot_active = await is_bot_active(bot_id) if bot_id else True
    if not bot_active:
        active_id = get_active_public_bot_id()
        alt_bot = temp.DELIVERY_BOTS.get(active_id) if (active_id and hasattr(temp, "DELIVERY_BOTS")) else None
        alt_u = getattr(getattr(alt_bot, "me", None), "username", None) if alt_bot else None
        msg = f"⚠️ Under maintenance. Please use @{alt_u}." if (alt_u and active_id != bot_id) else "⚠️ Bot under maintenance."
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        query.stop_propagation()
        return

    return

    bot_id = getattr(getattr(client, "me", None), "id", None) or getattr(temp, "ME", None)
    if bot_id:
        bot_id = int(bot_id)

    gdbot_id = getattr(temp, "GDBOT_ID", None) or getattr(temp, "ME", None)

    if gdbot_id and bot_id == int(gdbot_id):
        del_u = get_delivery_bot_username()
        try:
            await query.answer(f"⚠️ This bot is for admins only. Please use @{del_u}.", show_alert=True)
        except Exception:
            pass
        query.stop_propagation()
        return

    bot_active = await is_bot_active(bot_id)
    if not bot_active:
        active_id = get_active_public_bot_id()
        alt_bot = temp.DELIVERY_BOTS.get(active_id) if (active_id and hasattr(temp, "DELIVERY_BOTS")) else None
        alt_u = getattr(getattr(alt_bot, "me", None), "username", None) if alt_bot else None
        msg = f"⚠️ Under maintenance. Please use @{alt_u}." if (alt_u and active_id != bot_id) else "⚠️ Bot under maintenance."
        try:
            await query.answer(msg, show_alert=True)
        except Exception:
            pass
        query.stop_propagation()
        return

    if not is_bot_serving_public(bot_id):
        active_id = get_active_public_bot_id()
        alt_bot = temp.DELIVERY_BOTS.get(active_id) if (active_id and hasattr(temp, "DELIVERY_BOTS")) else None
        alt_u = getattr(getattr(alt_bot, "me", None), "username", "DeliveryBot") if alt_bot else "active bot"
        try:
            await query.answer(f"⚠️ This bot is on standby. Please use @{alt_u}.", show_alert=True)
        except Exception:
            pass
        query.stop_propagation()
        return
