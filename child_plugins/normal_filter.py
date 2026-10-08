import re
import html
import asyncio
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
from plugins.series import is_super_filter_query
from plugins.pm_filter import (
    render_normal_grouped_results,
    cb_normal_group_page,
    cb_normal_group_select,
    cb_norm_disclaimer,
    cb_norm_get_all_file,
    cb_norm_stop_files,
    BUTTON_OWNERS
)
from utils import temp, schedule_filter_message_delete

logger = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

def clean_search_query(text: str) -> str:
    name = str(text or "").strip()
    search = EMOJI_PATTERN.sub(" ", name)
    search = re.sub(r"[\.\_\-\:\+\/\\\[\]\(\)\{\}\#\@\*\&]+", " ", search)
    search = re.sub(r"(?i)\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)|with\ssubtitle(s)?|upload|full|print|file)\b", " ", search)
    search = re.sub(r"\s+", " ", search).strip()
    return search if search else name


@Client.on_message(filters.text & filters.incoming & ~filters.command(["start", "about", "help", "broadcast", "grp_broadcast"]))
async def child_filter_message_handler(client: Client, message: Message):
    if not message.text or message.text.startswith("/") or message.text.startswith("#"):
        return

    # Check banned users / chats
    if message.from_user and message.from_user.id in getattr(temp, "BANNED_USERS", []):
        return
    if message.chat and message.chat.id in getattr(temp, "BANNED_CHATS", []):
        return

    search = clean_search_query(message.text)
    if not search:
        return

    is_group = message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]

    # 1. Super Filter Check
    try:
        is_super = await is_super_filter_query(search)
    except Exception as e:
        logger.warning(f"[CHILD BOT SUPER CHECK ERROR] {e}")
        is_super = False

    if is_super:
        if is_group:
            # GROUP ROUTING: Child Bot MUST REMAIN COMPLETELY SILENT!
            logger.info(f"[CHILD BOT GROUP SILENT] query={search} matches Super Filter. Remaining silent.")
            return
        else:
            # PM ROUTING: Redirect user to Main Bot
            main_bot_username = temp.U_NAME if (hasattr(temp, "U_NAME") and temp.U_NAME) else "Bot"
            main_link = f"https://t.me/{str(main_bot_username).lstrip('@')}?start=getme_{search.replace(' ', '_')}"
            redirect_text = (
                "<b>🌟 This title is available on our Main Bot with full qualities & languages!</b>\n\n"
                "<i>ഈ മൂവി / സീരീസ് ലഭിക്കുന്നതിനായി താഴെ കാണുന്ന ബട്ടൺ ക്ലിക്ക് ചെയ്തു മെയിൻ ബോട്ടിൽ സേർച്ച് ചെയ്യുക.</i>"
            )
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Search on Main Bot", url=main_link)]])
            await message.reply_text(redirect_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            return

    # 2. Normal / Legacy Filter Search in Mongo DB
    logger.info(f"[CHILD BOT NORMAL SEARCH] query={search} chat_id={message.chat.id}")
    files, offset, total_results = await get_search_results(message.chat.id, search.lower(), max_results=100, offset=0, filter=True)

    if not files:
        # No files found in database message
        if is_group:
            msg_text = (
                "<b>sᴏʀʀʏ ɴᴏ ꜰɪʟᴇs ᴡᴇʀᴇ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ😕\n\n"
                "ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴘᴇʟʟɪɴɢ ɪɴ ɢᴏᴏɢʟᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ 😃\n\n"
                "<i>🕐 This message will be deleted in 50 seconds.</i></b>"
            )
            sent_msg = await message.reply_text(msg_text, parse_mode=enums.ParseMode.HTML)
            if sent_msg:
                schedule_filter_message_delete(client, sent_msg.chat.id, sent_msg.id, delay=50)
                schedule_filter_message_delete(client, message.chat.id, message.id, delay=50)
        else:
            await message.reply_text(f"<b>No files found in database for '<i>{html.escape(search)}</i>'</b>", parse_mode=enums.ParseMode.HTML)
        return

    # Render Normal Filter Results with max 5 buttons per page and 20-min auto-delete
    await render_normal_grouped_results(client=client, message=message, query_text=search, files=files, reply_msg=None, page=0)


# Register Callback Query Handlers on Child Bot
@Client.on_callback_query(filters.regex(r"^norm_page#"))
async def child_cb_page(client: Client, query: CallbackQuery):
    await cb_normal_group_page(client, query)

@Client.on_callback_query(filters.regex(r"^norm_grp#"))
async def child_cb_group(client: Client, query: CallbackQuery):
    await cb_normal_group_select(client, query)

@Client.on_callback_query(filters.regex(r"^norm_disc"))
async def child_cb_disc(client: Client, query: CallbackQuery):
    await cb_norm_disclaimer(client, query)

@Client.on_callback_query(filters.regex(r"^norm_getall#"))
async def child_cb_getall(client: Client, query: CallbackQuery):
    await cb_norm_get_all_file(client, query)

@Client.on_callback_query(filters.regex(r"^norm_stop#"))
async def child_cb_stop(client: Client, query: CallbackQuery):
    await cb_norm_stop_files(client, query)

@Client.on_callback_query(filters.regex(r"^english_only_reason$"))
async def child_cb_english_reason(client: Client, query: CallbackQuery):
    try:
        await query.answer("⚠️ Send movie name in English.\nOther languages are not supported!", show_alert=True)
    except Exception as e:
        logger.warning(f"[CHILD ENGLISH ALERT ERROR] {e}")
    try:
        query.stop_propagation()
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^not_in_db_reason$"))
async def child_cb_not_in_db_reason(client: Client, query: CallbackQuery):
    alert_text = (
        "➸ മൂവി Database ൽ കാണില്ല.\n"
        "➸ സ്പെല്ലിംഗ് Google ൽ ചെക്ക് ചെയ്ത് അയക്കുക.\n"
        "➸ മൂവിൻ്റെ കൂടെ റിലീസ് year ചേർക്കുക (Lift 2021).\n"
        "➸ Theatre print കിട്ടില്ല 🙂 പോയി കാണുക."
    )
    try:
        await query.answer(alert_text[:200], show_alert=True)
    except Exception as e:
        logger.warning(f"[CHILD NOT IN DB REASON ERROR] {e}")
    try:
        query.stop_propagation()
    except Exception:
        pass
