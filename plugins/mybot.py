import re
import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from info import ADMINS
from utils import (
    temp,
    get_all_delivery_bots,
    get_active_delivery_bot,
    get_active_public_bot_id,
    is_bot_active_in_memory,
    start_delivery_bot_client,
    stop_delivery_bot_client,
)
from database.users_chats_db import db

logger = logging.getLogger(__name__)


def build_mybot_panel():
    """Builds text and markup for /mybot dashboard."""
    active_clients = temp.DELIVERY_BOTS if hasattr(temp, "DELIVERY_BOTS") and isinstance(temp.DELIVERY_BOTS, dict) else {}
    bot_info = temp.DELIVERY_BOT_INFO if hasattr(temp, "DELIVERY_BOT_INFO") and isinstance(temp.DELIVERY_BOT_INFO, dict) else {}

    count = len(active_clients)
    gdbot_u = getattr(temp, "U_NAME", "GDBOT")
    active_pub_id = get_active_public_bot_id()

    bots_desc = ""
    if not active_clients:
        bots_desc = "<i>⚠️ No delivery bots connected yet.\nClick [➕ Add Delivery Bot] below to connect one!</i>\n"
    else:
        idx = 1
        for bid, client in active_clients.items():
            u = getattr(getattr(client, "me", None), "username", None) or bot_info.get(bid, {}).get("username", "Bot")
            name = getattr(getattr(client, "me", None), "first_name", None) or bot_info.get(bid, {}).get("name", "Delivery Bot")
            is_conn = getattr(client, "is_connected", False)
            is_on = is_bot_active_in_memory(bid)

            if not is_conn:
                status_dot = "🔴 Disconnected"
            elif not is_on:
                status_dot = "🔴 Turned OFF"
            elif bid == active_pub_id:
                status_dot = "🟢 ACTIVE (Serving Public)"
            else:
                status_dot = "🟡 STANDBY (Auto-activates if Active Bot goes OFF)"

            bots_desc += f"<b>{idx}. {name}</b> (@{u})\n   • ID: <code>{bid}</code> | Status: <b>{status_dot}</b>\n\n"
            idx += 1

    panel_text = (
        f"🤖 <b>Delivery Bot Control Panel</b>\n\n"
        f"🛡 <b>GDBOT:</b> @{gdbot_u} (Main Admin & DB Engine)\n"
        f"📊 <b>Connected Delivery Bots:</b> <b>{count}/2 Maximum</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{bots_desc}"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>At a time, only 1 delivery bot serves the public.\n"
        f"If the active bot is turned OFF, the standby bot auto-activates!</i>"
    )

    buttons = []
    action_row = []
    if count < 2:
        action_row.append(InlineKeyboardButton("➕ Add Bot", callback_data="mybot_add"))
    if count > 0:
        action_row.append(InlineKeyboardButton("🗑 Remove Bot", callback_data="mybot_del_menu"))
    if action_row:
        buttons.append(action_row)

    second_row = []
    if count >= 2:
        second_row.append(InlineKeyboardButton("🔀 Switch Active Bot", callback_data="mybot_switch_active"))
    if count > 0:
        second_row.append(InlineKeyboardButton("🔄 Migrate / Remap Files", callback_data="mybot_remap_menu"))
    if second_row:
        buttons.append(second_row)

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="mybot_refresh"),
        InlineKeyboardButton("❌ Close", callback_data="mybot_close")
    ])

    return panel_text, InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["mybot", "mybots", "deliverybot", "deliverybots"]) & filters.user(ADMINS))
