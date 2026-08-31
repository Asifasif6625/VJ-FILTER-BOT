# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os, logging, string, asyncio, time, re, ast, random, math, pytz, pyrogram
from datetime import datetime, timedelta, date, time
from Script import script
from info import *
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ChatPermissions, WebAppInfo
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from utils import get_size, is_subscribed, pub_is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings, get_shortlink, get_tutorial, send_all, get_cap
from database.users_chats_db import db
from database.ia_filterdb import col, sec_col, db as vjdb, sec_db, get_file_details, get_search_results, get_bad_files
from database.filters_mdb import del_all, find_filter, get_filters
from database.connections_mdb import mydb, active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from database.gfilters_mdb import find_gfilter, get_gfilters, del_allg
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
lock = asyncio.Lock()

BUTTON = {}
BUTTONS = {}
FRESH = {}
BUTTON_OWNERS = {}
BUTTONS0 = {}
BUTTONS1 = {}
BUTTONS2 = {}
SPELL_CHECK = {}

def is_button_owner(query: CallbackQuery, key: str) -> tuple[bool, str | None]:
    """Check if the user clicking the button is the original requester."""
    click_user = query.from_user.id
    chat_id = query.message.chat.id if (query.message and query.message.chat) else None
    message_id = query.message.id if query.message else None
    bot_id = getattr(temp, "ME", None)

    # In PM (private chat), the user clicking is ALWAYS the owner of their PM session
    if query.message and query.message.chat and query.message.chat.type == enums.ChatType.PRIVATE:
        return True, None
    if chat_id and chat_id > 0:
        return True, None

    # 1. Lookup in BUTTON_OWNERS by exact key
    stored_owner = BUTTON_OWNERS.get(key)
    if stored_owner and bot_id and stored_owner == bot_id:
        stored_owner = None

    # 2. Lookup in BUTTON_OWNERS by current message key
    if not stored_owner and chat_id and message_id:
        msg_key = f"{chat_id}-{message_id}"
        stored_owner = BUTTON_OWNERS.get(msg_key)
        if stored_owner and bot_id and stored_owner == bot_id:
            stored_owner = None

    # 3. Lookup in state caches
    if not stored_owner and hasattr(temp, "SERIES_STATE"):
        st = temp.SERIES_STATE.get(key) or (temp.SERIES_STATE.get(f"{chat_id}-{message_id}") if chat_id and message_id else None)
        if isinstance(st, dict):
            u = st.get("user_id") or st.get("user")
            if u and (not bot_id or u != bot_id):
                stored_owner = u

    if not stored_owner and hasattr(temp, "MOVIE_STATE"):
        st = temp.MOVIE_STATE.get(key) or (temp.MOVIE_STATE.get(f"{chat_id}-{message_id}") if chat_id and message_id else None)
        if isinstance(st, dict):
            u = st.get("user_id") or st.get("user")
            if u and (not bot_id or u != bot_id):
                stored_owner = u

    if not stored_owner and hasattr(temp, "GETALL"):
        st = temp.GETALL.get(key)
        if isinstance(st, dict):
            u = st.get("user_id") or st.get("user")
            if u and (not bot_id or u != bot_id):
                stored_owner = u

    # 4. Check reply_to_message if present
    if not stored_owner and query.message and query.message.reply_to_message and query.message.reply_to_message.from_user:
        rep_user = query.message.reply_to_message.from_user.id
        if rep_user and (not bot_id or rep_user != bot_id):
            stored_owner = rep_user

    # 5. Check caption/text in query.message for user mention
    if not stored_owner and query.message:
        cap = query.message.caption or query.message.text or ""
        m_req = re.search(r"tg://user\?id=(\d+)", cap)
        if m_req:
            stored_owner = int(m_req.group(1))

    # 6. Evaluation
    if stored_owner:
        is_allowed = (click_user == stored_owner)
        logger.info(
            f"[SERIES OWNER CHECK] "
            f"key={key} "
            f"click_user={click_user} "
            f"stored_owner={stored_owner} "
            f"chat_id={chat_id} "
            f"result={'ALLOWED' if is_allowed else 'DENIED'}"
        )
        if is_allowed:
            BUTTON_OWNERS[key] = stored_owner
            return True, None
        else:
            return False, "this is not your button 😊"

    # Fallback: if no owner record exists in memory, allow the clicking user and register them
    BUTTON_OWNERS[key] = click_user
    return True, None

# ─── English-Only Language Guard ───────────────────────────────────────────
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u200d\ufe0f\ufe0e\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u2934\u2935\u3030\u303d\u3297\u3299]+",
    flags=re.UNICODE
)

def is_english_only(text: str) -> bool:
    """Returns True if the non-emoji / non-symbol text contains only English / ASCII characters.
    Emojis, numbers, spaces, and punctuation are allowed."""
    cleaned = EMOJI_PATTERN.sub("", text).strip()
    if not cleaned:
        return True
    try:
        cleaned.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    
    # ── Check active wizard session ──
    from utils import get_wizard_session, temp
    if get_wizard_session(user_id) is not None:
        return
    if (user_id in getattr(temp, "AUTO_SERIES", {}) or 
        user_id in getattr(temp, "AUTO_MOVIE", {}) or 
        user_id in getattr(temp, "SERIES_WIZARD", {}) or 
        user_id in getattr(temp, "AUTO_MOVIE_BATCH", {}) or 
        getattr(temp, "SETTING_SERIES_THUMB", {}).get(user_id)):
        return

    if message.chat.id != SUPPORT_CHAT_ID:
        settings = await get_settings(message.chat.id)
        chatid = message.chat.id 
        from info import ADMINS
        if settings.get('fsub') is not None and user_id not in ADMINS:
            try:
                btn = await pub_is_subscribed(client, message, settings['fsub'])
                if btn:
                    btn.append([InlineKeyboardButton("Unmute Me 🔕", callback_data=f"unmuteme#{int(user_id)}")])
                    await client.restrict_chat_member(chatid, message.from_user.id, ChatPermissions(can_send_messages=False))
                    await message.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {message.from_user.mention},\n\nPlease join the channel then click on unmute me button. 😇", reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
                    return
            except Exception as e:
                logger.error(f"fsub error: {e}")
            
        manual = await manual_filters(client, message)
        if manual == False:
            settings = await get_settings(message.chat.id)
            # ── English-only guard ──
            if not is_english_only(message.text):
                reason_btn = InlineKeyboardMarkup([[InlineKeyboardButton("Reason 🔴", callback_data="english_only_reason")]])
                alert_msg = await message.reply_text(
                    "<b>⚠️ Only English Language Supported!\n\nThis bot only supports English language movie search.\nPlease send the movie name in English.</b>\n\n<i>🕐 This message will be deleted in 20 seconds.</i>",
                    reply_markup=reason_btn,
                    parse_mode=enums.ParseMode.HTML
                )
                await asyncio.sleep(20)
                try:
                    await alert_msg.delete()
                except:
                    pass
                return
            ai_search = True
            await auto_filter(client, message.text, message, None, ai_search)
    else: #a better logic to avoid repeated lines of code in auto_filter function
        search = message.text
        temp_files, temp_offset, total_results = await get_search_results(chat_id=message.chat.id, query=search.lower(), offset=0, filter=True)
        if total_results == 0:
            return
        else:
            return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, {str(total_results)} ʀᴇsᴜʟᴛs ᴀʀᴇ ғᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀsᴇ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {search}. \n\nTʜɪs ɪs ᴀ sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ sᴏ ᴛʜᴀᴛ ʏᴏᴜ ᴄᴀɴ'ᴛ ɢᴇᴛ ғɪʟᴇs ғʀᴏᴍ ʜᴇʀᴇ...\n\nJᴏɪɴ ᴀɴᴅ Sᴇᴀʀᴄʜ Hᴇʀᴇ - {GRP_LNK}</b>")

@Client.on_message(filters.private & filters.text & filters.incoming, group=2)
async def pm_text(bot, message):
    content = message.text
    user = message.from_user.first_name if message.from_user else "User"
    user_id = message.from_user.id if message.from_user else 0
    if not content or content.startswith("/") or content.startswith("#"):
        logger.info(f"[PM SEARCH SKIP]\nreason=start_command\ntext={content}")
        return  # ignore commands and hashtags

    if re.search(r"(?i)^(?:https?://|www\.|t\.me/|tt\d{5,12})", content.strip()):
        logger.info(f"[PM SEARCH SKIP]\nreason=url_or_id\ntext={content}")
        return
    
    # ── Check active wizard session ──
    from utils import get_wizard_session, temp
    if get_wizard_session(user_id) is not None:
        return
    if (user_id in getattr(temp, "AUTO_SERIES", {}) or 
        user_id in getattr(temp, "AUTO_MOVIE", {}) or 
        user_id in getattr(temp, "SERIES_WIZARD", {}) or 
        user_id in getattr(temp, "AUTO_MOVIE_BATCH", {}) or 
        getattr(temp, "SETTING_SERIES_THUMB", {}).get(user_id)):
        return
        
    # ── English-only guard ──
    if not is_english_only(content):
        reason_btn = InlineKeyboardMarkup([[InlineKeyboardButton("Reason 🔴", callback_data="english_only_reason")]])
        alert_msg = await bot.send_message(
            message.from_user.id,
            "<b>⚠️ Only English Language Supported!\n\nThis bot only supports English language movie search.\nPlease send the movie name in English.</b>\n\n<i>🕐 This message will be deleted in 20 seconds.</i>",
            reply_markup=reason_btn,
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(20)
        try:
            await alert_msg.delete()
        except:
            pass
        return
    if PM_SEARCH == True:
        ai_search = True
        await auto_filter(bot, content, message, None, ai_search)

@Client.on_callback_query(filters.regex(r"^english_only_reason$"), group=-100)
async def english_only_reason_alert(bot, query):
    """Show a popup alert when user clicks the Reason button for non-English search."""
    try:
        await query.answer(
            "⚠️ Send movie name in English.\nOther languages are not supported!",
            show_alert=True
        )
    except Exception as e:
        logger.warning(f"[ENGLISH ONLY ALERT ERROR] {e}")
    query.stop_propagation()

@Client.on_callback_query(filters.regex(r"^not_in_db_reason$"), group=-100)
async def not_in_db_reason_alert(bot, query):
    """Show a popup alert when user clicks the Reason button for movie not in db."""
    alert_text = (
        "➸ മൂവി Database ൽ കാണില്ല.\n"
        "➸ സ്പെല്ലിംഗ് Google ൽ ചെക്ക് ചെയ്ത് അയക്കുക.\n"
        "➸ മൂവിൻ്റെ കൂടെ റിലീസ് year ചേർക്കുക (Lift 2021).\n"
        "➸ Theatre print കിട്ടില്ല 🙂 പോയി കാണുക."
    )
    try:
        await query.answer(
            alert_text[:200],
            show_alert=True
        )
    except Exception as e:
        logger.warning(f"[NOT IN DB REASON ERROR] {e}")
    query.stop_propagation()

# ─── Movie Filter Hierarchical Flow Helpers & Handlers ───────────────────────
LANGUAGE_FLAGS = {
    "Malayalam": "🇮🇳",
    "Tamil": "🇮🇳",
    "Hindi": "🇮🇳",
    "Telugu": "🇮🇳",
    "Kannada": "🇮🇳",
    "Bengali": "🇮🇳",
    "Marathi": "🇮🇳",
    "Punjabi": "🇮🇳",
    "Gujarati": "🇮🇳",
    "Urdu": "🇮🇳",
    "Odia": "🇮🇳",
    "English": "🇬🇧",
    "Dual Audio": "🎙",
    "Multi Audio": "🎧",
    "German": "🇩🇪",
    "Korean": "🇰🇷",
    "Japanese": "🇯🇵",
    "Spanish": "🇪🇸",
    "French": "🇫🇷",
    "Arabic": "🇸🇦",
    "Russian": "🇷🇺",
    "Chinese": "🇨🇳",
    "Italian": "🇮🇹",
    "Portuguese": "🇵🇹",
    "Turkish": "🇹🇷",
    "Thai": "🇹🇭",
}

def detect_file_languages(filename: str, caption: str = None) -> list:
    from plugins.series import AUTO_LANGUAGE_MAP
    raw = str(filename or "") + " " + str(caption or "")
    raw = re.sub(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts)$", "", raw, flags=re.I)
    cleaned = ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), raw.split()))
    
    f_words = re.split(r"[\s._\-\[\]\(\)\{\}\+]+", cleaned.lower())
    detected = []
    
    is_multi_kw = ("multi" in f_words or "multiaudio" in f_words or "multi-audio" in cleaned.lower() or "multi audio" in cleaned.lower())
    is_dual_kw = (("dual" in f_words and "audio" in f_words) or "dualaudio" in f_words or "dual-audio" in cleaned.lower())
    
    found_langs = set()
    for w in f_words:
        if w in AUTO_LANGUAGE_MAP:
            found_langs.add(AUTO_LANGUAGE_MAP[w])

    if is_multi_kw or len(found_langs) >= 2:
        detected.append("Multi")
    elif is_dual_kw:
        detected.append("Dual Audio")
    elif len(found_langs) == 1:
        detected.append(list(found_langs)[0])
    else:
        detected.append("English")
        
    return detected

