import asyncio
import logging
from pyrogram import Client, filters, enums
from info import ADMINS
from utils import is_bot_active, set_bot_active, temp

logger = logging.getLogger(__name__)

MAINTENANCE_STICKER_ID = "CAACAgIAAxkBAAESIaBq5My_ixto286jugnjHphoYUbZNAACyxQAAt2wUUlMYGw0MqQdYT0E"
MAINTENANCE_TEXT = (
    "⚠️ <b>This bot is currently unavailable due to maintenance.</b>\n\n"
    "<i>Please try again later or use our backup bot.</i>"
)


async def _auto_delete_maintenance_bundle(client: Client, chat_id: int, message_ids: list[int], delay: int = 40):
    """Deletes the maintenance notices and the triggering user message after delay seconds."""
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
        bot_info = await client.get_me()
        bot_id = bot_info.id
    bot_username = getattr(getattr(client, "me", None), "username", "Bot")
    
    await set_bot_active(bot_id, False)
    logger.info(f"[BOT POWER] Bot @{bot_username} ({bot_id}) turned OFF by admin {message.from_user.id}")
    
    await message.reply_text(
        f"🔴 <b>Bot @{bot_username} is now turned OFF.</b>\n\n"
        f"• The bot will now <b>ONLY</b> respond to Admins.\n"
        f"• All other users will receive the maintenance sticker and notice (auto-deleting in 40s).\n"
        f"• Use <code>/boton</code> to turn this bot back ON at any time.",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["boton", "bot_on"]) & filters.user(ADMINS), group=-10)
async def cmd_boton(client: Client, message):
    """Admin command to turn the receiving bot ON."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        bot_info = await client.get_me()
        bot_id = bot_info.id
    bot_username = getattr(getattr(client, "me", None), "username", "Bot")
    
    await set_bot_active(bot_id, True)
    logger.info(f"[BOT POWER] Bot @{bot_username} ({bot_id}) turned ON by admin {message.from_user.id}")
    
    await message.reply_text(
        f"🟢 <b>Bot @{bot_username} is now turned ON.</b>\n\n"
        f"• The bot is now fully active and responding to all users normally.",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["botstatus", "bot_status"]) & filters.user(ADMINS), group=-10)
async def cmd_botstatus(client: Client, message):
    """Admin command to check status of current bot and connected bots."""
    bot_id = getattr(getattr(client, "me", None), "id", None)
    curr_active = await is_bot_active(bot_id)
    curr_u = getattr(getattr(client, "me", None), "username", "ThisBot")
    
    b1_id = getattr(temp, "ME", None)
    b2_id = getattr(temp, "ME2", None) or getattr(temp, "CHILD_ME", None)
    
    b1_status = await is_bot_active(b1_id) if b1_id else "Not Set"
    b2_status = await is_bot_active(b2_id) if b2_id else "Not Connected"
    
    b1_u = getattr(temp, "U_NAME", "Bot 1")
    b2_u = getattr(temp, "U_NAME2", "Bot 2") or getattr(temp, "CHILD_U_NAME", "Bot 2")
    
    status_text = (
        f"🤖 <b>Bot Status Overview:</b>\n\n"
        f"<b>Current Receiving Bot (@{curr_u}):</b> {'🟢 ON (Active)' if curr_active else '🔴 OFF (Maintenance)'}\n\n"
        f"<b>Bot 1 (@{b1_u}):</b> {'🟢 ON' if b1_status is True else ('🔴 OFF' if b1_status is False else b1_status)}\n"
        f"<b>Bot 2 (@{b2_u}):</b> {'🟢 ON' if b2_status is True else ('🔴 OFF' if b2_status is False else b2_status)}\n\n"
        f"<i>To toggle power on this bot: <code>/botoff</code> or <code>/boton</code></i>"
    )
    await message.reply_text(status_text, parse_mode=enums.ParseMode.HTML)


@Client.on_message(group=-100)
async def maintenance_message_gate(client: Client, message):
    """
    High-priority message gate:
    If current bot is OFF, blocks all messages from non-admins,
    sends maintenance sticker and notice, and auto-deletes both plus
    the incoming user message after 40 seconds.
    """
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        return

    # Check power status for this bot
    is_active = await is_bot_active(bot_id)
    if is_active:
        return  # Bot is ON: allow normal handler pipeline

    # Bot is OFF! Check sender authorization
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if user_id in ADMINS:
        return  # Admins are exempt: pass through to admin commands/handlers

    # Sender is NOT admin: intercept message completely
    message.stop_propagation()

    to_delete = [message.id]
    try:
        stk = await message.reply_sticker(
            sticker=MAINTENANCE_STICKER_ID,
            reply_to_message_id=message.id
        )
        if stk:
            to_delete.append(stk.id)
    except Exception as se:
        logger.debug(f"[MAINTENANCE] Error sending sticker: {se}")

    try:
        txt = await message.reply_text(
            text=MAINTENANCE_TEXT,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )
        if txt:
            to_delete.append(txt.id)
    except Exception as te:
        logger.debug(f"[MAINTENANCE] Error sending text: {te}")

    # Launch 40-second auto-deletion task
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
    If current bot is OFF, alerts non-admins and halts callback execution.
    """
    bot_id = getattr(getattr(client, "me", None), "id", None)
    if not bot_id:
        return

    is_active = await is_bot_active(bot_id)
    if is_active:
        return

    user_id = query.from_user.id if query.from_user else 0
    if user_id in ADMINS:
        return

    query.stop_propagation()
    try:
        await query.answer(
            "⚠️ This bot is currently unavailable due to maintenance. Please try again later.",
            show_alert=True
        )
    except Exception:
        pass

