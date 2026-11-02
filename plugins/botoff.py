import os
import asyncio
import logging
from pyrogram import Client, filters, enums
from info import ADMINS
from utils import (
    temp,
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
    curr_bot_id = getattr(getattr(client, "me", None), "id", None) or getattr(temp, "ME", None)
    curr_u = getattr(getattr(client, "me", None), "username", "Bot")

    args = message.text.split()[1:] if message.text else []
    target = args[0].lower() if args else None

    if target in ["all", "both"]:
        if curr_bot_id:
            await set_bot_active(int(curr_bot_id), False)
        for b in get_all_delivery_bots():
            if getattr(b, "me", None):
                await set_bot_active(b.me.id, False)
        logger.info(f"[BOT POWER] All bots turned OFF by admin {message.from_user.id}")
        return await message.reply_text(
            "🔴 <b>All Bots are now turned OFF.</b>\n\n"
            "• Maintenance mode is ACTIVE for all non-admin users.\n"
            "• Admins can continue to use bots at any time.\n"
            "• Use <code>/boton</code> or <code>/boton all</code> to turn ON.",
            parse_mode=enums.ParseMode.HTML
        )

    await set_bot_active(int(curr_bot_id), False)
    logger.info(f"[BOT POWER] Bot @{curr_u} ({curr_bot_id}) turned OFF by admin {message.from_user.id}")

    await message.reply_text(
        f"🔴 <b>Bot @{curr_u} is now turned OFF.</b>\n\n"
        f"• This bot will now <b>ONLY</b> respond to Admins.\n"
        f"• Non-admins sending /start or searching movies will receive the maintenance notice + sticker (auto-deleted in 40s).\n"
        f"• Use <code>/boton</code> on this bot to turn it back ON.",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["boton", "bot_on"]) & filters.user(ADMINS), group=-10)
async def cmd_boton(client: Client, message):
    """
    Admin command to turn bot(s) ON.
    Usage:
    /boton       -> turns ON this receiving bot
    /boton all   -> turns ON all connected bots
    """
    curr_bot_id = getattr(getattr(client, "me", None), "id", None) or getattr(temp, "ME", None)
    curr_u = getattr(getattr(client, "me", None), "username", "Bot")

    args = message.text.split()[1:] if message.text else []
    target = args[0].lower() if args else None

    if target in ["all", "both"]:
        if curr_bot_id:
            await set_bot_active(int(curr_bot_id), True)
        for b in get_all_delivery_bots():
            if getattr(b, "me", None):
                await set_bot_active(b.me.id, True)
        logger.info(f"[BOT POWER] All bots turned ON by admin {message.from_user.id}")
        return await message.reply_text(
            "🟢 <b>All Bots are now turned ON.</b>\n\n"
            "• Public search traffic is active on delivery bots.",
            parse_mode=enums.ParseMode.HTML
        )

    await set_bot_active(int(curr_bot_id), True)
    logger.info(f"[BOT POWER] Bot @{curr_u} ({curr_bot_id}) turned ON by admin {message.from_user.id}")

    await message.reply_text(
        f"🟢 <b>Bot @{curr_u} is now turned ON.</b>",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["botstatus", "bot_status"]) & filters.user(ADMINS), group=-10)