def parse_movie_file_info(file_doc):
    from plugins.series import extract_quality_from_filename
    fname = file_doc.get("file_name", "")
    quality = extract_quality_from_filename(fname)
    langs = detect_file_languages(fname, file_doc.get("caption"))
    primary_lang = langs[0] if langs else "English"
    return primary_lang, quality

def get_movie_languages(files):
    langs = set()
    for f in files:
        flangs = detect_file_languages(f.get("file_name", ""), f.get("caption"))
        for l in flangs:
            langs.add(l)
    preferred_order = ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English", "Multi", "Dual Audio", "Multi Audio"]
    return sorted(list(langs), key=lambda x: (preferred_order.index(x) if x in preferred_order else 99, x))

def get_movie_qualities(files, target_lang=None):
    from plugins.series import extract_quality_from_filename
    quals = set()
    for f in files:
        if target_lang:
            flangs = detect_file_languages(f.get("file_name", ""), f.get("caption"))
            if target_lang not in flangs:
                continue
        q = extract_quality_from_filename(f.get("file_name", ""))
        quals.add(q)
    quality_order = ["2160p", "4K", "1440p", "1080p", "720p", "480p", "360p", "HDRip", "WEB-DL", "BluRay", "DVDRip", "HEVC", "Unknown"]
    return sorted(list(quals), key=lambda x: (quality_order.index(x) if x in quality_order else 99, x))

def group_movie_files(files):
    from plugins.series import extract_quality_from_filename
    grouped = {}
    for f in files:
        fname = f.get("file_name", "")
        fqual = extract_quality_from_filename(fname)
        flangs = detect_file_languages(fname, f.get("caption"))
        for lang in flangs:
            if lang not in grouped:
                grouped[lang] = {}
            if fqual not in grouped[lang]:
                grouped[lang][fqual] = []
            if not any(x.get("file_id") == f.get("file_id") for x in grouped[lang][fqual]):
                grouped[lang][fqual].append(f)
    return grouped

def build_movie_language_keyboard(key, grouped_data):
    from plugins.series import to_series_font
    buttons = []
    langs = list(grouped_data.keys())
    preferred_order = ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English", "Multi", "Dual Audio", "Multi Audio"]
    langs.sort(key=lambda x: (preferred_order.index(x) if x in preferred_order else 99, x))
    
    for i in range(0, len(langs), 2):
        row = []
        for l in langs[i:i+2]:
            row.append(InlineKeyboardButton(to_series_font(l), callback_data=f"movie_lang#{key}#{l}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def build_movie_quality_keyboard(key, lang, qualities_dict):
    from plugins.series import to_series_font
    buttons = []
    quality_order = ["2160p", "4K", "1440p", "1080p", "720p", "480p", "360p", "HDRip", "WEB-DL", "BluRay", "DVDRip", "HEVC", "Unknown"]
    qualities_sorted = sorted(list(qualities_dict.keys()), key=lambda x: (quality_order.index(x) if x in quality_order else 99, x))
    
    for i in range(0, len(qualities_sorted), 2):
        row = []
        for q in qualities_sorted[i:i+2]:
            row.append(InlineKeyboardButton(to_series_font(q), callback_data=f"movie_quality#{key}#{lang}#{q}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(f"⬅️  {to_series_font('Back')}", callback_data=f"movie_back#{key}#langs")])
    return InlineKeyboardMarkup(buttons)

def build_movie_file_keyboard(key, lang, qual, files, page=0, pre="file"):
    PAGE_SIZE = 10
    total_files = len(files)
    total_pages = max(1, math.ceil(total_files / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    current_page_files = files[start_idx:end_idx]
    
    buttons = []
    for f in current_page_files:
        f_size = get_size(f.get("file_size", 0))
        cleaned_fn = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.') and not x.startswith('t.me'), f.get("file_name", "").split()))
        buttons.append([
            InlineKeyboardButton(
                f"📁 [{f_size}] {cleaned_fn[:45]}",
                callback_data=f"{pre}#{f['file_id']}"
            )
        ])
        
    if total_pages > 1:
        pag_row = []
        if page > 0:
            pag_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"movie_files#{key}#{lang}#{qual}#{page-1}"))
        pag_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="pages"))
        if page < total_pages - 1:
            pag_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"movie_files#{key}#{lang}#{qual}#{page+1}"))
        buttons.append(pag_row)
        
    buttons.append([
        InlineKeyboardButton("⬅️ Quality", callback_data=f"movie_lang#{key}#{lang}"),
        InlineKeyboardButton("⬅️ Language", callback_data=f"movie_back#{key}#langs")
    ])
    return InlineKeyboardMarkup(buttons)


@Client.on_callback_query(filters.regex(r"^(mvlang#|movie_lang#)"))
async def movie_lang_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    key = parts[1]
    lang = parts[2]
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
        
    state = getattr(temp, "MOVIE_STATE", {}).get(key)
    if not state:
        return await query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        
    qualities_dict = state.get("grouped", {}).get(lang, {})
    if not qualities_dict:
        return await query.answer("⚠️ No qualities found for this language.", show_alert=True)
        
    total_lang_files = sum(len(flist) for flist in qualities_dict.values())
    logger.info(f"[MOVIE LANGUAGE]\nkey={key}\nlanguage={lang}\nfiles={total_lang_files}")

    title = state.get("title", "Movie")
    year = state.get("year", "")
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = state.get("rating", "")
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    
    cap = (
        f"🎬 <b>{title}{year_str}</b>"
        f"{rating_str}\n\n"
        f"🌐 <b>Language:</b> {lang}\n\n"
        f"🎞 <b>Choose Quality:</b>"
    )
    markup = build_movie_quality_keyboard(key, lang, qualities_dict)
    try:
        if query.message.photo or query.message.caption:
            await query.message.edit_caption(caption=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.message.edit_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        pass
    from utils import schedule_filter_message_delete
    schedule_filter_message_delete(client, query.message.chat.id, query.message.id, 600)
    await query.answer()

@Client.on_callback_query(filters.regex(r"^(mvqual#|movie_quality#)"))
async def movie_qual_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    key = parts[1]
    lang = parts[2]
    qual = parts[3]
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
        
    state = getattr(temp, "MOVIE_STATE", {}).get(key)
    if not state:
        return await query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        
    files = state.get("grouped", {}).get(lang, {}).get(qual, [])
    if not files:
        return await query.answer("⚠️ No files found for this quality.", show_alert=True)
        
    title = state.get("title", "Movie")
    logger.info(f"[MOVIE QUALITY]\ntitle={title}\nlanguage={lang}\nquality={qual}\nfiles={len(files)}")
    logger.info(
        f"[QUALITY DELIVERY]\n"
        f"filter_type=movie\n"
        f"language={lang}\n"
        f"quality={qual}\n"
        f"files={len(files)}"
    )
    
    import uuid, time
    from database.series_db import save_temp_request
    req_key = str(uuid.uuid4())[:8]
    req_data = {
        "request_key": req_key,
        "user": query.from_user.id,
        "user_id": query.from_user.id,
        "type": "movie",
        "request_type": "movie",
        "source": "MOVIE_FILTER",
        "movie_title": title,
        "title": title,
        "language": lang,
        "quality": qual,
        "files": files,
        "delivery_status": "pending",
        "state": "PENDING",
        "created_at": time.time()
    }
    if not hasattr(temp, "MOVIE_STATE"):
        temp.MOVIE_STATE = {}
    temp.MOVIE_STATE[req_key] = req_data
    if not hasattr(temp, "GETALL"):
        temp.GETALL = {}
    temp.GETALL[req_key] = req_data
    try:
        await save_temp_request(req_key, req_data)
    except Exception:
        pass
        
    bot_username = temp.U_NAME if (hasattr(temp, "U_NAME") and temp.U_NAME) else getattr(getattr(client, "me", None), "username", None)
    if bot_username:
        bot_username = str(bot_username).lstrip("@")
    else:
        bot_username = "Bot"

    start_url = f"https://t.me/{bot_username}?start=all_{req_key}"
    
    # If in private chat, directly deliver files
    if query.message.chat.type == enums.ChatType.PRIVATE:
        from plugins.commands import send_movie_files_to_user
        await query.answer("🚀 Sending files...")
        await send_movie_files_to_user(
            client=client,
            user_id=query.from_user.id,
            files=files,
            query=query,
            movie_title=title,
            language=lang,
            quality=qual
        )
        return
        
    try:
        return await query.answer(url=start_url)
    except Exception as e:
        logger.warning(f"[MOVIE QUALITY ROUTING] query.answer(url=start_url) failed: {e}. Replying with fallback button.")
        fb_msg = await query.message.reply_text(
            f"📩 Open bot to get your requested <b>{title}</b> ({qual}) files:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📂 Open Bot", url=start_url)]
            ])
        )
        from utils import schedule_filter_message_delete
        if fb_msg:
            schedule_filter_message_delete(client, fb_msg.chat.id, fb_msg.id, 600)
        return

@Client.on_callback_query(filters.regex(r"^(mvpage#|movie_files#)"))
async def movie_page_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    key = parts[1]
    lang = parts[2]
    qual = parts[3]
    page_str = parts[4] if len(parts) > 4 else "0"
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
        
    state = getattr(temp, "MOVIE_STATE", {}).get(key)
    if not state:
        return await query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        
    files = state.get("grouped", {}).get(lang, {}).get(qual, [])
    page = int(page_str) if page_str.isdigit() else 0
    pre = state.get("pre", "file")
    
    logger.info(f"[MOVIE FILES]\nkey={key}\nlanguage={lang}\nquality={qual}\npage={page}\nfiles={len(files)}")

    markup = build_movie_file_keyboard(key, lang, qual, files, page=page, pre=pre)
    try:
        await query.message.edit_reply_markup(reply_markup=markup)
    except MessageNotModified:
        pass
    from utils import schedule_filter_message_delete
    schedule_filter_message_delete(client, query.message.chat.id, query.message.id, 600)
    await query.answer()