async def cmd_mybot(client: Client, message):
    """Admin dashboard to manage up to 2 delivery bots."""
    panel_text, markup = build_mybot_panel()
    await message.reply_text(panel_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


@Client.on_callback_query(filters.regex(r"^mybot_refresh$"))
async def cb_mybot_refresh(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)
    panel_text, markup = build_mybot_panel()
    try:
        await query.message.edit_text(panel_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        await query.answer("Refreshed! 🔄")
    except Exception:
        await query.answer()


@Client.on_callback_query(filters.regex(r"^mybot_close$"))
async def cb_mybot_close(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)
    try:
        await query.message.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^mybot_add$"))
async def cb_mybot_add(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    active_clients = temp.DELIVERY_BOTS if hasattr(temp, "DELIVERY_BOTS") and isinstance(temp.DELIVERY_BOTS, dict) else {}
    if len(active_clients) >= 2:
        return await query.answer("❌ Maximum 2 delivery bots allowed! Remove one first.", show_alert=True)

    await query.answer()
    chat_id = query.message.chat.id

    cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="mybot_cancel_ask")]])
    ask_msg = await client.send_message(
        chat_id,
        "🤖 <b>Add New Delivery Bot:</b>\n\n"
        "1. Open @BotFather on Telegram.\n"
        "2. Send <code>/newbot</code> and create your bot.\n"
        "3. Copy the <b>HTTP API Token</b> and send it here.\n\n"
        "<i>Send /cancel to abort.</i>",
        reply_markup=cancel_btn,
        parse_mode=enums.ParseMode.HTML
    )

    try:
        resp = await client.ask(chat_id, timeout=120)
    except Exception:
        try:
            await ask_msg.delete()
        except Exception:
            pass
        return await client.send_message(chat_id, "⌛ <b>Timed out!</b> Please run /mybot again.")

    if not resp.text or resp.text.strip().lower() in ["/cancel", "cancel"]:
        try:
            await ask_msg.delete()
            await resp.delete()
        except Exception:
            pass
        return await client.send_message(chat_id, "🚫 <b>Process cancelled.</b>")

    raw_token = resp.text.strip()
    match = re.search(r"\b(\d+:[A-Za-z0-9_-]+)\b", raw_token)
    if not match:
        try:
            await ask_msg.delete()
        except Exception:
            pass
        return await client.send_message(chat_id, "❌ <b>Invalid Token!</b> Please provide a valid Bot API Token from @BotFather.")

    bot_token = match.group(1)

    loading_msg = await client.send_message(chat_id, "⏳ <b>Connecting and registering Delivery Bot...</b>", parse_mode=enums.ParseMode.HTML)
    try:
        await ask_msg.delete()
    except Exception:
        pass

    success, res, bot_client = await start_delivery_bot_client(bot_token, added_by=query.from_user.id)
    if not success:
        return await loading_msg.edit_text(f"❌ <b>Failed to start Delivery Bot:</b>\n\n<code>{res}</code>", parse_mode=enums.ParseMode.HTML)

    b_uname = res
    bid = bot_client.me.id if (bot_client and getattr(bot_client, "me", None)) else ""
    post_buttons = [
        [InlineKeyboardButton(f"🔄 Remap Files for {b_uname}", callback_data=f"mybot_remap_{bid}")],
        [InlineKeyboardButton("🔙 Back to /mybot", callback_data="mybot_refresh")]
    ]
    await loading_msg.edit_text(
        f"✅ <b>Successfully Connected Delivery Bot {b_uname}!</b>\n\n"
        f"• <b>Bot ID:</b> <code>{bid}</code>\n"
        f"• <b>Status:</b> 🟢 Live & Delivering Files\n"
        f"• <b>Capacity:</b> {len(temp.DELIVERY_BOTS)}/2 Bots Active\n\n"
        f"<i>💡 If this is a new bot, make sure to add it as Admin in your Storage Channels, then click 'Remap Files' below to sync file IDs.</i>",
        reply_markup=InlineKeyboardMarkup(post_buttons),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_callback_query(filters.regex(r"^mybot_cancel_ask$"))
async def cb_mybot_cancel_ask(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Cancelled.")


@Client.on_callback_query(filters.regex(r"^mybot_del_menu$"))
async def cb_mybot_del_menu(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    active_clients = temp.DELIVERY_BOTS if hasattr(temp, "DELIVERY_BOTS") and isinstance(temp.DELIVERY_BOTS, dict) else {}
    bot_info = temp.DELIVERY_BOT_INFO if hasattr(temp, "DELIVERY_BOT_INFO") and isinstance(temp.DELIVERY_BOT_INFO, dict) else {}

    if not active_clients:
        return await query.answer("No delivery bots to remove.", show_alert=True)

    buttons = []
    for bid, c in active_clients.items():
        u = getattr(getattr(c, "me", None), "username", None) or bot_info.get(bid, {}).get("username", "Bot")
        buttons.append([InlineKeyboardButton(f"🗑 Remove @{u} ({bid})", callback_data=f"mybot_del_{bid}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="mybot_refresh")])
    await query.message.edit_text(
        "🗑 <b>Select the Delivery Bot to Remove:</b>\n\n"
        "<i>This will safely stop the bot and delete it from your system.</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_callback_query(filters.regex(r"^mybot_del_(\d+)$"))
async def cb_mybot_del_confirm(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    bot_id = int(query.data.split("_")[2])
    success, u_name = await stop_delivery_bot_client(bot_id)
    await query.answer(f"Bot {u_name} removed!", show_alert=True)
    panel_text, markup = build_mybot_panel()
    try:
        await query.message.edit_text(panel_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^mybot_switch_active$"))
async def cb_mybot_switch_active(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    active_clients = temp.DELIVERY_BOTS if hasattr(temp, "DELIVERY_BOTS") and isinstance(temp.DELIVERY_BOTS, dict) else {}
    if len(active_clients) < 2:
        return await query.answer("Need 2 delivery bots connected to switch.", show_alert=True)

    bids = list(active_clients.keys())
    curr_active_id = get_active_public_bot_id()
    new_bid = bids[1] if curr_active_id == bids[0] else bids[0]
    temp.PRIMARY_DELIVERY_BOT_ID = new_bid

    from plugins.botoff import set_bot_active
    await set_bot_active(new_bid, True)

    new_bot = active_clients.get(new_bid)
    new_u = getattr(getattr(new_bot, "me", None), "username", "Bot")
    await query.answer(f"Switched active public bot to @{new_u}!", show_alert=True)

    panel_text, markup = build_mybot_panel()
    try:
        await query.message.edit_text(panel_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^mybot_remap_menu$"))
async def cb_mybot_remap_menu(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    active_clients = temp.DELIVERY_BOTS if hasattr(temp, "DELIVERY_BOTS") and isinstance(temp.DELIVERY_BOTS, dict) else {}
    bot_info = temp.DELIVERY_BOT_INFO if hasattr(temp, "DELIVERY_BOT_INFO") and isinstance(temp.DELIVERY_BOT_INFO, dict) else {}

    if not active_clients:
        return await query.answer("No delivery bots available to remap.", show_alert=True)

    buttons = []
    for bid, c in active_clients.items():
        u = getattr(getattr(c, "me", None), "username", None) or bot_info.get(bid, {}).get("username", "Bot")
        buttons.append([InlineKeyboardButton(f"🔄 Remap on @{u}", callback_data=f"mybot_remap_{bid}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="mybot_refresh")])
    await query.message.edit_text(
        "🔄 <b>Select Delivery Bot for File Migration:</b>\n\n"
        "• This will scan storage channels using the selected delivery bot.\n"
        "• All file IDs in MongoDB will be saved under this bot's token so it can deliver files smoothly.\n"
        "• Super filter and series links will be preserved.\n\n"
        "<i>⚠️ Ensure the bot is added as Admin with full rights in your storage channels!</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_callback_query(filters.regex(r"^mybot_remap_(\d+)$"))
async def cb_mybot_remap_start(client: Client, query: CallbackQuery):
    if query.from_user.id not in ADMINS and str(query.from_user.id) not in [str(a) for a in ADMINS]:
        return await query.answer("⚠️ Admin only.", show_alert=True)

    bot_id = int(query.data.split("_")[2])
    delivery_client = temp.DELIVERY_BOTS.get(bot_id)
    if not delivery_client:
        return await query.answer("❌ This delivery bot is not currently active.", show_alert=True)

    await query.answer("Starting file remapping...")
    try:
        from plugins.index import start_delivery_bot_remap
        await start_delivery_bot_remap(
            caller_client=client,
            delivery_bot=delivery_client,
            message=query.message,
            admin_user_id=query.from_user.id
        )
    except Exception as e:
        logger.error(f"[MYBOT REMAP START ERROR] {e}")
        await query.message.reply_text(f"❌ <b>Error starting remap:</b>\n\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)