async def cmd_botstatus(client: Client, message):
    """Admin command to check status of GDBOT and all connected delivery bots."""
    gdbot_id = getattr(temp, "GDBOT_ID", None) or getattr(temp, "ME", None)
    gdbot_u = getattr(temp, "U_NAME", "GDBOT")
    gdbot_on = is_bot_active_in_memory(int(gdbot_id)) if gdbot_id else True

    delivery_bots = get_all_delivery_bots()
    del_lines = ""
    if not delivery_bots:
        del_lines = "<i>No delivery bots connected yet. Use /mybot to add.</i>"
    else:
        for b in delivery_bots:
            u = getattr(getattr(b, "me", None), "username", "DeliveryBot")
            bid = getattr(getattr(b, "me", None), "id", 0)
            b_on = is_bot_active_in_memory(bid)
            del_lines += f"• <b>@{u}:</b> {'🟢 ON' if b_on else '🔴 OFF'} (ID: <code>{bid}</code>)\n"

    status_text = (
        f"🤖 <b>Bot System Status:</b>\n\n"
        f"🛡 <b>GDBOT (@{gdbot_u}):</b> {'🟢 ON' if gdbot_on else '🔴 OFF'} (Admin Management)\n\n"
        f"📦 <b>Delivery Bots ({len(delivery_bots)}/2):</b>\n"
        f"{del_lines}\n"
        f"<b>Management:</b>\n"
        f"• Use <code>/mybot</code> to add, remove, and remap delivery bots\n"
        f"• Use <code>/botoff</code> or <code>/boton</code> to toggle power"
    )
    await message.reply_text(status_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(group=-100)
async def maintenance_message_gate(client: Client, message):
    """
    High-priority message gate:
    1. Admins are exempt: can always use all bots.
    2. GDBOT is Admin-Only: redirects non-admins to the active Delivery Bot.
    3. Delivery Bots: serve public searches unless turned OFF via /botoff.
    """
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    admins_list = [int(a) for a in ADMINS if str(a).lstrip("-").isdigit()]
    if user_id in admins_list or str(user_id) in [str(a) for a in ADMINS]:
        return  # Admins always pass through!

    bot_id = getattr(getattr(client, "me", None), "id", None) or getattr(temp, "ME", None)
    if bot_id:
        bot_id = int(bot_id)

    gdbot_id = getattr(temp, "GDBOT_ID", None) or getattr(temp, "ME", None)

    # 1. Check if receiving client is GDBOT (Admin-Only Main Bot)
    if gdbot_id and bot_id == int(gdbot_id):
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
        bot_active = await is_bot_active(bot_id)
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
            # Bot is ON. Check if this bot is the single designated public bot!
            if not is_bot_serving_public(bot_id):
                active_id = get_active_public_bot_id()
                alt_bot = temp.DELIVERY_BOTS.get(active_id) if (active_id and hasattr(temp, "DELIVERY_BOTS")) else None
                alt_u = getattr(getattr(alt_bot, "me", None), "username", "DeliveryBot") if alt_bot else "our main bot"
                notice_text = (
                    "⚠️ <b>This bot is currently on standby.</b>\n\n"
                    f"👉 <b>Please search and download movies from our active bot:</b>\n"
                    f"@{alt_u}\n\n"
                    "<i>🕐 This message will be deleted in 40 seconds.</i>"
                )
            else:
                # This bot is ON and is the designated active public bot! Proceed!
                return

    to_delete = [message.id]

    # 1. Send notice text FIRST (guaranteed delivery)
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

    # 2. Send maintenance sticker SECOND (isolated try/except)
    try:
        stk = await client.send_sticker(
            chat_id=message.chat.id,
            sticker=MAINTENANCE_STICKER_ID
        )
        if stk:
            to_delete.append(stk.id)
    except Exception as se:
        logger.warning(f"[MAINTENANCE] Sticker send skipped or failed: {se}")

    # 3. Schedule 40-second auto-deletion for user message + notice + sticker
    asyncio.create_task(
        _auto_delete_maintenance_bundle(
            client=client,
            chat_id=message.chat.id,
            message_ids=to_delete,
            delay=40
        )
    )

    logger.info(f"[MAINTENANCE GATE] Redirected non-admin {user_id} on bot {bot_id}. Notice sent, scheduled 40s delete.")

    # 4. Stop propagation at the very end
    message.stop_propagation()


@Client.on_callback_query(group=-100)
async def maintenance_callback_gate(client: Client, query):
    """
    High-priority callback gate:
    Prevents non-admins from triggering callbacks on inactive bots or GDBOT.
    """
    user_id = query.from_user.id if query.from_user else 0
    admins_list = [int(a) for a in ADMINS if str(a).lstrip("-").isdigit()]
    if user_id in admins_list or str(user_id) in [str(a) for a in ADMINS]:
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