@Client.on_callback_query(filters.regex(r"^(mvback#|movie_back#)"))
async def movie_back_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    key = parts[1]
    target = parts[2]
    
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
        
    state = getattr(temp, "MOVIE_STATE", {}).get(key)
    if not state:
        return await query.answer("⚠️ Session expired. Please search again.", show_alert=True)
        
    title = state.get("title", "Movie")
    year = state.get("year", "")
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = state.get("rating", "")
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = state.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
    
    if target == "langs":
        grouped = state.get("grouped", {})
        langs_disp = ", ".join(grouped.keys())
        cap = (
            f"🎬 <b>{title}{year_str}</b>"
            f"{rating_str}"
            f"{genre_str}\n\n"
            f"🌐 <b>Available Languages:</b> {langs_disp}\n\n"
            f"🍿 <b>Choose Language:</b>"
        )
        markup = build_movie_language_keyboard(key, grouped)
    elif target == "qual":
        lang = parts[3] if len(parts) > 3 else list(state.get("grouped", {}).keys())[0]
        qualities_dict = state.get("grouped", {}).get(lang, {})
        cap = (
            f"🎬 <b>{title}{year_str}</b>"
            f"{rating_str}\n\n"
            f"🌐 <b>Language:</b> {lang}\n\n"
            f"🎞 <b>Choose Quality:</b>"
        )
        markup = build_movie_quality_keyboard(key, lang, qualities_dict)
    else:
        return await query.answer()
        
    try:
        if query.message.photo or query.message.caption:
            await query.message.edit_caption(caption=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.message.edit_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        pass
    from utils import schedule_filter_message_delete
    schedule_filter_message_delete(client, query.message.chat.id, query.message.id, 600)
    await query.answer()

@Client.on_callback_query(filters.regex(r"^(mvclose#|movie_close#)"))
async def movie_close_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    key = parts[1] if len(parts) > 1 else None
    if key and hasattr(temp, "MOVIE_STATE"):
        temp.MOVIE_STATE.pop(key, None)
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Closed.")


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    is_owner, _ = is_button_owner(query, key)
    if int(req) not in [query.from_user.id, 0] and not is_owner:
        return await query.answer("this is not your button 😊", show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = FRESH.get(key)
   # if not search:
      #  await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
       # return

    files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    temp.GETALL[key] = files
    temp.SHORT[query.from_user.id] = query.message.chat.id
    settings = await get_settings(query.message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]

        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])

    page_limit = int(MAX_B_TN) if MAX_B_TN else 5
    cur_page = (offset // page_limit) + 1
    total_pages = math.ceil(total / page_limit) if total else 1

    if 0 < offset <= page_limit:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - page_limit

    if n_offset == 0 or n_offset == "":
        btn.append(
            [InlineKeyboardButton("⌫ 𝐁𝐀𝐂𝐊", callback_data=f"next_{req}_{key}_{off_set}"), InlineKeyboardButton(f"{cur_page} / {total_pages}", callback_data="pages")]
        )
    elif off_set is None:
        btn.append([InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(f"{cur_page} / {total_pages}", callback_data="pages"), InlineKeyboardButton("𝐍𝐄𝐗𝐓 ➪", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⌫ 𝐁𝐀𝐂𝐊", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"{cur_page} / {total_pages}", callback_data="pages"),
                InlineKeyboardButton("𝐍𝐄𝐗𝐓 ➪", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        cap = await get_cap(settings, remaining_seconds, files, query, total, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            pass
    await query.answer()

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    movies = None
    if query.message and query.message.reply_to_message:
        movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies and query.message and hasattr(query.message, "reply_to_message_id") and query.message.reply_to_message_id:
        movies = SPELL_CHECK.get(query.message.reply_to_message_id)
    if not movies and query.message:
        movies = SPELL_CHECK.get(query.message.id)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    if int(user) != 0 and query.from_user.id != int(user):
        logger.info(f"[PM MOVIE OWNERSHIP]\ncallback_user_id={query.from_user.id}\nstored_user_id={user}\nrequest_key={query.data}\nresult=DENIED")
        return await query.answer("⚠️ This is not your button.", show_alert=True)
    if not movies:
        logger.info(f"[PM MOVIE OWNERSHIP]\ncallback_user_id={query.from_user.id}\nstored_user_id={user}\nrequest_key={query.data}\nresult=EXPIRED")
        return await query.answer("⚠️ Search request expired. Please search again.", show_alert=True)
    try:
        movie = movies[(int(movie_))]
    except (IndexError, ValueError, TypeError):
        return await query.answer("⚠️ Search request expired. Please search again.", show_alert=True)
    movie = re.sub(r"[🎬📺\(\)\[\]]", " ", movie)
    movie = re.sub(r"[:\-]", " ", movie)
    movie = re.sub(r"\s+", " ", movie).strip()
    await query.answer(script.TOP_ALRT_MSG)
    gl = await global_filters(bot, query.message, text=movie)
    if gl == False:
        k = await manual_filters(bot, query.message, text=movie)
        if k == False:
            # ── 1. Check Super Movie ──
            try:
                from plugins.series import process_super_movie_search
                is_super_movie = await process_super_movie_search(bot, query.message.reply_to_message or query.message, movie, query.message)
                if is_super_movie:
                    return
            except Exception as e:
                logger.error(f"[SUPER MOVIE SEARCH ROUTING ERROR in spoll] {e}")

            # ── 2. Check ia_filterdb ──
            files, offset, total_results = await get_search_results(query.message.chat.id, movie, offset=0, filter=True)
            logger.info(f"[NORMAL MOVIE SEARCH]\nquery={movie}\ndb_files={len(files)}")
            if files:
                k = (movie, files, offset, total_results)
                ai_search = True
                reply_msg = await query.message.edit_text(f"<b><i>Searching For {movie} 🔍</i></b>")
                await auto_filter(bot, movie, query, reply_msg, ai_search, k)
            else:
                # ── 3. Check Series ──
                try:
                    from plugins.series import process_series_search
                    is_series = await process_series_search(bot, query.message.reply_to_message or query.message, movie, query.message)
                    if is_series:
                        return
                except Exception:
                    pass

                # ── 4. No Results ──
                reqstr1 = query.from_user.id if query.from_user else 0
                reqstr = await bot.get_users(reqstr1)
                if NO_RESULTS_MSG:
                    await bot.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, movie)))
                k = await query.message.edit(script.MVE_NT_FND)
                await asyncio.sleep(10)
                await k.delete()

# Year 
@Client.on_callback_query(filters.regex(r"^years#"))
async def years_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    btn = []
    for i in range(0, len(YEARS)-1, 4):
        row = []
        for j in range(4):
            if i+j < len(YEARS):
                row.append(
                    InlineKeyboardButton(
                        text=YEARS[i+j].title(),
                        callback_data=f"fy#{YEARS[i+j].lower()}#{key}"
                    )
                )
        btn.append(row)

    btn.insert(
        0,
        [
            InlineKeyboardButton(
                text="sᴇʟᴇᴄᴛ ʏᴏᴜʀ ʏᴇᴀʀ", callback_data="ident"
            )
        ],
    )
    req = query.from_user.id
    offset = 0
    btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fy#homepage#{key}")])

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^fy#"))
async def filter_yearss_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    baal = lang in search
    if baal:
        search = search.replace(lang, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    if lang != "homepage":
        search = f"{search} {lang}" 
    BUTTONS[key] = search

    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    if not files:
        await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])

    if offset != "":
        try:
            if settings['max_btn']:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
    
            else:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_B_TN))}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append(
                [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
            )
    else:
        btn.append(
            [InlineKeyboardButton(text="𝐍𝐎 𝐌𝐎𝐑𝐄 𝐏𝐀𝐆𝐄𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄",callback_data="pages")]
        )
    if lang != "homepage":
        req = query.from_user.id
        offset = 0
        btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fy#homepage#{key}")])
    
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            pass
    await query.answer()  

# Episode

@Client.on_callback_query(filters.regex(r"^episodes#"))
async def episodes_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    btn = []
    for i in range(0, len(EPISODES)-1, 4):
        row = []
        for j in range(4):
            if i+j < len(EPISODES):
                row.append(
                    InlineKeyboardButton(
                        text=EPISODES[i+j].title(),
                        callback_data=f"fe#{EPISODES[i+j].lower()}#{key}"
                    )
                )
        btn.append(row)

    btn.insert(
        0,
        [
            InlineKeyboardButton(
                text="sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴇᴘɪsᴏᴅᴇ", callback_data="ident"
            )
        ],
    )
    req = query.from_user.id
    offset = 0
    btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fe#homepage#{key}")])

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^fe#"))
async def filter_episodes_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    baal = lang in search
    if baal:
        search = search.replace(lang, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    if lang != "homepage":
        search = f"{search} {lang}" 
    BUTTONS[key] = search

    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    if not files:
        await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])

    if offset != "":
        try:
            if settings['max_btn']:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
    
            else:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_B_TN))}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append(
                [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
            )
    else:
        btn.append(
            [InlineKeyboardButton(text="𝐍𝐎 𝐌𝐎𝐑𝐄 𝐏𝐀𝐆𝐄𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄",callback_data="pages")]
        )
    if lang != "homepage":
        req = query.from_user.id
        offset = 0
        btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fe#homepage#{key}")])
    
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            pass
    await query.answer()
    


#languages

@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) >= 4:
        from plugins.series import ser_lang_callback
        return await ser_lang_callback(client, query)
    key = parts[1] if len(parts) > 1 else ""
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    btn = []
    for i in range(0, len(LANGUAGES)-1, 2):
        btn.append([
            InlineKeyboardButton(
                text=LANGUAGES[i].title(),
                callback_data=f"fl#{LANGUAGES[i].lower()}#{key}"
            ),
            InlineKeyboardButton(
                text=LANGUAGES[i+1].title(),
                callback_data=f"fl#{LANGUAGES[i+1].lower()}#{key}"
            ),
        ])

    btn.insert(
        0,
        [
            InlineKeyboardButton(
                text="👇 𝖲𝖾𝗅𝖾𝖼𝗍 𝖸𝗈𝗎𝗋 𝖫𝖺𝗇𝗀𝗎𝖺𝗀𝖾𝗌 👇", callback_data="ident"
            )
        ],
    )
    req = query.from_user.id
    offset = 0
    btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ​↭", callback_data=f"fl#homepage#{key}")])

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^fl#"))
async def filter_languages_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    baal = lang in search
    if baal:
        search = search.replace(lang, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    if lang != "homepage":
        search = f"{search} {lang}" 
    BUTTONS[key] = search

    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    if not files:
        await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])

    if offset != "":
        try:
            if settings['max_btn']:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
    
            else:
                btn.append(
                    [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_B_TN))}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
                )
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append(
                [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪",callback_data=f"next_{req}_{key}_{offset}")]
            )
    else:
        btn.append(
            [InlineKeyboardButton(text="𝐍𝐎 𝐌𝐎𝐑𝐄 𝐏𝐀𝐆𝐄𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄",callback_data="pages")]
        )
    if lang != "homepage":
        req = query.from_user.id
        offset = 0
        btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fl#homepage#{key}")])
    
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            pass
    await query.answer()
    
    
    
@Client.on_callback_query(filters.regex(r"^seasons#"))
async def seasons_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    BUTTONS[key] = None
    try:
        search = search.replace(' ', '_')
    except:
        pass
    btn = []
    for i in range(0, len(SEASONS)-1, 2):
        btn.append([
            InlineKeyboardButton(
                text=SEASONS[i].title(),
                callback_data=f"fs#{SEASONS[i].lower()}#{key}"
            ),
            InlineKeyboardButton(
                text=SEASONS[i+1].title(),
                callback_data=f"fs#{SEASONS[i+1].lower()}#{key}"
            ),
        ])

    btn.insert(
        0,
        [
            InlineKeyboardButton(
                text="👇 𝖲𝖾𝗅𝖾𝖼𝗍 Season 👇", callback_data="ident"
            )
        ],
    )
    req = query.from_user.id
    offset = 0
    btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ​↭", callback_data=f"next_{req}_{key}_{offset}")])

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^fs#"))
async def filter_seasons_cb_handler(client: Client, query: CallbackQuery):
    _, seas, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    sea = ""
    season_search = ["s01","s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09", "s10", "season 01","season 02","season 03","season 04","season 05","season 06","season 07","season 08","season 09","season 10", "season 1","season 2","season 3","season 4","season 5","season 6","season 7","season 8","season 9"]
    for x in range (len(season_search)):
        if season_search[x] in search:
            sea = season_search[x]
            break
    if sea:
        search = search.replace(sea, "")
    else:
        search = search
    
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    
    searchagn = search
    search1 = search
    search2 = search
    search = f"{search} {seas}"
    BUTTONS0[key] = search
    
    files, _, _ = await get_search_results(chat_id, search, max_results=10)
    files = [file for file in files if re.search(seas, file["file_name"], re.IGNORECASE)]
    
    seas1 = "s01" if seas == "season 1" else "s02" if seas == "season 2" else "s03" if seas == "season 3" else "s04" if seas == "season 4" else "s05" if seas == "season 5" else "s06" if seas == "season 6" else "s07" if seas == "season 7" else "s08" if seas == "season 8" else "s09" if seas == "season 9" else "s10" if seas == "season 10" else ""
    search1 = f"{search1} {seas1}"
    BUTTONS1[key] = search1
    files1, _, _ = await get_search_results(chat_id, search1, max_results=10)
    files1 = [file for file in files1 if re.search(seas1, file["file_name"], re.IGNORECASE)]
    
    if files1:
        files.extend(files1)
    
    seas2 = "season 01" if seas == "season 1" else "season 02" if seas == "season 2" else "season 03" if seas == "season 3" else "season 04" if seas == "season 4" else "season 05" if seas == "season 5" else "season 06" if seas == "season 6" else "season 07" if seas == "season 7" else "season 08" if seas == "season 8" else "season 09" if seas == "season 9" else "s010"
    search2 = f"{search2} {seas2}"
    BUTTONS2[key] = search2
    files2, _, _ = await get_search_results(chat_id, search2, max_results=10)
    files2 = [file for file in files2 if re.search(seas2, file["file_name"], re.IGNORECASE)]

    if files2:
        files.extend(files2)
        
    if not files:
        await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    if lang != "homepage":
        req = query.from_user.id
        offset = 0
        btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"next_{req}_{key}_{offset}")])
    
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        total_results = len(files)
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except MessageNotModified:
            pass

@Client.on_callback_query(filters.regex(r"^qualities#"))
async def qualities_cb_handler(client: Client, query: CallbackQuery):
    _, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    btn = []
    for i in range(0, len(QUALITIES)-1, 2):
        btn.append([
            InlineKeyboardButton(
                text=QUALITIES[i].title(),
                callback_data=f"fq#{QUALITIES[i].lower()}#{key}"
            ),
            InlineKeyboardButton(
                text=QUALITIES[i+1].title(),
                callback_data=f"fq#{QUALITIES[i+1].lower()}#{key}"
            ),
        ])

    btn.insert(
        0,
        [
            InlineKeyboardButton(
                text="⇊ ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ǫᴜᴀʟɪᴛʏ ⇊", callback_data="ident"
            )
        ],
    )
    req = query.from_user.id
    offset = 0
    btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"fq#homepage#{key}")])

    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))
    await query.answer()
    

@Client.on_callback_query(filters.regex(r"^fq#"))
async def filter_qualities_cb_handler(client: Client, query: CallbackQuery):
    _, qual, key = query.data.split("#")
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)
    search = FRESH.get(key)
    if not search:
        return await query.answer("Search Context Expired! Please search again.", show_alert=True)
    try:
        search = search.replace(' ', '_')
    except:
        pass
    baal = qual in search
    if baal:
        search = search.replace(qual, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    searchagain = search
    if qual != "homepage":
        search = f"{search} {qual}" 
    BUTTONS[key] = search

    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    # files = [file for file in files if re.search(lang, file["file_name"], re.IGNORECASE)]
    if not files:
        await query.answer("🚫 𝗡𝗼 𝗙𝗶𝗹𝗲 𝗪𝗲𝗿𝗲 𝗙𝗼𝘂𝗻𝗱 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])
    else:
        btn = []
        btn.insert(0, [
            InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
        ])

    if offset != "":
        try:
            if settings['max_btn']:
                btn.append(
                    [InlineKeyboardButton("ᴘᴀɢᴇ", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⇛",callback_data=f"next_{req}_{key}_{offset}")]
                )
    
            else:
                btn.append(
                    [InlineKeyboardButton("ᴘᴀɢᴇ", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_B_TN))}",callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⇛",callback_data=f"next_{req}_{key}_{offset}")]
                )
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append(
                [InlineKeyboardButton("ᴘᴀɢᴇ", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}",callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⇛",callback_data=f"next_{req}_{key}_{offset}")]
            )
    else:
        btn.append(
            [InlineKeyboardButton(text="😶 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇꜱ ᴀᴠᴀɪʟᴀʙʟᴇ 😶",callback_data="pages")]
        )
    if qual != "homepage":
        req = query.from_user.id
        offset = 0
        btn.append([InlineKeyboardButton(text="↭ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ↭", callback_data=f"next_{req}_{key}_{offset}")])
    
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        total_results = len(files)
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except MessageNotModified:
            pass
                
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data and query.data.startswith(("as_season#", "as_finish#", "sr#", "sw#", "edser#", "vser#", "edmov#", "delmov#", "anomov#", "emovie_", "emov#", "series_", "movie_", "smovie_", "send_fsall#", "am_", "slink_", "sfile_", "ser_", "sug_mov#", "sug_ser#")):
        query.continue_propagation()
        return
    if query.data == "not_in_db_reason":
        alert_text = (
            "➸ മൂവി Database ൽ കാണില്ല.\n"
            "➸ സ്പെല്ലിംഗ് Google ൽ ചെക്ക് ചെയ്ത് അയക്കുക.\n"
            "➸ മൂവിൻ്റെ കൂടെ റിലീസ് year ചേർക്കുക (Lift 2021).\n"
            "➸ Theatre print കിട്ടില്ല 🙂 പോയി കാണുക."
        )
        return await query.answer(alert_text[:200], show_alert=True)
    if query.data == "english_only_reason":
        return await query.answer("⚠️ Send movie name in English.\nOther languages are not supported!", show_alert=True)
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "get_trail":
        user_id = query.from_user.id
        free_trial_status = await db.get_free_trial_status(user_id)
        if not free_trial_status:            
            await db.give_free_trail(user_id)
            new_text = "**ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇs ꜰʀᴏᴍ ɴᴏᴡ 😀\n\nआप अब से 5 मिनट के लिए निःशुल्क ट्रायल का उपयोग कर सकते हैं 😀**"        
            await query.message.edit_text(text=new_text)
            return
        else:
            new_text= "**🤣 you already used free now no more free trail. please buy subscription here are our 👉 /plans**"
            await query.message.edit_text(text=new_text)
            return
            
    elif query.data == "buy_premium":
        btn = [[            
            InlineKeyboardButton("✅sᴇɴᴅ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ ✅", url = OWNER_LINK)
        ]
            for admin in ADMINS
        ]
        btn.append(
            [InlineKeyboardButton("⚠️ᴄʟᴏsᴇ / ᴅᴇʟᴇᴛᴇ⚠️", callback_data="close_data")]
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo=PAYMENT_QR,
            caption=PAYMENT_TEXT,
            reply_markup=reply_markup
        )
        return 
    elif query.data == "gfiltersdeleteallconfirm":
        await del_allg(query.message, 'gfilters')
        await query.answer("Done !")
        return
    elif query.data == "gfiltersdeleteallcancel": 
        await query.message.reply_to_message.delete()
        await query.message.delete()
        await query.answer("Process Cancelled !")
        return
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Mᴀᴋᴇ sᴜʀᴇ I'ᴍ ᴘʀᴇsᴇɴᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ!!", quote=True)
                    return await query.answer(MSG_ALRT)
            else:
                await query.message.edit_text(
                    "I'ᴍ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs!\nCʜᴇᴄᴋ /connections ᴏʀ ᴄᴏɴɴᴇᴄᴛ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs",
                    quote=True
                )
                return await query.answer(MSG_ALRT)

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer(MSG_ALRT)

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ Gʀᴏᴜᴘ Oᴡɴᴇʀ ᴏʀ ᴀɴ Aᴜᴛʜ Usᴇʀ ᴛᴏ ᴅᴏ ᴛʜᴀᴛ!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Tʜᴀᴛ's ɴᴏᴛ ғᴏʀ ʏᴏᴜ!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Gʀᴏᴜᴘ Nᴀᴍᴇ : **{title}**\nGʀᴏᴜᴘ ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer(MSG_ALRT)
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Cᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Dɪsᴄᴏɴɴᴇᴄᴛᴇᴅ ғʀᴏᴍ **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴄᴏɴɴᴇᴄᴛɪᴏɴ !"
            )
        else:
            await query.message.edit_text(
                f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "Tʜᴇʀᴇ ᴀʀᴇ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴs!! Cᴏɴɴᴇᴄᴛ ᴛᴏ sᴏᴍᴇ ɢʀᴏᴜᴘs ғɪʀsᴛ.",
            )
            return await query.answer(MSG_ALRT)
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Yᴏᴜʀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘ ᴅᴇᴛᴀɪʟs ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "gfilteralert" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_gfilter('gfilters', keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
            
    elif query.data.startswith("file"):
        clicked = query.from_user.id
        chat_id = query.message.chat.id if query.message else None
        msg_id = query.message.id if query.message else None
        is_private = (chat_id and chat_id > 0) or (query.message and query.message.chat and query.message.chat.type == enums.ChatType.PRIVATE)
        
        is_owner = False
        if is_private:
            is_owner = True
        else:
            key = f"{chat_id}-{msg_id}"
            is_owner, _ = is_button_owner(query, key)
            if not is_owner and query.message and query.message.reply_to_message and query.message.reply_to_message.from_user:
                is_owner = (clicked == query.message.reply_to_message.from_user.id)
                if is_owner:
                    BUTTON_OWNERS[key] = clicked

        import logging
        log = logging.getLogger(__name__)
        if is_owner:
            log.info(f"[PM MOVIE OWNERSHIP]\ncallback_user_id={clicked}\nrequest_key={query.data}\nchat_id={chat_id}\nmessage_id={msg_id}\nresult=ALLOWED")
        else:
            log.info(f"[PM MOVIE OWNERSHIP]\ncallback_user_id={clicked}\nrequest_key={query.data}\nchat_id={chat_id}\nmessage_id={msg_id}\nresult=DENIED")
            return await query.answer("this is not your button 😊", show_alert=True)

        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        files = files_
        title = files["file_name"]
        size = get_size(files["file_size"])
        f_caption = files["caption"]
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files['file_name']}"

        try:
            if settings['is_shortlink'] and not await db.has_premium_access(query.from_user.id):
                cmd = f"short_{file_id}"
            else:
                cmd = f"{ident}_{file_id}"
                
            if is_owner:
                if query.message.chat.type == enums.ChatType.PRIVATE:
                    await query.answer()
                    from plugins.commands import start
                    class MockMsg:
                        def __init__(self, q, c):
                            self.message = q.message
                            self.chat = q.message.chat
                            self.from_user = q.from_user
                            self.text = f"/start {c}"
                            self.command = ["start", c]
                            self.id = q.message.id
                            self.date = q.message.date
                        def __getattr__(self, name):
                            return getattr(self.message, name)
                    return await start(client, MockMsg(query, cmd))
                else:
                    if not hasattr(temp, "GROUP_MOVIE_REQS"):
                        temp.GROUP_MOVIE_REQS = {}
                        
                    if AUTH_CHANNEL and not await is_subscribed(client, query):
                        import uuid
                        req_id = str(uuid.uuid4())[:8]
                        temp.GROUP_MOVIE_REQS[req_id] = {
                            "user": clicked,
                            "source": "group",
                            "cmd": cmd
                        }
                        log.info(f"[GROUP MOVIE] FILE CLICK\n[GROUP MOVIE] USER = {clicked}\n[GROUP MOVIE] REQUEST ID = {req_id}\n[GROUP MOVIE] FORCE SUB CHECK\n[GROUP MOVIE] FORCE SUB RESULT = FAIL")
                        await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=fsub_{req_id}")
                        return
                    else:
                        log.info(f"[GROUP MOVIE] NEW FILE REQUEST\n[GROUP MOVIE] FRESH FORCE SUB CHECK\n[GROUP MOVIE] FORCE SUB RESULT = PASS")
                        if settings['is_shortlink'] and not await db.has_premium_access(query.from_user.id):
                            temp.SHORT[clicked] = query.message.chat.id
                        await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")
                        return
            else:
                await query.answer("this is not your button 😊", show_alert=True)
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")
        except Exception as e:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")
            
    elif query.data.startswith("sendfiles"):
        ident, key = query.data.split("#")
        is_owner, err_msg = is_button_owner(query, key)
        if not is_owner:
            return await query.answer(err_msg, show_alert=True)
        clicked = query.from_user.id
        settings = await get_settings(query.message.chat.id)
        pre = 'allfilesp' if settings['file_secure'] else 'allfiles'
        try:
            if settings['is_shortlink'] and not await db.has_premium_access(query.from_user.id):
                cmd = f"sendfiles1_{key}"
            else:
                cmd = f"{pre}_{key}"
                
            if query.message.chat.type == enums.ChatType.PRIVATE:
                await query.answer()
                from plugins.commands import start
                class MockMsg:
                    def __init__(self, q, c):
                        self.message = q.message
                        self.chat = q.message.chat
                        self.from_user = q.from_user
                        self.text = f"/start {c}"
                        self.command = ["start", c]
                        self.id = q.message.id
                        self.date = q.message.date
                    def __getattr__(self, name):
                        return getattr(self.message, name)
                return await start(client, MockMsg(query, cmd))
            else:
                import logging
                log = logging.getLogger(__name__)
                if not hasattr(temp, "GROUP_MOVIE_REQS"):
                    temp.GROUP_MOVIE_REQS = {}
                    
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    import uuid
                    req_id = str(uuid.uuid4())[:8]
                    temp.GROUP_MOVIE_REQS[req_id] = {
                        "user": clicked,
                        "source": "group",
                        "cmd": cmd
                    }
                    log.info(f"[GROUP MOVIE] FILE CLICK\n[GROUP MOVIE] USER = {clicked}\n[GROUP MOVIE] REQUEST ID = {req_id}\n[GROUP MOVIE] FORCE SUB CHECK\n[GROUP MOVIE] FORCE SUB RESULT = FAIL")
                    await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=fsub_{req_id}")
                    return
                else:
                    log.info(f"[GROUP MOVIE] NEW FILE REQUEST\n[GROUP MOVIE] FRESH FORCE SUB CHECK\n[GROUP MOVIE] FORCE SUB RESULT = PASS")
                    await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")
                    return
                
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")
        except Exception as e:
            logger.exception(e)
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={cmd}")

    elif query.data.startswith("unmuteme"):
        ident, userid = query.data.split("#")
        user_id = query.from_user.id
        settings = await get_settings(int(query.message.chat.id))
        if userid == 0:
            await query.answer("You are anonymous admin !", show_alert=True)
            return
        try:
            btn = await pub_is_subscribed(client, query, settings['fsub'])
            if btn:
                await query.answer("Kindly Join Given Channel Then Click On Unmute Button", show_alert=True)
            else:
                await client.unban_chat_member(query.message.chat.id, user_id)
                await query.answer("Unmuted Successfully !", show_alert=True)
                try:
                    await query.message.delete()
                except:
                    return
        except:
            await query.answer("Not For Your My Dear", show_alert=True)
   
    elif query.data.startswith("del"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        files = files_
        title = files['file_name']
        size = get_size(files['file_size'])
        f_caption = files['caption']
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files['file_name']}"
        await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=file_{file_id}")
    
    elif query.data.startswith("checksub"):
        try:
            ident, kk, file_id = query.data.split("#", 2)
            import logging
            log = logging.getLogger(__name__)
            
            req_id = file_id
            log.info(f"[TRY AGAIN] clicked user_id={query.from_user.id}")
            log.info(f"[TRY AGAIN] requested_file_id={req_id}")
            
            if kk == "movie":
                if not hasattr(temp, "GROUP_MOVIE_REQS"):
                    temp.GROUP_MOVIE_REQS = {}
                req = temp.GROUP_MOVIE_REQS.get(req_id)
                if not req:
                    await query.answer("⚠️ Request expired.", show_alert=True)
                    return
                if query.from_user.id != req["user"]:
                    await query.answer("⚠️ This request is not for you.", show_alert=True)
                    return
                    
                if req.get("state") in ["SENDING", "COMPLETED"]:
                    await query.answer("⚠️ This request is already being processed.", show_alert=True)
                    return
                    
                first_check = not await is_subscribed(client, query) if AUTH_CHANNEL else False
                if AUTH_CHANNEL and first_check:
                    log.info(f"[TRY AGAIN] user_id={query.from_user.id} membership=NOT_JOINED")
                    log.info("[TRY AGAIN] alert_sent=NOT_JOINED")
                    await query.answer("⚠️ Please send a Join Request first.", show_alert=True)
                    return
                    
                log.info(f"[TRY AGAIN] user_id={query.from_user.id} membership=JOINED")
                req["state"] = "SENDING"
                cmd = req["cmd"]
                
                from plugins.commands import start
                class MockMsg:
                    def __init__(self, q, c):
                        self.message = q.message
                        self.chat = q.message.chat
                        self.from_user = q.from_user
                        self.text = f"/start {c}"
                        self.command = ["start", c]
                        self.id = q.message.id
                        self.date = q.message.date
                    def __getattr__(self, name):
                        return getattr(self.message, name)
                    async def reply(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_text(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_photo(self, photo, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_photo(self.chat.id, photo, *args, **kwargs)
                        
                await query.answer()
                
                try:
                    await query.message.delete()
                except Exception as e:
                    pass
                    
                res = await start(client, MockMsg(query, cmd))
                
                req["state"] = "COMPLETED"
                temp.GROUP_MOVIE_REQS.pop(req_id, None)
                return res
                
            elif kk == "all":
                log.info(f"[TRY AGAIN START]\nuser_id={query.from_user.id}\ncallback_data={query.data}\nrequest_key={req_id}")
                req = temp.GETALL.get(req_id)
                if not req:
                    from database.series_db import get_temp_request
                    req = await get_temp_request(req_id)
                if not req:
                    return await query.answer("⚠️ Request expired. Please search again.", show_alert=True)
                if isinstance(req, dict) and "user" in req:
                    if query.from_user.id != req["user"]:
                        return await query.answer("⚠️ This request is not for you.", show_alert=True)
                        
                if isinstance(req, dict) and (req.get("state") in ["SENDING", "COMPLETED"] or req.get("delivery_status") in ["sending", "completed"]):
                    return await query.answer("✅ Files already sent or being sent.", show_alert=True)
                    
                first_check = not await is_subscribed(client, query) if AUTH_CHANNEL else False
                if AUTH_CHANNEL and first_check:
                    log.info(f"[TRY AGAIN MEMBERSHIP]\nstatus=NOT_JOINED\nalert=SHOW_ALERT")
                    return await query.answer("⚠️ Please send a Join Request first.", show_alert=True)
                    
                log.info(f"[TRY AGAIN MEMBERSHIP]\nstatus=JOINED")
                await query.answer()
                
                try:
                    await query.message.delete()
                except Exception as e:
                    pass
                    
                if isinstance(req, dict):
                    req["state"] = "SENDING"
                    req["delivery_status"] = "sending"
                    
                from plugins.commands import start
                class MockMsg2:
                    def __init__(self, q, k, fid):
                        self.message = q.message
                        self.chat = q.message.chat
                        self.from_user = q.from_user
                        self.text = f"/start {k}_{fid}"
                        self.command = ["start", f"{k}_{fid}"]
                        self.id = q.message.id
                        self.date = q.message.date
                    def __getattr__(self, name):
                        return getattr(self.message, name)
                    async def reply(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_text(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_photo(self, photo, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_photo(self.chat.id, photo, *args, **kwargs)
                        
                res = await start(client, MockMsg2(query, kk, req_id))
                
                if isinstance(req, dict):
                    req["state"] = "COMPLETED"
                    req["delivery_status"] = "completed"
                    temp.GETALL.pop(req_id, None)
                return res
                
            elif kk == "series":
                req_key = file_id.split("#")[-1] if "#" in file_id else file_id
                log.info(f"[SERIES TRY AGAIN] clicked user_id={query.from_user.id} request_key={req_key}")
                
                # Check channel membership first
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    log.info(f"[SERIES TRY AGAIN]\nkey={req_key}\nuser_id={query.from_user.id}\nmembership=NOT_JOINED")
                    return await query.answer("⚠️ Please send a Join Request first.", show_alert=True)
                
                # Immediately delete Join Request message upon confirmed membership
                try:
                    if query.message:
                        await query.message.delete()
                        log.info(f"[SERIES TRY AGAIN] Deleted Join Request message for request_key={req_key}")
                except Exception as e:
                    log.warning(f"[SERIES TRY AGAIN] Failed to delete Join Request message: {e}")

                from database.series_db import get_temp_request
                req = temp.SERIES_STATE.get(req_key) or temp.GETALL.get(req_key) or await get_temp_request(req_key)
                if req and (req.get("type") == "movie" or req.get("request_type") == "movie"):
                    from plugins.commands import send_movie_files_to_user
                    req["delivery_status"] = "sending"
                    await send_movie_files_to_user(
                        client=client,
                        user_id=query.from_user.id,
                        files=req.get("files", []),
                        movie_title=req.get("movie_title", req.get("title")),
                        language=req.get("language"),
                        quality=req.get("quality")
                    )
                    req["delivery_status"] = "completed"
                    return
                else:
                    from plugins.series import deliver_series_request
                    await deliver_series_request(client, req_key, query.from_user.id, query=query)
                    return

            elif kk == "main":
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    return await query.answer("⚠️ Please send a Join Request first.", show_alert=True)
                await query.answer("✅ Verification successful!", show_alert=True)
                try:
                    if query.message:
                        await query.message.delete()
                except Exception:
                    pass
                from plugins.commands import start
                class MockMsg3:
                    def __init__(self, q):
                        self.message = q.message
                        self.chat = q.message.chat
                        self.from_user = q.from_user
                        self.text = "/start"
                        self.command = ["start"]
                        self.id = q.message.id
                        self.date = q.message.date
                    def __getattr__(self, name):
                        return getattr(self.message, name)
                    async def reply(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_text(self, text, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_message(self.chat.id, text, *args, **kwargs)
                    async def reply_photo(self, photo, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_photo(self.chat.id, photo, *args, **kwargs)
                    async def reply_sticker(self, sticker, *args, **kwargs):
                        kwargs.pop("reply_to_message_id", None)
                        return await self.message._client.send_sticker(self.chat.id, sticker, *args, **kwargs)
                return await start(client, MockMsg3(query))
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("[FORCE SUB] ERROR: %s", e)
            try:
                await query.answer("⚠️ Verification failed. Please try again.", show_alert=True)
            except:
                pass
            return
    
    elif query.data == "pages":
        await query.answer()
    
    elif query.data.startswith("send_fsall"):
        temp_var, ident, key, offset = query.data.split("#")
        search = BUTTON0.get(key)
     #   if not search:
      #      await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
      #      return
        files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        search = BUTTONS1.get(key)
        files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        search = BUTTONS2.get(key)
        files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        await query.answer(f"Hey {query.from_user.first_name}, All files on this page has been sent successfully to your PM !", show_alert=True)
        
    elif query.data.startswith("send_fall"):
        temp_var, ident, key, offset = query.data.split("#")
        search = FRESH.get(key)
     #   if not search:
       #     await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
      #      return
        files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=int(offset), filter=True)
        await send_all(client, query.from_user.id, files, ident, query.message.chat.id, query.from_user.first_name, query)
        await query.answer(f"Hey {query.from_user.first_name}, All files on this page has been sent successfully to your PM !", show_alert=True)
        
    elif query.data.startswith("killfilesdq"):
        ident, keyword = query.data.split("#")
        #await query.message.edit_text(f"<b>Fetching Files for your query {keyword} on DB... Please wait...</b>")
        files, total = await get_bad_files(keyword)
        await query.message.edit_text("<b>File deletion process will start in 5 seconds !</b>")
        await asyncio.sleep(5)
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_ids = file["file_id"]
                    file_name = file["file_name"]
                    result = col.delete_one({
                        'file_id': file_ids,
                    })
                    if not result.deleted_count:
                        result = sec_col.delete_one({
                            'file_id': file_ids,
                        })
                    if result.deleted_count:
                        logger.info(f'File Found for your query {keyword}! Successfully deleted {file_name} from database.')
                    deleted += 1
                    if deleted % 50 == 0:
                        await query.message.edit_text(f"<b>Process started for deleting files from DB. Successfully deleted {str(deleted)} files from DB for your query {keyword} !\n\nPlease wait...</b>")
            except Exception as e:
                logger.exception(e)
                await query.message.edit_text(f'Error: {e}')
            else:
                await query.message.edit_text(f"<b>Process Completed for file deletion !\n\nSuccessfully deleted {str(deleted)} files from database for your query {keyword}.</b>")
    
    elif query.data.startswith("opnsetgrp"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)
            return
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML
            )
            await query.message.edit_reply_markup(reply_markup)
        
    elif query.data.startswith("opnsetpm"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)
            return
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        btn2 = [[
                 InlineKeyboardButton("Cʜᴇᴄᴋ PM", url=f"telegram.me/{temp.U_NAME}")
               ]]
        reply_markup = InlineKeyboardMarkup(btn2)
        await query.message.edit_text(f"<b>Yᴏᴜʀ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ ғᴏʀ {title} ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ʏᴏᴜʀ PM</b>")
        await query.message.edit_reply_markup(reply_markup)
        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await client.send_message(
                chat_id=userid,
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=query.message.id
            )

    elif query.data.startswith("show_option"):
        ident, from_user = query.data.split("#")
        btn = [[
                InlineKeyboardButton("Uɴᴀᴠᴀɪʟᴀʙʟᴇ", callback_data=f"unavailable#{from_user}"),
                InlineKeyboardButton("Uᴘʟᴏᴀᴅᴇᴅ", callback_data=f"uploaded#{from_user}")
             ],[
                InlineKeyboardButton("Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ", callback_data=f"already_available#{from_user}")
              ]]
        btn2 = [[
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴏᴘᴛɪᴏɴs !")
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
        
    elif query.data.startswith("unavailable"):
        ident, from_user = query.data.split("#")
        btn = [[
                InlineKeyboardButton("⚠️ Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️", callback_data=f"unalert#{from_user}")
              ]]
        btn2 = [[
                 InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uɴᴀᴠᴀɪʟᴀʙʟᴇ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Sᴏʀʀʏ Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Sᴏʀʀʏ Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("uploaded"):
        ident, from_user = query.data.split("#")
        btn = [[
                InlineKeyboardButton("✅ Uᴘʟᴏᴀᴅᴇᴅ ✅", callback_data=f"upalert#{from_user}")
              ]]
        btn2 = [[
                 InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ],[
                 InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https://t.me/+KzbVzahVdqQ3MmM1")
               ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uᴘʟᴏᴀᴅᴇᴅ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("already_available"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton("🟢 Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ 🟢", callback_data=f"alalert#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
        ],[
            InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https://t.me/vj_bots")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !")
            try:
                await client.send_message(chat_id=int(from_user), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴏᴜʀ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
            except UserIsBlocked:
                await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴏᴜʀ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ. Tᴏ sᴇɴᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ PM, Mᴜsᴛ ᴜɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn2))
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("alalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("upalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uᴘʟᴏᴀᴅᴇᴅ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
        
    elif query.data.startswith("unalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(f"Hᴇʏ {user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uɴᴀᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("generate_stream_link"):
        _, file_id = query.data.split(":")
        try:
            log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=file_id)
            fileName = {quote_plus(get_name(log_msg))}
            stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
            download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
            button = [[
                InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
            ],[
                InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(button))
        except Exception as e:
            print(e)
            await query.answer(f"something went wrong\n\n{e}", show_alert=True)
            return
    
    elif query.data == "reqinfo":
        await query.answer(text=script.REQINFO, show_alert=True)

    elif query.data == "select":
        await query.answer(text=script.SELECT, show_alert=True)

    elif query.data == "sinfo":
        await query.answer(text=script.SINFO, show_alert=True)

    elif query.data == "start":
        if PREMIUM_AND_REFERAL_MODE == True:
            buttons = [[
                InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
            ]]
        else:
            buttons = [[
                InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
            ]]
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('ᴄʀᴇᴀᴛᴇ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer(MSG_ALRT)

    elif query.data == "clone":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='start')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CLONE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "filters":
        buttons = [[
            InlineKeyboardButton('Mᴀɴᴜᴀʟ FIʟᴛᴇʀ', callback_data='manuelfilter'),
            InlineKeyboardButton('Aᴜᴛᴏ FIʟᴛᴇʀ', callback_data='autofilter')
        ],[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('Gʟᴏʙᴀʟ Fɪʟᴛᴇʀs', callback_data='global_filters')
        ]]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.ALL_FILTERS.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "global_filters":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.GFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "help":
        buttons = [[
             InlineKeyboardButton('⚙️ ᴀᴅᴍɪɴ ᴏɴʟʏ 🔧', callback_data='admin'),
         ], [ 
             InlineKeyboardButton('ʀᴇɴᴀᴍᴇ', callback_data='r_txt'),   
             InlineKeyboardButton('sᴛʀᴇᴀᴍ/ᴅᴏᴡɴʟᴏᴀᴅ', callback_data='s_txt') 
         ], [ 
             InlineKeyboardButton('ꜰɪʟᴇ ꜱᴛᴏʀᴇ', callback_data='store_file'),   
             InlineKeyboardButton('ᴛᴇʟᴇɢʀᴀᴘʜ', callback_data='tele') 
         ], [ 
             InlineKeyboardButton('ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ', callback_data='coct'), 
             InlineKeyboardButton('ꜰɪʟᴛᴇʀꜱ', callback_data='filters')
         ], [
             InlineKeyboardButton('ʏᴛ-ᴅʟ', callback_data='ytdl'), 
             InlineKeyboardButton('ꜱʜᴀʀᴇ ᴛᴇxᴛ', callback_data='share')
         ], [
             InlineKeyboardButton('ꜱᴏɴɢ', callback_data='song'),
             InlineKeyboardButton('ᴇᴀʀɴ ᴍᴏɴᴇʏ', callback_data='shortlink_info')
         ], [
             InlineKeyboardButton('ꜱᴛɪᴄᴋᴇʀ-ɪᴅ', callback_data='sticker'),
             InlineKeyboardButton('ᴊ-ꜱᴏɴ', callback_data='json')
         ], [             
             InlineKeyboardButton('🏠 𝙷𝙾𝙼𝙴 🏠', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
            InlineKeyboardButton('Sᴏᴜʀᴄᴇ Cᴏᴅᴇ', url="https://github.com/VJBots/VJ-FILTER-BOT")
        ],[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, OWNER_LNK),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "subscription":
        buttons = [[
            InlineKeyboardButton('⇚Back', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.SUBSCRIPTION_TXT.format(REFERAL_PREMEIUM_TIME, temp.U_NAME, query.from_user.id, REFERAL_COUNT),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters'),
            InlineKeyboardButton('Bᴜᴛᴛᴏɴs', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='manuelfilter')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('ᴇxᴛʀᴀ', callback_data='extra')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "store_file":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FILE_STORE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "r_txt":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.RENAME_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "s_txt":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.STREAM_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='admin')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT.format(OWNER_LNK, CHNL_LNK),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        total_users = await db.total_users_count()
        totl_chats = await db.total_chat_count()
        filesp = col.count_documents({})
        totalsec = sec_col.count_documents({})
        stats = vjdb.command('dbStats')
        used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))
        free_dbSize = 512-used_dbSize
        stats2 = sec_db.command('dbStats')
        used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
        free_dbSize2 = 512-used_dbSize2
        stats3 = mydb.command('dbStats')
        used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats3['indexSize']/(1024*1024))
        free_dbSize3 = 512-used_dbSize3
        await query.message.edit_text(
            text=script.STATUS_TXT.format((int(filesp)+int(totalsec)), total_users, totl_chats, filesp, round(used_dbSize, 2), round(free_dbSize, 2), totalsec, round(used_dbSize2, 2), round(free_dbSize2, 2), round(used_dbSize3, 2), round(free_dbSize3, 2)),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        total_users = await db.total_users_count()
        totl_chats = await db.total_chat_count()
        filesp = col.count_documents({})
        totalsec = sec_col.count_documents({})
        stats = vjdb.command('dbStats')
        used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))
        free_dbSize = 512-used_dbSize
        stats2 = sec_db.command('dbStats')
        used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
        free_dbSize2 = 512-used_dbSize2
        stats3 = mydb.command('dbStats')
        used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats3['indexSize']/(1024*1024))
        free_dbSize3 = 512-used_dbSize3
        await query.message.edit_text(
            text=script.STATUS_TXT.format((int(filesp)+int(totalsec)), total_users, totl_chats, filesp, round(used_dbSize, 2), round(free_dbSize, 2), totalsec, round(used_dbSize2, 2), round(free_dbSize2, 2), round(used_dbSize3, 2), round(free_dbSize3, 2)),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "shortlink_info":
        btn = [[
            InlineKeyboardButton("👇Select Your Language 👇", callback_data="laninfo")
        ],[
            InlineKeyboardButton("Tamil", callback_data="tamil_info"),
            InlineKeyboardButton("English", callback_data="english_info"),
            InlineKeyboardButton("Hindi", callback_data="hindi_info")
        ],[
            InlineKeyboardButton("Malayalam", callback_data="malayalam_info"),
            InlineKeyboardButton("Urdu", callback_data="urdu_info"),
            InlineKeyboardButton("Bangla", callback_data="bangladesh_info")
        ],[
            InlineKeyboardButton("Telugu", callback_data="telugu_info"),
            InlineKeyboardButton("Kannada", callback_data="kannada_info"),
            InlineKeyboardButton("Gujarati", callback_data="gujarati_info")
        ],[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.SHORTLINK_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tele":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVJ01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.TELE_TXT),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "ytdl":
        buttons = [[
            InlineKeyboardButton('⇍ ʙᴀᴄᴋ ⇏', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text="● ◌ ◌"
        )
        await query.message.edit_text(
            text="● ● ◌"
        )
        await query.message.edit_text(
            text="● ● ●"
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.YTDL_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "share":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.SHARE_TXT),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "song":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.SONG_TXT),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "json":
        buttons = [[
            InlineKeyboardButton('⇍ ʙᴀᴄᴋ ⇏', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text="● ◌ ◌"
        )
        await query.message.edit_text(
            text="● ● ◌"
        )
        await query.message.edit_text(
            text="● ● ●"
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.JSON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "sticker":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.STICKER_TXT),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tamil_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.TAMIL_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "english_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.ENGLISH_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "hindi_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.HINDI_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "telugu_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.TELUGU_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "malayalam_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.MALAYALAM_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "urdu_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.URDU_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "bangladesh_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.BANGLADESH_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "kannada_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/KingVj01")
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_text(
            text=(script.KANNADA_INFO),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Yᴏᴜʀ Aᴄᴛɪᴠᴇ Cᴏɴɴᴇᴄᴛɪᴏɴ Hᴀs Bᴇᴇɴ Cʜᴀɴɢᴇᴅ. Gᴏ Tᴏ /connections ᴀɴᴅ ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ.")
            return await query.answer(MSG_ALRT)

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            settings = await get_settings(grpid)
            if set_type == "is_shortlink" and not settings['shortlink']:
                return await query.answer(text = "First Add Your Shortlink Url And Api By /shortlink Command, Then Turn Me On.", show_alert = True)
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('5 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ',
                                         callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}',
                                         callback_data=f'setgs#max_btn#{settings["max_btn"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ',
                                         callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer(MSG_ALRT)

async def auto_filter(client, name, msg, reply_msg=None, ai_search=True, spoll=False):
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    if not spoll:
        message = msg
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\\/|^,|^!|^\\.).*)", message.text):
            return
        if len(message.text) < 100:
            user_id = message.from_user.id if (hasattr(message, "from_user") and message.from_user) else (message.sender_chat.id if getattr(message, "sender_chat", None) else 0)
            from info import ADMINS
            is_admin = user_id in ADMINS
            is_owner = (user_id == ADMINS[0]) if (ADMINS and len(ADMINS) > 0) else False
            chat_type = str(message.chat.type if message.chat else "UNKNOWN")

            logger.info(
                f"[NORMAL SEARCH ROUTE]\n"
                f"user_id={user_id}\n"
                f"is_admin={is_admin}\n"
                f"is_owner={is_owner}\n"
                f"chat_type={chat_type}\n"
                f"query={name}"
            )

            search = EMOJI_PATTERN.sub(" ", name)
            search = re.sub(r"[\.\_\-\:\+\/\\\[\]\(\)\{\}\#\@\*\&]+", " ", search)
            search = re.sub(r"(?i)\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)|with\ssubtitle(s)?|upload|full|print|file)\b", " ", search)
            search = re.sub(r"\s+", " ", search).strip()

            # -- 1. Check Unified Movie & Series Filter Search --
            try:
                from plugins.series import process_unified_filter_search
                is_handled = await process_unified_filter_search(client, message, search if search else name, reply_msg)
                if is_handled:
                    return
            except Exception as e:
                logger.error(f"[UNIFIED FILTER SEARCH ROUTING ERROR] {e}")

            # -- 3. Normal Movie Filter (ia_filterdb) --
            page_limit = int(MAX_B_TN) if MAX_B_TN else 5
            files, offset, total_results = await get_search_results(message.chat.id, search, max_results=page_limit, offset=0, filter=True)
            logger.info(
                f"[FILE SEARCH]\n"
                f"query={search}\n"
                f"matches={len(files) if files else 0}"
            )
            settings = await get_settings(message.chat.id)

            if not files:
                logger.info(f"[SEARCH ROUTE] type=no_result query={search}")
                # -- 4. Route to Spell Check / Suggestions --
                if settings.get("spell_check", True):
                    return await advantage_spell_chok(client, search if search else name, message, reply_msg, True)

                # If spell check disabled, show not found / reason
                no_db_btn = InlineKeyboardMarkup([[InlineKeyboardButton(chr(0x1F9A8) + " Reason", callback_data="not_in_db_reason")]])
                msg_text = (
                    "<b>sᴏʀʀʏ ɴᴏ ꜰɪʟᴇs ᴡᴇʀᴇ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ😕\n\n"
                    "ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴘᴇʟʟɪɴɢ ɪɴ ɢᴏᴏɢʟᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ 😃\n\n"
                    "<i>🕐 This message will be deleted in 50 seconds.</i></b>"
                )
                if reply_msg:
                    msg_obj = await reply_msg.edit_text(msg_text, reply_markup=no_db_btn)
                else:
                    msg_obj = await message.reply_text(msg_text, reply_markup=no_db_btn)

                await asyncio.sleep(50)
                try:
                    if msg_obj:
                        await msg_obj.delete()
                    await message.delete()
                except Exception:
                    pass
                return
        else:
            return
    else:
        search, files, offset, total_results = spoll
        if hasattr(msg, "message") and msg.message:
            message = msg.message.reply_to_message if msg.message.reply_to_message else msg.message
        else:
            message = msg
        settings = await get_settings(message.chat.id)
        try:
            await msg.message.delete()
        except:
            pass
    pre = 'filep' if settings['file_secure'] else 'file'
    key = f"{message.chat.id}-{message.id}"
    req = msg.from_user.id if (hasattr(msg, 'from_user') and msg.from_user) else (message.from_user.id if (message and message.from_user) else 0)
    if not req and message.chat.type == enums.ChatType.PRIVATE:
        req = message.chat.id
    BUTTON_OWNERS[key] = req
    FRESH[key] = search
    BUTTONS[key] = search
    temp.GETALL[key] = files
    if req:
        temp.SHORT[req] = message.chat.id

    btn = [
        [
            InlineKeyboardButton(
                text=f"[{get_size(filevj['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), filevj['file_name'].split()))}",
                callback_data=f"{pre}#{filevj['file_id']}"
            ),
        ]
        for filevj in files
    ]
    btn.insert(0, [
        InlineKeyboardButton("🔹 𝐒𝐞𝐧𝐝 𝐀𝐥𝐥 🔹", callback_data=f"sendfiles#{key}")
    ])
    if offset != "":
        req_id = message.from_user.id if (hasattr(message, "from_user") and message.from_user) else 0
        btn.append(
            [InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"), InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_B_TN))}", callback_data="pages"), InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪", callback_data=f"next_{req_id}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="𝐍𝐎 𝐌𝐎𝐑𝐄 𝐏𝐀𝐆𝐄𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄", callback_data="pages")]
        )

    imdb = None
    if settings.get("imdb", True):
        try:
            first_fname = (files[0]).get('file_name') if files else None
            imdb = await get_poster(search, file=first_fname)
        except Exception as ie:
            logger.warning(f"[MOVIE FILTER IMDb fetch failed for '{search}']: {ie}")
            imdb = None

    cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
    remaining_seconds = "{:.2f}".format(time_difference.total_seconds())

    TEMPLATE = script.IMDB_TEMPLATE_TXT
    if imdb:
        try:
            cap = TEMPLATE.format(
                qurey=search,
                title=imdb.get('title', search),
                votes=imdb.get('votes', ''),
                aka=imdb.get("aka", ''),
                seasons=imdb.get("seasons", ''),
                box_office=imdb.get('box_office', ''),
                localized_title=imdb.get('localized_title', ''),
                kind=imdb.get('kind', ''),
                imdb_id=imdb.get("imdb_id", ''),
                cast=imdb.get("cast", ''),
                runtime=imdb.get("runtime", ''),
                countries=imdb.get("countries", ''),
                certificates=imdb.get("certificates", ''),
                languages=imdb.get("languages", ''),
                director=imdb.get("director", ''),
                writer=imdb.get("writer", ''),
                producer=imdb.get("producer", ''),
                composer=imdb.get("composer", ''),
                cinematographer=imdb.get("cinematographer", ''),
                music_team=imdb.get("music_team", ''),
                distributors=imdb.get("distributors", ''),
                release_date=imdb.get('release_date', ''),
                year=imdb.get('year', ''),
                genres=imdb.get('genres', ''),
                poster=imdb.get('poster', ''),
                plot=imdb.get('plot', ''),
                rating=imdb.get('rating', ''),
                url=imdb.get('url', ''),
                **locals()
            )
            if hasattr(message, "from_user") and message.from_user:
                temp.IMDB_CAP[message.from_user.id] = cap
        except Exception:
            cap = f"<b>🎬 {search.title()}\n\n📁 Select File to Download:</b>"
    else:
        cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {message.from_user.mention if (hasattr(message, 'from_user') and message.from_user) else 'User'}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {message.chat.title if message.chat else ''} \n\n⚠️ ᴀꜰᴛᴇʀ 10 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"

    reply_markup = InlineKeyboardMarkup(btn)
    from utils import safe_delete_message
    if imdb and imdb.get('poster'):
        try:
            hehe = await message.reply_photo(photo=imdb.get('poster'), caption=cap, reply_markup=reply_markup)
            if reply_msg:
                await safe_delete_message(client, reply_msg.chat.id, reply_msg.id)
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await safe_delete_message(client, hehe.chat.id, hehe.id)
                    await safe_delete_message(client, message.chat.id, message.id)
            except KeyError:
                await save_group_settings(message.chat.id, 'auto_delete', True)
                await asyncio.sleep(600)
                await safe_delete_message(client, hehe.chat.id, hehe.id)
                await safe_delete_message(client, message.chat.id, message.id)
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            poster_alt = (imdb.get('poster') or '').replace('.jpg', "._V1_UX360.jpg") 
            hmm = await message.reply_photo(photo=poster_alt, caption=cap, reply_markup=reply_markup)
            if reply_msg:
                await safe_delete_message(client, reply_msg.chat.id, reply_msg.id)
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    await safe_delete_message(client, hmm.chat.id, hmm.id)
                    await safe_delete_message(client, message.chat.id, message.id)
            except KeyError:
                await save_group_settings(message.chat.id, 'auto_delete', True)
                await asyncio.sleep(600)
                await safe_delete_message(client, hmm.chat.id, hmm.id)
                await safe_delete_message(client, message.chat.id, message.id)
        except Exception as e:
            logger.exception(e) 
            if reply_msg:
                fek = await reply_msg.edit_text(text=cap, reply_markup=reply_markup)
            else:
                fek = await message.reply_text(text=cap, reply_markup=reply_markup)
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(600)
                    if fek:
                        await safe_delete_message(client, fek.chat.id, fek.id)
                    await safe_delete_message(client, message.chat.id, message.id)
            except KeyError:
                await save_group_settings(message.chat.id, 'auto_delete', True)
                await asyncio.sleep(600)
                if fek:
                    await safe_delete_message(client, fek.chat.id, fek.id)
                await safe_delete_message(client, message.chat.id, message.id)
    else:
        if reply_msg:
            fuk = await reply_msg.edit_text(text=cap, reply_markup=reply_markup, disable_web_page_preview=True)
        else:
            fuk = await message.reply_text(text=cap, reply_markup=reply_markup, disable_web_page_preview=True)
        
        try:
            if settings['auto_delete']:
                await asyncio.sleep(600)
                if fuk:
                    await safe_delete_message(client, fuk.chat.id, fuk.id)
                await safe_delete_message(client, message.chat.id, message.id)
        except KeyError:
            await save_group_settings(message.chat.id, 'auto_delete', True)
            await asyncio.sleep(600)
            if fuk:
                await safe_delete_message(client, fuk.chat.id, fuk.id)
            await safe_delete_message(client, message.chat.id, message.id)

async def advantage_spell_chok(client, name, msg, reply_msg, vj_search):
    mv_id = msg.id
    mv_rqst = name
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1) if reqstr1 else None
    settings = await get_settings(msg.chat.id)

    # 1. First check if any saved filters match in database (Super Movies & Series)
    from database.series_db import search_super_movies, search_series
    saved_movies = await search_super_movies(mv_rqst)
    saved_series = await search_series(mv_rqst)

    valid_movies = [m for m in saved_movies if m.get("file_ids")]
    valid_series = saved_series

    if valid_movies or valid_series:
        from plugins.series import process_unified_filter_search
        return await process_unified_filter_search(client, msg, mv_rqst, reply_msg)

    # 2. No saved filter in database -> Check IMDb / TMDB for movie metadata
    imdb = None
    try:
        imdb = await get_poster(mv_rqst)
    except Exception as e:
        logger.warning(f"[IMDB NO-RESULT LOOKUP ERROR] {e}")

    reason_btn = [[
        InlineKeyboardButton(chr(0x1F9A8) + " Reason", callback_data="not_in_db_reason")
    ]]
    markup = InlineKeyboardMarkup(reason_btn)

    if imdb and imdb.get("title"):
        title = imdb.get("title")
        year = str(imdb.get("year", "")).strip()
        year_str = f" ({year})" if year and year != "N/A" else ""
        rating = str(imdb.get("rating", "")).strip()
        rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
        genres = imdb.get("genres") or imdb.get("genre") or ""
        genre_str = f"\n🎭 <b>Genre:</b> {genres}" if genres and genres != "N/A" else ""
        poster = imdb.get("poster")

        cap = (
            f"🎬 <b>{title}{year_str}</b>"
            f"{rating_str}"
            f"{genre_str}\n\n"
            f"😕 <b>Requested content is currently not available in our database.</b>\n\n"
            f"<i>🕐 This message will be deleted in 50 seconds.</i>"
        )

        sent_msg = None
        if poster:
            try:
                if reply_msg:
                    if reply_msg.photo:
                        try:
                            sent_msg = await reply_msg.edit_media(
                                media=InputMediaPhoto(media=poster, caption=cap, parse_mode=enums.ParseMode.HTML),
                                reply_markup=markup
                            )
                        except Exception:
                            sent_msg = await reply_msg.edit_caption(caption=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                    else:
                        try:
                            await reply_msg.delete()
                        except Exception:
                            pass
                        sent_msg = await msg.reply_photo(photo=poster, caption=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                else:
                    sent_msg = await msg.reply_photo(photo=poster, caption=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            except Exception as pe:
                logger.warning(f"[NO RESULT PHOTO SEND ERROR] {pe}")
                if reply_msg:
                    sent_msg = await reply_msg.edit_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                else:
                    sent_msg = await msg.reply_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        else:
            if reply_msg:
                sent_msg = await reply_msg.edit_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            else:
                sent_msg = await msg.reply_text(text=cap, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

        await asyncio.sleep(50)
        try:
            if sent_msg:
                await sent_msg.delete()
            await msg.delete()
        except Exception:
            pass
        return

    # 3. Not in IMDb / TMDB either -> Standard non-result message
    msg_text = (
        "<b>sᴏʀʀʏ ɴᴏ ꜰɪʟᴇs ᴡᴇʀᴇ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ😕\n\n"
        "ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴘᴇʟʟɪɴɢ ɪɴ ɢᴏᴏɢʟᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ 😃\n\n"
        "<i>🕐 This message will be deleted in 50 seconds.</i></b>"
    )

    sent_msg = None
    if reply_msg:
        sent_msg = await reply_msg.edit_text(msg_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    else:
        sent_msg = await msg.reply_text(msg_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    await asyncio.sleep(50)
    try:
        if sent_msg:
            await sent_msg.delete()
        await msg.delete()
    except Exception:
        pass

async def manual_filters(client, message, text=False):
    settings = await get_settings(message.chat.id)
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            joelkb = await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                protect_content=True if settings["file_secure"] else False,
                                reply_to_message_id=reply_id
                            )
                            try:
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                                    try:
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                else:
                                    try:
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_ffilter', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)

                        else:
                            button = eval(btn)
                            joelkb = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                protect_content=True if settings["file_secure"] else False,
                                reply_to_message_id=reply_id
                            )
                            try:
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                                    try:
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                else:
                                    try:
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_ffilter', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                    elif btn == "[]":
                        joelkb = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            protect_content=True if settings["file_secure"] else False,
                            reply_to_message_id=reply_id
                        )
                        try:
                            if settings['auto_ffilter']:
                                ai_search = True
                                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                await auto_filter(client, message.text, message, reply_msg, ai_search)
                                try:
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                            else:
                                try:
                                    if settings['auto_delete']:
                                        await asyncio.sleep(600)
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await asyncio.sleep(600)
                                        await joelkb.delete()
                        except KeyError:
                            grpid = await active_connection(str(message.from_user.id))
                            await save_group_settings(grpid, 'auto_ffilter', True)
                            settings = await get_settings(message.chat.id)
                            if settings['auto_ffilter']:
                                ai_search = True
                                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                await auto_filter(client, message.text, message, reply_msg, ai_search)
                    else:
                        button = eval(btn)
                        joelkb = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                        try:
                            if settings['auto_ffilter']:
                                ai_search = True
                                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                await auto_filter(client, message.text, message, reply_msg, ai_search)
                                try:
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                            else:
                                try:
                                    if settings['auto_delete']:
                                        await asyncio.sleep(600)
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await asyncio.sleep(600)
                                        await joelkb.delete()
                        except KeyError:
                            grpid = await active_connection(str(message.from_user.id))
                            await save_group_settings(grpid, 'auto_ffilter', True)
                            settings = await get_settings(message.chat.id)
                            if settings['auto_ffilter']:
                                ai_search = True
                                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                await auto_filter(client, message.text, message, reply_msg, ai_search)

                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False

async def global_filters(client, message, text=False):
    settings = await get_settings(message.chat.id)
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            joelkb = await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                reply_to_message_id=reply_id
                            )
                            manual = await manual_filters(client, message)
                            if manual == False:
                                settings = await get_settings(message.chat.id)
                                try:
                                    if settings['auto_ffilter']:
                                        ai_search = True
                                        reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                        await auto_filter(client, message.text, message, reply_msg, ai_search)
                                        try:
                                            if settings['auto_delete']:
                                                await joelkb.delete()
                                        except KeyError:
                                            grpid = await active_connection(str(message.from_user.id))
                                            await save_group_settings(grpid, 'auto_delete', True)
                                            settings = await get_settings(message.chat.id)
                                            if settings['auto_delete']:
                                                await joelkb.delete()
                                    else:
                                        try:
                                            if settings['auto_delete']:
                                                await asyncio.sleep(600)
                                                await joelkb.delete()
                                        except KeyError:
                                            grpid = await active_connection(str(message.from_user.id))
                                            await save_group_settings(grpid, 'auto_delete', True)
                                            settings = await get_settings(message.chat.id)
                                            if settings['auto_delete']:
                                                await asyncio.sleep(600)
                                                await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_ffilter', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_ffilter']:
                                        ai_search = True
                                        reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                        await auto_filter(client, message.text, message, reply_msg, ai_search) 
                            else:
                                try:
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                            
                        else:
                            button = eval(btn)
                            joelkb = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                            manual = await manual_filters(client, message)
                            if manual == False:
                                settings = await get_settings(message.chat.id)
                                try:
                                    if settings['auto_ffilter']:
                                        ai_search = True
                                        reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                        await auto_filter(client, message.text, message, reply_msg, ai_search)
                                        try:
                                            if settings['auto_delete']:
                                                await joelkb.delete()
                                        except KeyError:
                                            grpid = await active_connection(str(message.from_user.id))
                                            await save_group_settings(grpid, 'auto_delete', True)
                                            settings = await get_settings(message.chat.id)
                                            if settings['auto_delete']:
                                                await joelkb.delete()
                                    else:
                                        try:
                                            if settings['auto_delete']:
                                                await asyncio.sleep(600)
                                                await joelkb.delete()
                                        except KeyError:
                                            grpid = await active_connection(str(message.from_user.id))
                                            await save_group_settings(grpid, 'auto_delete', True)
                                            settings = await get_settings(message.chat.id)
                                            if settings['auto_delete']:
                                                await asyncio.sleep(600)
                                                await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_ffilter', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_ffilter']:
                                        ai_search = True
                                        reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                        await auto_filter(client, message.text, message, reply_msg, ai_search)
                            else:
                                try:
                                    if settings['auto_delete']:
                                        await joelkb.delete()
                                except KeyError:
                                    grpid = await active_connection(str(message.from_user.id))
                                    await save_group_settings(grpid, 'auto_delete', True)
                                    settings = await get_settings(message.chat.id)
                                    if settings['auto_delete']:
                                        await joelkb.delete()

                    elif btn == "[]":
                        joelkb = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                        manual = await manual_filters(client, message)
                        if manual == False:
                            settings = await get_settings(message.chat.id)
                            try:
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                                    try:
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                else:
                                    try:
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_ffilter', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search) 
                        else:
                            try:
                                if settings['auto_delete']:
                                    await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_delete', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_delete']:
                                    await joelkb.delete()

                    else:
                        button = eval(btn)
                        joelkb = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                        manual = await manual_filters(client, message)
                        if manual == False:
                            settings = await get_settings(message.chat.id)
                            try:
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                                    try:
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await joelkb.delete()
                                else:
                                    try:
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                                    except KeyError:
                                        grpid = await active_connection(str(message.from_user.id))
                                        await save_group_settings(grpid, 'auto_delete', True)
                                        settings = await get_settings(message.chat.id)
                                        if settings['auto_delete']:
                                            await asyncio.sleep(600)
                                            await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_ffilter', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_ffilter']:
                                    ai_search = True
                                    reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                                    await auto_filter(client, message.text, message, reply_msg, ai_search)
                        else:
                            try:
                                if settings['auto_delete']:
                                    await joelkb.delete()
                            except KeyError:
                                grpid = await active_connection(str(message.from_user.id))
                                await save_group_settings(grpid, 'auto_delete', True)
                                settings = await get_settings(message.chat.id)
                                if settings['auto_delete']:
                                    await joelkb.delete()

                                
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
