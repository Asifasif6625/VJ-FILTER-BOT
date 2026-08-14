# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01
#
# ─── series.py — Series & Episode Management System ──────────────────────────
#
# Admin commands:   /seriesfil   — create / manage series
#                   /sbatch      — add episode batch from channel link range
# User flow:        Search series name in group → Language → Season → Episode → Quality → File
#

import re
import logging
import asyncio
from datetime import datetime

from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    ForceReply,
)
from pyrogram.errors import (
    FloodWait,
    MessageNotModified,
    BadRequest,
    ChatAdminRequired,
)

from info import ADMINS, CHANNELS
from database.series_db import (
    create_series,
    get_series,
    get_series_by_name,
    search_series,
    update_series,
    list_all_series,
    add_series_file,
    replace_series_file,
    get_series_files,
    list_series_languages,
    list_series_seasons,
    list_season_qualities,
    list_quality_episodes,
    save_batch,
    get_batches,
    _ensure_indexes,
    _normalize,
)

logger = logging.getLogger(__name__)

from utils import temp

# ─── Wizard State Names ───────────────────────────────────────────────────────
S_NAME         = "WAITING_NAME"
S_YEAR         = "WAITING_YEAR"
S_GENRE        = "WAITING_GENRE"
S_RATING       = "WAITING_RATING"
S_DESC         = "WAITING_DESCRIPTION"
S_POSTER       = "WAITING_POSTER"
S_LANGS        = "SELECTING_LANGUAGES"
S_SEASONS      = "SELECTING_SEASONS"
S_QUALITY      = "SELECTING_QUALITY"
S_BATCH_LANG   = "BATCH_SELECT_LANG"
S_BATCH_SEASON = "BATCH_SELECT_SEASON"
S_BATCH_QUAL   = "BATCH_SELECT_QUAL"
S_BATCH_WAIT   = "WAITING_BATCH"
S_BATCH_CONF   = "CONFIRMING_BATCH"
S_DONE         = "SAVED"

# ─── Language / Season / Quality choices ─────────────────────────────────────
LANG_OPTIONS = [
    "Malayalam", "English", "Hindi", "Tamil", "Telugu",
    "Kannada", "Bengali", "Marathi", "German", "Korean",
    "Japanese", "Spanish", "French", "Other",
]
QUALITY_OPTIONS = [
    "360p", "480p", "720p", "1080p", "2160p/4K",
    "WEB-DL", "BluRay", "HDRip", "DVDRip",
]
MAX_SEASONS = 15


# ═════════════════════════════════════════════════════════════════════════════
# ─── HELPERS ─────────────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

def _is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def _parse_tg_link(link: str) -> tuple[int | str | None, int | None]:
    """
    Parse a Telegram message link.
    Supports:
      https://t.me/channelname/12345
      https://t.me/c/1234567890/12345
    Returns (chat_identifier, message_id).
    chat_identifier is either '@username' or '-100<chat_id>'.
    """
    link = link.strip()
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    match = regex.match(link)
    if match:
        chat_id = match.group(4)
        msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
        else:
            chat_id = "@" + chat_id
        return chat_id, msg_id
    return None, None


def _series_short_id(series_id: str) -> str:
    """Use last 8 chars of ObjectId to keep callback data short."""
    return series_id[-8:]


def _extract_episode_number(text: str) -> int | None:
    if not text:
        return None
    
    # Common patterns: S01E01, S1E1, E01, Episode 1, EP 01
    patterns = [
        r"S\d{1,2}[\s\-]?E(\d{1,3})", # S01E01, S1 E1, S01-E01
        r"E[P]?[\s\-]?(\d{1,3})",     # E01, EP01, EP 01, E-01
        r"Episode[\s\-]?(\d{1,3})",   # Episode 1, Episode-01
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


# Reverse lookup: short_id → full_id (populated at runtime)
_SERIES_ID_MAP: dict[str, str] = {}


async def _get_full_id(short_id: str) -> str | None:
    """Resolve a short_id back to full ObjectId string."""
    if short_id in _SERIES_ID_MAP:
        return _SERIES_ID_MAP[short_id]
    # Fallback: search DB for series whose _id ends in short_id
    from database.series_db import series_col
    cursor = series_col.find({"status": "active"})
    async for doc in cursor:
        full = str(doc["_id"])
        _SERIES_ID_MAP[full[-8:]] = full
    return _SERIES_ID_MAP.get(short_id)


def _register_short_id(full_id: str):
    _SERIES_ID_MAP[full_id[-8:]] = full_id


def _series_card(series: dict) -> str:
    """Build a formatted text card for a series."""
    name  = series.get("name", "?")
    year  = series.get("year", "N/A")
    genre = series.get("genre", "N/A")
    rating = series.get("rating", "")
    desc  = series.get("description", "")
    
    card = f"📺 <b>{name}</b>\n\n"
    if year and year != "N/A":
        card += f"📅 <b>Year:</b> {year}\n"
    if genre and genre != "N/A":
        card += f"🎭 <b>Genre:</b> {genre}\n"
    if rating:
        card += f"⭐ <b>Rating:</b> {rating}\n"
    if desc:
        card += f"\n📝 {desc[:300]}"
    return card


# ═════════════════════════════════════════════════════════════════════════════
# ─── ADMIN WIZARD KEYBOARD BUILDERS ──────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

def _lang_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(LANG_OPTIONS), 3):
        row = []
        for lang in LANG_OPTIONS[i:i+3]:
            tick = "🟢 " if lang in selected else ""
            row.append(InlineKeyboardButton(
                f"{tick}{lang}",
                callback_data=f"sw#lang#{lang}"
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("🟢 Submit Languages", callback_data="sw#lang#submit"),
        InlineKeyboardButton("🔴 Cancel",            callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _season_keyboard(total: int, selected: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, total, 4):
        row = []
        for n in range(i+1, min(i+5, total+1)):
            tick = "✅ " if n in selected else ""
            row.append(InlineKeyboardButton(
                f"{tick}S{n}",
                callback_data=f"sw#season#{n}"
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("🟢 Submit Seasons", callback_data="sw#season#submit"),
        InlineKeyboardButton("⏭ Skip (None)",       callback_data="sw#season#skip"),
    ])
    rows.append([
        InlineKeyboardButton("🔴 Cancel",          callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _quality_keyboard(
    selected: list[str],
    already_saved: list[str] = None,
) -> InlineKeyboardMarkup:
    """
    selected      — qualities chosen for the CURRENT batch (shown with 🟢)
    already_saved — qualities already committed to the series (shown with ✅)
                    They are still tap-able; the tick is purely informational.
    """
    already_saved = already_saved or []
    rows = []
    for i in range(0, len(QUALITY_OPTIONS), 3):
        row = []
        for q in QUALITY_OPTIONS[i:i+3]:
            if q in selected:
                tick = "🟢 "        # active in current batch selection
            elif q in already_saved:
                tick = "✅ "        # already saved to this series
            else:
                tick = ""
            row.append(InlineKeyboardButton(
                f"{tick}{q}",
                callback_data=f"sw#quality#{q}"
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("🟢 Submit Quality", callback_data="sw#quality#submit"),
        InlineKeyboardButton("🔴 Cancel",           callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _config_menu_keyboard(series_id: str = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📦 Add Files (Batch)", callback_data="sw#menu#batch")]
    ]
    if series_id:
        buttons.append([InlineKeyboardButton("🗑 Delete Series", callback_data=f"sw#del_series#{series_id}")])
    buttons.append([
        InlineKeyboardButton("🟢 Save Series", callback_data="sw#save"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel")
    ])
    return InlineKeyboardMarkup(buttons)


def _batch_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Save Batch",  callback_data="sw#bconfirm#yes"),
            InlineKeyboardButton("🔴 Cancel",       callback_data="sw#bconfirm#no"),
        ]
    ])


def _duplicate_file_keyboard(data_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Replace", callback_data=f"sw#dup#replace#{data_key}"),
            InlineKeyboardButton("🔴 Keep",    callback_data=f"sw#dup#keep#{data_key}"),
        ]
    ])


# ═════════════════════════════════════════════════════════════════════════════
# ─── USER NAVIGATION KEYBOARD BUILDERS ───────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

def _user_lang_keyboard(sid: str, langs: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(langs), 2):
        row = [
            InlineKeyboardButton(l, callback_data=f"sr#{sid}#l#{l}")
            for l in langs[i:i+2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _user_season_keyboard(sid: str, lang: str, seasons: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(seasons), 3):
        row = [
            InlineKeyboardButton(f"Season {s}" if s > 0 else "Direct Episodes", callback_data=f"sr#{sid}#l#{lang}#s#{s}")
            for s in seasons[i:i+3]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)


def _user_quality_keyboard(sid: str, lang: str, season: int, quals: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(quals), 3):
        row = [
            InlineKeyboardButton(
                q,
                callback_data=f"sr#{sid}#l#{lang}#s#{season}#q#{q}"
            )
            for q in quals[i:i+3]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#home" if season == 0 else f"sr#{sid}#l#{lang}"),
        InlineKeyboardButton("🏠 Home",  callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)


# ═════════════════════════════════════════════════════════════════════════════
# ─── /seriesfil — START ADMIN WIZARD ─────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("seriesfil") & filters.private, group=1)
async def cmd_seriesfil(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")

    uid = message.from_user.id
    temp.SERIES_WIZARD[uid] = {
        "state": S_NAME,
        "name": "", "year": "", "genre": "", "description": "",
        "languages": [], "seasons": [], "qualities": [],
        "series_id": None,
        # batch session
        "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
        "batch_data": None,
    }
    await message.reply_text(
        f"🎬 <b>Create New Series</b>\n\n"
        f"Hey {message.from_user.mention}, please send the <b>series name</b>.",
        reply_to_message_id=message.id,
        reply_markup=ForceReply(selective=True),
        parse_mode=enums.ParseMode.HTML,
    )

# ═════════════════════════════════════════════════════════════════════════════
# ─── /ed_series — EDIT WIZARD ────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["ed_series"]) & (filters.private | filters.group), group=1)
async def cmd_ed_series(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")

    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "Usage: <code>/ed_series SERIES_NAME</code> or <code>/ed_series SERIES_ID</code>\n",
            parse_mode=enums.ParseMode.HTML,
        )

    arg = args[1].strip().strip('"').strip("'")
    from database.series_db import search_series, get_series_by_name, _normalize
    import re

    exact = None
    if re.fullmatch(r"[0-9a-fA-F]{24}", arg):
        exact = await get_series(arg)
    else:
        normalized = _normalize(arg)
        exact = await get_series_by_name(normalized)
        if not exact:
            matches = await search_series(arg)
            if matches:
                exact = matches[0]

    if not exact:
        return await message.reply_text(f"❌ No series found matching '<b>{arg}</b>'.", parse_mode=enums.ParseMode.HTML)

    uid = message.from_user.id
    temp.SERIES_WIZARD[uid] = {
        "state": S_DONE,
        "name": exact["name"],
        "year": exact.get("year", ""),
        "genre": exact.get("genre", ""),
        "description": exact.get("description", ""),
        "poster": exact.get("poster", ""),
        "languages": exact.get("languages", []),
        "seasons": exact.get("seasons", []),
        "qualities": exact.get("qualities", []),
        "series_id": str(exact["_id"]),
        # batch session
        "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
        "batch_data": None,
    }
    
    wiz = temp.SERIES_WIZARD[uid]
    await message.reply_text(
        _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
        reply_markup=_config_menu_keyboard(wiz.get("series_id")),
        parse_mode=enums.ParseMode.HTML,
    )


# ═════════════════════════════════════════════════════════════════════════════
# ─── /cancel — ABORT WIZARD ──────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("cancel") & filters.private, group=1)
async def cmd_cancel(client: Client, message: Message):
    uid = message.from_user.id
    if uid in temp.SERIES_WIZARD:
        del temp.SERIES_WIZARD[uid]
        await message.reply_text("❌ Series wizard cancelled.")
    else:
        await message.reply_text("No active wizard session.")


# ═════════════════════════════════════════════════════════════════════════════
# ─── TEXT HANDLER — WIZARD STEPS ─────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(
    ["seriesfil", "sbatch", "cancel", "start", "help", "settings",
     "connect", "disconnect", "connections", "stats", "users", "chats",
     "broadcast", "ban", "unban", "leave", "disable", "logs",
     "delete", "deletefiles", "batch", "link", "pbatch", "plink",
     "request", "filter", "filters", "del", "delall", "gfilter",
     "gfilters", "delg", "delallg", "shortlink", "ping", "alive",
     "id", "info", "rename", "genpassword", "song", "set_tutorial",
     "set_thumb", "del_thumb", "view_thumb", "set_caption", "see_caption",
     "del_caption", "json", "short", "carbon", "tts", "tr", "telegraph",
     "font", "pin", "unpin", "purge", "whois", "share", "audiobook",
     "stickerid", "video", "mp4", "covid", "stream", "index",
     "setskip", "deleteall", "channel"]
), group=1)
async def wizard_text_handler(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in temp.SERIES_WIZARD:
        return  # not in wizard — let other handlers process

    if not message.reply_to_message:
        pass  # We process all text to prevent auto_filter from running

    wiz = temp.SERIES_WIZARD[uid]
    state = wiz["state"]
    
    text = ""
    if message.text:
        text = message.text.strip()
    elif message.caption:
        text = message.caption.strip()

    # ── Name ──────────────────────────────────────────────────────────────────
    if state == S_NAME:
        if not text: return
        wiz["name"] = text
        wiz["state"] = S_YEAR
        await message.reply_text(
            f"✅ Series name: <b>{text}</b>\n\nPlease send the <b>year</b> (e.g. 2017).",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Year ──────────────────────────────────────────────────────────────────
    elif state == S_YEAR:
        if not text: return
        wiz["year"] = text
        wiz["state"] = S_GENRE
        await message.reply_text(
            f"✅ Year: <b>{text}</b>\n\nPlease send the <b>genre</b> (e.g. Action, Drama).",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Genre ─────────────────────────────────────────────────────────────────
    elif state == S_GENRE:
        if not text: return
        wiz["genre"] = text
        wiz["state"] = S_RATING
        await message.reply_text(
            f"✅ Genre: <b>{text}</b>\n\nPlease send the <b>Rating</b> (or send <code>skip</code>).",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Rating ────────────────────────────────────────────────────────────────
    elif state == S_RATING:
        if not text: return
        wiz["rating"] = "" if text.lower() == "skip" else text
        wiz["state"] = S_DESC
        await message.reply_text(
            f"✅ Rating: <b>{wiz.get('rating') or 'Skipped'}</b>\n\nPlease send a short <b>description</b> (or send <code>skip</code>).",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Description ───────────────────────────────────────────────────────────
    elif state == S_DESC:
        if not text: return
        wiz["description"] = "" if text.lower() == "skip" else text
        wiz["state"] = S_POSTER
        await message.reply_text(
            f"✅ Description saved.\n\nNow, <b>send a poster photo</b> (or send an IMDb/TMDB image URL).\n\n<i>Type 'skip' to skip poster.</i>",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Poster ────────────────────────────────────────────────────────────────
    elif state == S_POSTER:
        if message.photo:
            wiz["poster"] = message.photo.file_id
        elif text.lower() == "skip":
            wiz["poster"] = ""
        else:
            return await message.reply_text("⚠️ Please send a photo, or type `skip`.")

        wiz["state"] = S_LANGS

        # Show config menu
        card = (
            f"✅ <b>Series Info Saved</b>\n\n"
            f"🎬 <b>{wiz['name']}</b>\n"
            f"📅 {wiz['year']}  🎭 {wiz['genre']}\n"
            f"⭐ {wiz.get('rating', 'N/A')}\n\n"
            f"Now configure languages, seasons, and quality."
        )
        if wiz.get("poster"):
            await message.reply_photo(
                photo=wiz["poster"],
                caption=card,
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            await message.reply_text(
                card,
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )


# ═════════════════════════════════════════════════════════════════════════════
# ─── WIZARD CALLBACK QUERIES (sw#...) ────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^sw#"), group=1)
async def wizard_callback(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    if not _is_admin(uid):
        return await query.answer("❌ Not authorized.", show_alert=True)

    data = query.data  # e.g.  sw#lang#Malayalam  or  sw#save
    parts = data.split("#")
    # parts[0] = "sw", parts[1] = action, parts[2..] = values

    if uid not in temp.SERIES_WIZARD:
        return await query.answer("No active wizard. Run /seriesfil first.", show_alert=True)

    wiz  = temp.SERIES_WIZARD[uid]
    action = parts[1] if len(parts) > 1 else ""

    if not action:
        return await query.answer()

    if action == "del_series":
        if len(parts) < 3: return await query.answer()
        series_id = parts[2]
        return await query.message.edit_text(
            f"⚠️ <b>Confirm Deletion</b>\n\nAre you sure you want to delete the series <b>{wiz.get('name', 'Unknown')}</b>?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm Delete", callback_data=f"sw#del_conf#{series_id}")],
                [InlineKeyboardButton("🔴 Cancel", callback_data=f"sw#back_to_menu")]
            ]),
            parse_mode=enums.ParseMode.HTML
        )
        
    if action == "del_conf":
        if len(parts) < 3: return await query.answer()
        series_id = parts[2]
        from database.series_db import delete_series as _del
        await _del(series_id)
        if uid in temp.SERIES_WIZARD:
            del temp.SERIES_WIZARD[uid]
        return await query.message.edit_text("✅ Series deleted successfully.")
        
    if action == "back_to_menu":
        wiz["state"] = S_DONE
        return await query.message.edit_text(
            _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
            reply_markup=_config_menu_keyboard(wiz.get("series_id")),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Cancel ────────────────────────────────────────────────────────────────
    if action == "cancel":
        if wiz.get("name"):
            wiz["state"] = S_DONE
            await query.message.edit_text(
                _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
                reply_markup=_config_menu_keyboard(wiz.get("series_id")),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            del temp.SERIES_WIZARD[uid]
            await query.message.edit_text("❌ Series wizard cancelled.")
        return await query.answer()

    # ── Config Menu shortcuts ─────────────────────────────────────────────────
    if action == "menu":
        sub = parts[2] if len(parts) > 2 else ""
        if sub == "lang":
            wiz["state"] = S_LANGS
            await query.message.edit_text(
                "🌐 <b>Select Languages</b>\n\nTap to toggle, then press Submit.",
                reply_markup=_lang_keyboard(wiz["languages"]),
                parse_mode=enums.ParseMode.HTML,
            )
        elif sub == "season":
            wiz["state"] = S_SEASONS
            await query.message.edit_text(
                "📁 <b>Select Seasons</b>\n\nTap to toggle, then press Submit.",
                reply_markup=_season_keyboard(MAX_SEASONS, wiz["seasons"]),
                parse_mode=enums.ParseMode.HTML,
            )
        elif sub == "quality":
            wiz["state"] = S_QUALITY
            await query.message.edit_text(
                "🎞 <b>Select Quality Options</b>\n\nTap to toggle, then press Submit.",
                reply_markup=_quality_keyboard(wiz["qualities"]),
                parse_mode=enums.ParseMode.HTML,
            )
        elif sub == "batch":
            wiz["state"] = S_BATCH_LANG
            wiz["batch_langs"] = []
            wiz["batch_seasons"] = []
            wiz["batch_qualities"] = []
            await query.message.edit_text(
                "📦 <b>Add Episode Batch</b>\n\nSelect <b>languages</b> for this batch:",
                reply_markup=_lang_keyboard(wiz["batch_langs"]),
                parse_mode=enums.ParseMode.HTML,
            )
        return await query.answer()

    # ── Language toggle ───────────────────────────────────────────────────────
    if action == "lang":
        val = "#".join(parts[2:])
        target_list = wiz["batch_langs"] if wiz["state"] == S_BATCH_LANG else wiz["languages"]
        if val == "submit":
            if not target_list:
                return await query.answer("⚠️ Select at least one language.", show_alert=True)
            if wiz["state"] == S_BATCH_LANG:
                wiz["languages"] = list(set(wiz["languages"] + target_list))
                wiz["state"] = S_BATCH_SEASON
                await query.message.edit_text(
                    f"📦 Batch — <b>{wiz['name']}</b>\n🌐 Languages: <b>{', '.join(target_list)}</b>\n\nSelect <b>seasons</b>:",
                    reply_markup=_season_keyboard(MAX_SEASONS, wiz["batch_seasons"]),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                await query.message.edit_text(
                    f"✅ <b>Languages saved:</b>\n" + "\n".join(f"• {l}" for l in wiz["languages"]) +
                    "\n\nNow configure seasons, quality, or add batch files.",
                    reply_markup=_config_menu_keyboard(),
                    parse_mode=enums.ParseMode.HTML,
                )
        else:
            lang = val
            if lang in target_list:
                target_list.remove(lang)
            else:
                target_list.append(lang)
            try:
                await query.message.edit_reply_markup(_lang_keyboard(target_list))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Season toggle ─────────────────────────────────────────────────────────
    if action == "season":
        val = parts[2] if len(parts) > 2 else ""
        target_list = wiz["batch_seasons"] if wiz["state"] == S_BATCH_SEASON else wiz["seasons"]
        if val == "submit":
            if wiz["state"] == S_BATCH_SEASON:
                wiz["seasons"] = list(set(wiz["seasons"] + target_list))
                wiz["state"] = S_BATCH_QUAL
                await query.message.edit_text(
                    f"📦 Batch — <b>{wiz['name']}</b>\n"
                    f"🌐 {', '.join(wiz['batch_langs'])} · 📁 Seasons {', '.join(str(s) for s in sorted(target_list)) if target_list else 'None'}\n\n"
                    "Select <b>qualities</b>:\n"
                    "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>",
                    reply_markup=_quality_keyboard(wiz["batch_qualities"], wiz["qualities"]),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                await query.message.edit_text(
                    "✅ <b>Seasons saved:</b>\n" + ("\n".join(f"• Season {s}" for s in sorted(wiz["seasons"])) if wiz["seasons"] else "None") +
                    "\n\nNow configure quality or add batch files.",
                    reply_markup=_config_menu_keyboard(),
                    parse_mode=enums.ParseMode.HTML,
                )
        elif val == "skip":
            if wiz["state"] == S_BATCH_SEASON:
                wiz["batch_seasons"] = [0]
                wiz["state"] = S_BATCH_QUAL
                await query.message.edit_text(
                    f"📦 Batch — <b>{wiz['name']}</b>\n"
                    f"🌐 {', '.join(wiz['batch_langs'])} · 📁 Season None\n\n"
                    "Select <b>qualities</b>:\n"
                    "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>",
                    reply_markup=_quality_keyboard(wiz["batch_qualities"], wiz["qualities"]),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                wiz["seasons"] = []
                await query.message.edit_text(
                    "✅ <b>Seasons skipped.</b>\n\nNow configure quality or add batch files.",
                    reply_markup=_config_menu_keyboard(),
                    parse_mode=enums.ParseMode.HTML,
                )
        else:
            n = int(val)
            if n in target_list:
                target_list.remove(n)
            else:
                target_list.append(n)
            try:
                await query.message.edit_reply_markup(_season_keyboard(MAX_SEASONS, target_list))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Quality toggle ────────────────────────────────────────────────────────
    if action == "quality":
        val = "#".join(parts[2:])
        target_list = wiz["batch_qualities"] if wiz["state"] == S_BATCH_QUAL else wiz["qualities"]
        if val == "submit":
            if not target_list:
                return await query.answer("⚠️ Select at least one quality.", show_alert=True)
            if wiz["state"] == S_BATCH_QUAL:
                wiz["qualities"] = list(set(wiz["qualities"] + target_list))
                wiz["state"] = S_BATCH_WAIT
                await query.message.edit_text(
                    f"📦 <b>Add Episode Batch</b>\n\n"
                    f"<b>Series:</b> {wiz['name']}\n"
                    f"<b>Languages:</b> {', '.join(wiz['batch_langs'])}\n"
                    f"<b>Seasons:</b> {', '.join(str(s) for s in sorted(wiz['batch_seasons'])) if wiz['batch_seasons'] and wiz['batch_seasons'] != [0] else 'None'}\n"
                    f"<b>Qualities:</b> {', '.join(wiz['batch_qualities'])}\n\n"
                    "Now send:\n"
                    "<code>/sbatch FIRST_LINK LAST_LINK</code>\n\n"
                    "Example:\n"
                    "<code>/sbatch https://t.me/c/123456/1001 https://t.me/c/123456/1010</code>",
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                await query.message.edit_text(
                    "✅ <b>Quality options saved:</b>\n" + "\n".join(f"• {q}" for q in wiz["qualities"]) +
                    "\n\nNow add batch files or save the series.",
                    reply_markup=_config_menu_keyboard(),
                    parse_mode=enums.ParseMode.HTML,
                )
        else:
            q = val
            if q in target_list:
                target_list.remove(q)
            else:
                target_list.append(q)
            # In batch mode show already-saved series qualities with ✅
            already_saved = wiz["qualities"] if wiz["state"] == S_BATCH_QUAL else []
            try:
                await query.message.edit_reply_markup(_quality_keyboard(target_list, already_saved))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Batch confirm ─────────────────────────────────────────────────────────
    if action == "bconfirm":
        choice = parts[2] if len(parts) > 2 else "no"
        if choice == "no":
            wiz["batch_data"] = None
            wiz["state"] = S_BATCH_LANG  # restart batch flow
            await query.message.edit_text(
                "Batch cancelled. Use the menu to try again.",
                reply_markup=_config_menu_keyboard(),
            )
            return await query.answer("Batch cancelled.")

        if choice == "yes":
            bd = wiz.get("batch_data")
            if not bd:
                return await query.answer("⚠️ No batch data found.", show_alert=True)

            # Ensure series is saved first
            if not wiz.get("series_id"):
                series_id = await create_series({
                    "name": wiz["name"],
                    "year": wiz["year"],
                    "genre": wiz["genre"],
                    "rating": wiz.get("rating", ""),
                    "description": wiz["description"],
                    "poster": wiz.get("poster", ""),
                    "languages": wiz["languages"],
                    "seasons": wiz["seasons"],
                    "qualities": wiz["qualities"],
                    "created_by": uid,
                })
                wiz["series_id"] = series_id
                _register_short_id(series_id)
            else:
                series_id = wiz["series_id"]
                await update_series(series_id, {
                    "languages": wiz["languages"],
                    "seasons": wiz["seasons"],
                    "qualities": wiz["qualities"],
                    "rating": wiz.get("rating", ""),
                    "poster": wiz.get("poster", ""),
                })

            # Process batch files — use ep_ prefix to avoid overwriting outer vars
            await query.message.edit_text(
                f"⏳ Processing batch... saving {bd['total_files']} files."
            )
            inserted = 0
            duplicates = 0

            # Ensure seasons_to_add always has at least one value
            seasons_to_add = wiz.get("batch_seasons") or [0]
            if not seasons_to_add:
                seasons_to_add = [0]

            for ep_num, ep_chat_id, ep_msg_id, ep_file_id, ep_file_name, ep_file_size in bd["files"]:
                for lang in wiz["batch_langs"]:
                    for season in seasons_to_add:
                        for quality in wiz["batch_qualities"]:
                            try:
                                status, reason = await add_series_file({
                                    "series_id":  series_id,
                                    "language":   lang,
                                    "season":     season,
                                    "episode":    ep_num,
                                    "quality":    quality,
                                    "chat_id":    ep_chat_id,
                                    "message_id": ep_msg_id,
                                    "file_id":    ep_file_id,
                                    "file_name":  ep_file_name,
                                    "file_size":  ep_file_size,
                                })
                                if status:
                                    inserted += 1
                                else:
                                    duplicates += 1
                            except Exception as e:
                                logger.warning(f"add_series_file error ep={ep_num}: {e}")
                                duplicates += 1

            # Save batch record
            for lang in wiz["batch_langs"]:
                for season in seasons_to_add:
                    for quality in wiz["batch_qualities"]:
                        await save_batch({
                            "series_id": series_id,
                            "language": lang,
                            "season": season,
                            "quality": quality,
                            "chat_id": bd["chat_id"],
                            "first_message_id": bd["first_msg_id"],
                            "last_message_id": bd["last_msg_id"],
                            "total_files": inserted,
                        })

            wiz["batch_data"] = None
            wiz["state"] = S_BATCH_LANG

            await query.message.edit_text(
                f"✅ <b>Batch saved successfully!</b>\n\n"
                f"📺 {wiz['name']}\n"
                f"🌐 Languages: {', '.join(wiz['batch_langs'])}\n"
                f"📁 Seasons: {', '.join(str(s) for s in wiz['batch_seasons']) if wiz['batch_seasons'] and wiz['batch_seasons'] != [0] else 'None'}\n"
                f"🎞 Qualities: {', '.join(wiz['batch_qualities'])}\n\n"
                f"✅ {inserted} files added.\n"
                f"⚠️ {duplicates} duplicates skipped.\n\n"
                "Add more batches or save the series.",
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )
            return await query.answer("Batch saved!")

    # ── Save Series ───────────────────────────────────────────────────────────
    if action == "save":
        if not wiz["name"]:
            return await query.answer("⚠️ Series name is missing.", show_alert=True)
        if not wiz["languages"]:
            return await query.answer("⚠️ Add at least one language.", show_alert=True)

        if wiz.get("series_id"):
            # Update if already saved (happens after batch)
            await update_series(wiz["series_id"], {
                "name": wiz["name"],
                "year": wiz["year"],
                "genre": wiz["genre"],
                "rating": wiz.get("rating", ""),
                "description": wiz["description"],
                "poster": wiz.get("poster", ""),
                "languages": wiz["languages"],
                "seasons": wiz["seasons"],
                "qualities": wiz["qualities"],
            })
            series_id = wiz["series_id"]
        else:
            series_id = await create_series({
                "name": wiz["name"],
                "year": wiz["year"],
                "genre": wiz["genre"],
                "rating": wiz.get("rating", ""),
                "description": wiz["description"],
                "poster": wiz.get("poster", ""),
                "languages": wiz["languages"],
                "seasons": wiz["seasons"],
                "qualities": wiz["qualities"],
                "created_by": uid,
            })
            _register_short_id(series_id)

        del temp.SERIES_WIZARD[uid]
        await query.message.edit_text(
            f"🎉 <b>Series saved!</b>\n\n"
            f"📺 <b>{wiz['name']}</b>\n"
            f"📅 {wiz['year']}  🎭 {wiz['genre']}\n"
            f"🌐 Languages: {', '.join(wiz['languages'])}\n"
            f"📁 Seasons: {', '.join(str(s) for s in sorted(wiz['seasons']))}\n"
            f"🎞 Qualities: {', '.join(wiz['qualities'])}\n\n"
            f"Users can now search: <code>{wiz['name']}</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("✅ Series saved!")

    await query.answer()


# ═════════════════════════════════════════════════════════════════════════════
# ─── /sbatch — BATCH FILE IMPORTER ───────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("sbatch") & filters.private, group=1)
async def cmd_sbatch(client: Client, message: Message):
    uid = message.from_user.id
    if not _is_admin(uid):
        return await message.reply_text("❌ You are not authorized to use this command.")

    if uid not in temp.SERIES_WIZARD or temp.SERIES_WIZARD[uid].get("state") != S_BATCH_WAIT:
        return await message.reply_text(
            "⚠️ Run <code>/seriesfil</code> first and configure language/season/quality "
            "before sending a batch.",
            parse_mode=enums.ParseMode.HTML,
        )

    args = message.command[1:]
    if len(args) < 2:
        return await message.reply_text(
            "❌ <b>Invalid batch format.</b>\n\n"
            "Please provide:\n"
            "<code>/sbatch FIRST_MESSAGE_LINK LAST_MESSAGE_LINK</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    link1, link2 = args[0], args[1]
    chat1, msg1 = _parse_tg_link(link1)
    chat2, msg2 = _parse_tg_link(link2)

    if not chat1 or not msg1 or not chat2 or not msg2:
        return await message.reply_text(
            "❌ <b>Invalid Telegram link(s).</b>\n\n"
            "Accepted formats:\n"
            "• <code>https://t.me/channelname/12345</code>\n"
            "• <code>https://t.me/c/1234567890/12345</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    if chat1 != chat2:
        return await message.reply_text(
            "❌ Both links must be from the <b>same channel</b>.",
            parse_mode=enums.ParseMode.HTML,
        )

    if msg1 > msg2:
        return await message.reply_text(
            "❌ First link must have a <b>lower</b> message ID than the second."
        )

    total = msg2 - msg1 + 1
    if total > 1000:
        return await message.reply_text(
            f"❌ Range too large ({total} messages). Maximum allowed is 1000 per batch."
        )

    wiz = temp.SERIES_WIZARD[uid]
    processing_msg = await message.reply_text(
        f"⏳ Scanning messages {msg1} → {msg2} ({total} total)...\nThis may take time depending on number of messages."
    )

    # ── Collect files using chunked get_messages (same as /batch in genlink.py) ─
    files_found = []
    errors      = 0

    # Verify bot can read the channel first
    try:
        await client.get_messages(chat1, msg1)
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ <b>Cannot read messages from this channel.</b>\n\n"
            f"Make sure the bot is added as an <b>admin</b> in the source channel.\n\n"
            f"<code>{e}</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    for chunk_start in range(msg1, msg2 + 1, 200):
        chunk_end = min(chunk_start + 199, msg2)
        try:
            messages = await client.get_messages(chat1, list(range(chunk_start, chunk_end + 1)))
            for msg in messages:
                if not msg or msg.empty or msg.service:
                    errors += 1
                    continue
                if not msg.media:
                    errors += 1
                    continue
                try:
                    file_type = msg.media
                    media     = getattr(msg, file_type.value)
                    if not media:
                        errors += 1
                        continue

                    file_id   = getattr(media, "file_id", "")
                    file_name = getattr(media, "file_name", None) or f"file_{msg.id}"
                    file_size = getattr(media, "file_size", 0) or 0

                    # Attempt to extract episode number from filename, caption, or text
                    ep_num = _extract_episode_number(file_name)
                    if not ep_num and msg.caption:
                        ep_num = _extract_episode_number(msg.caption)
                    if not ep_num and msg.text:
                        ep_num = _extract_episode_number(msg.text)

                    files_found.append((chat1, msg.id, file_id, file_name, file_size, ep_num))
                except Exception as ex:
                    logger.warning(f"sbatch scan error mid={msg.id}: {ex}")
                    errors += 1
        except Exception as ex:
            logger.warning(f"sbatch chunk error {chunk_start}-{chunk_end}: {ex}")
            errors += (chunk_end - chunk_start + 1)

    if not files_found:
        await processing_msg.edit_text(
            "❌ <b>No files found</b> in the given range.\n\n"
            "Make sure the bot is a member of the channel and the messages contain files.",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Process episode mapping
    mapped_files = []
    last_ep = 0
    for chat_id, mid, file_id, file_name, file_size, ep_num in files_found:
        if not ep_num:
            ep_num = last_ep + 1
        mapped_files.append((ep_num, chat_id, mid, file_id, file_name, file_size))
        last_ep = ep_num

    # Build episode preview
    ep_preview = "\n".join(
        f"  Ep {ep_num:02d} — {fname}"
        for ep_num, _, _, _, fname, _ in mapped_files[:10]
    )
    if len(mapped_files) > 10:
        ep_preview += f"\n  ... and {len(mapped_files) - 10} more"

    # Store in wizard
    wiz["batch_data"] = {
        "chat_id":     chat1,
        "first_msg_id": msg1,
        "last_msg_id":  msg2,
        "total_files": len(mapped_files),
        "files":       mapped_files,
    }
    wiz["state"] = S_BATCH_CONF

    await processing_msg.edit_text(
        f"📦 <b>Batch Preview</b>\n\n"
        f"📺 <b>Series:</b> {wiz['name']}\n"
        f"🌐 <b>Languages:</b> {', '.join(wiz['batch_langs'])}\n"
        f"📁 <b>Seasons:</b> {', '.join(str(s) for s in wiz['batch_seasons']) if wiz['batch_seasons'] and wiz['batch_seasons'] != [0] else 'None'}\n"
        f"🎞 <b>Qualities:</b> {', '.join(wiz['batch_qualities'])}\n\n"
        f"📨 <b>First Message:</b> {msg1}\n"
        f"📨 <b>Last Message:</b> {msg2}\n"
        f"🎬 <b>Total Files:</b> {len(files_found)}\n"
        f"⚠️ <b>Skipped:</b> {errors}\n\n"
        f"<b>Episodes:</b>\n{ep_preview}\n\n"
        "Save this batch?",
        reply_markup=_batch_confirm_keyboard(),
        parse_mode=enums.ParseMode.HTML,
    )


# ═════════════════════════════════════════════════════════════════════════════
# ─── USER SEARCH & NAVIGATION LOGIC ──────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

async def _send_or_edit(message_or_query, text, reply_markup, poster=None):
    if isinstance(message_or_query, Message):
        if poster:
            return await message_or_query.reply_photo(photo=poster, caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            return await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    else:
        try:
            if message_or_query.message.photo:
                return await message_or_query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                return await message_or_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            return message_or_query.message


async def _resolve_nav_step(full_id: str, sid: str, series: dict, lang=None, season=None, qual=None):
    """
    Returns (text, reply_markup)
    """
    card = _series_card(series)
    
    if lang is None:
        langs = await list_series_languages(full_id)
        if not langs: langs = series.get("languages", [])
        if not langs: return "⚠️ No files yet.", None
        return card + "\n\n🌐 <b>Select Language:</b>", _user_lang_keyboard(sid, langs)
        
    if season is None:
        seasons = await list_series_seasons(full_id, lang)
        if not seasons: seasons = sorted(series.get("seasons", []))
        if not seasons: return "⚠️ No seasons found.", None
        if seasons == [0]:
            season = 0
        else:
            return card + f"\n\n🌐 <b>{lang}</b>\n📁 <b>Select Season:</b>", _user_season_keyboard(sid, lang, seasons)
        
    if qual is None:
        quals = await list_season_qualities(full_id, lang, season)
        if not quals: return "⚠️ No qualities found.", None
        
        season_str = f"Season {season}" if season > 0 else "Direct Episodes"
        return card + f"\n\n🌐 <b>{lang}</b>\n📁 <b>{season_str}</b>\n🎞 <b>Select Quality:</b>", _user_quality_keyboard(sid, lang, season, quals)
        
    return "⚠️ Invalid step.", None


async def process_series_search(client: Client, message: Message, txt: str, reply_msg: Message = None):
    # Try normalized first, then raw text for better matching
    matches = await search_series(_normalize(txt))
    if not matches:
        matches = await search_series(txt)
    if not matches:
        return False

    series = matches[0]
    series_id = str(series["_id"])
    _register_short_id(series_id)
    sid = _series_short_id(series_id)

    text, rm = await _resolve_nav_step(series_id, sid, series)
    if rm:
        if reply_msg:
            try:
                await reply_msg.delete()
            except:
                pass
        msg = await _send_or_edit(message, text, rm, poster=series.get("poster"))
        if msg:
            from info import AUTO_DELETE
            if AUTO_DELETE:
                async def delete_search_msg(m):
                    await asyncio.sleep(60)
                    try:
                        await m.delete()
                    except:
                        pass
                import asyncio
                asyncio.create_task(delete_search_msg(msg))
    return True

@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming, group=2)
async def series_search_handler(client: Client, message: Message):
    txt = message.text.strip()
    if txt.startswith("/") or len(txt) > 100 or len(txt) < 2:
        return
    await process_series_search(client, message, txt)


@Client.on_callback_query(filters.regex(r"^sr#"), group=1)
async def series_user_nav(client: Client, query: CallbackQuery):
    if query.message.reply_to_message and query.from_user.id != query.message.reply_to_message.from_user.id:
        from Script import script
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        
    parts = query.data.split("#")
    
    if len(parts) < 2: return await query.answer()

    sid = parts[1]
    if sid == "close":
        return await query.message.delete()
        
    full_id = await _get_full_id(sid)
    if not full_id:
        return await query.answer("Series context expired.", show_alert=True)
    
    series = await get_series(full_id)
    if not series:
        return await query.answer("Series not found in database.", show_alert=True)

    lang = None
    season = None
    qual = None
    
    # ── Send file (Quality selected) ──────────────────────────────────────────
    if len(parts) >= 8 and parts[2] == "l" and parts[4] == "s" and parts[6] == "q":
        lang    = parts[3]
        season  = int(parts[5])
        qual    = parts[7]
        
        rating = series.get("rating", "N/A")
        if len(parts) >= 10 and parts[8] == "e":
            ep      = int(parts[9])
            files = await get_series_files(full_id, lang, season, ep, qual)
            for f in files:
                f["is_series"] = True
                f["series_rating"] = rating
                f["episode_index"] = 1
                f["total_episodes"] = 1
        else:
            files = []
            episodes = await list_quality_episodes(full_id, lang, season, qual)
            total_eps = len(episodes)
            for i, ep in enumerate(episodes, start=1):
                ep_files = await get_series_files(full_id, lang, season, ep, qual)
                for f in ep_files:
                    f["is_series"] = True
                    f["series_rating"] = rating
                    f["episode_index"] = i
                    f["total_episodes"] = total_eps
                files.extend(ep_files)

        if files:
            if query.message.chat.type == enums.ChatType.PRIVATE:
                await query.answer()
                from plugins.commands import send_series_files_to_user
                await send_series_files_to_user(client, query.from_user.id, files, query=query)
                return
            else:
                from utils import temp as _temp
                import uuid as _uuid
                key = str(_uuid.uuid4())
                _temp.GETALL[key] = {"user": query.from_user.id, "files": files}
                return await query.answer(url=f"https://t.me/{temp.U_NAME}?start=all_{key}")
        elif files is not None:
            return await query.answer("⚠️ File not found. It may have been removed.", show_alert=True)


        
    # Navigation mapping
    if len(parts) >= 4 and parts[2] == "l":
        lang = parts[3]
    if len(parts) >= 6 and parts[4] == "s":
        season = int(parts[5])
    if len(parts) >= 8 and parts[6] == "q":
        qual = parts[7]
        
    text, rm = await _resolve_nav_step(full_id, sid, series, lang, season, qual)
    if rm:
        await _send_or_edit(query, text, rm)
        return await query.answer()
    
    return await query.answer(text, show_alert=True)



# ═════════════════════════════════════════════════════════════════════════════
# ─── /serieslist — Admin: list all series ────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["serieslist", "viewseries"]) & (filters.private | filters.group), group=1)
async def cmd_serieslist(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ Not authorized.")

    all_series = await list_all_series()
    if not all_series:
        return await message.reply_text("No series added yet. Use /seriesfil to create one.")

    lines = []
    for s in all_series:
        sid = str(s["_id"])
        _register_short_id(sid)
        lines.append(
            f"📺 <b>{s['name']}</b> ({s.get('year','?')})\n"
            f"   🌐 {', '.join(s.get('languages',[]))}\n"
            f"   📁 Seasons: {', '.join(str(x) if x > 0 else 'Direct' for x in sorted(s.get('seasons',[])))}\n"
            f"   ID: <code>{sid}</code>"
        )

    text = "📋 <b>All Series</b>\n\n" + "\n\n".join(lines)
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ═════════════════════════════════════════════════════════════════════════════
# ─── /seriesdel — Admin: delete a series ─────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command(["seriesdel", "delseries"]) & (filters.private | filters.group), group=1)
async def cmd_seriesdel(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ Not authorized.")

    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "Usage: <code>/delseries SERIES_NAME</code> or <code>/delseries SERIES_ID</code>\n"
            "Get names/IDs with /viewseries",
            parse_mode=enums.ParseMode.HTML,
        )

    arg = args[1].strip().strip('"').strip("'")
    from database.series_db import delete_series as _del, search_series, get_series_by_name, _normalize
    import re

    if re.fullmatch(r"[0-9a-fA-F]{24}", arg):
        await _del(arg)
        return await message.reply_text(f"✅ Series ID <code>{arg}</code> deleted (soft).", parse_mode=enums.ParseMode.HTML)

    normalized = _normalize(arg)
    exact = await get_series_by_name(normalized)
    if exact:
        await _del(str(exact["_id"]))
        return await message.reply_text(f"✅ Series <b>{exact['name']}</b> deleted (soft).", parse_mode=enums.ParseMode.HTML)
        
    matches = await search_series(arg)
    if not matches:
        return await message.reply_text(f"❌ No series found matching '<b>{arg}</b>'.", parse_mode=enums.ParseMode.HTML)
    
    match = matches[0]
    await _del(str(match["_id"]))
    await message.reply_text(f"✅ Series <b>{match['name']}</b> deleted (soft).", parse_mode=enums.ParseMode.HTML)


# ═════════════════════════════════════════════════════════════════════════════
# ─── STARTUP: Ensure DB indexes ──────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

async def _startup():
    await _ensure_indexes()
    logger.info("Series DB indexes ensured.")

# Schedule index creation when the module is loaded
import asyncio as _asyncio
try:
    loop = _asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(_startup())
    else:
        loop.run_until_complete(_startup())
except Exception as _e:
    logger.warning(f"Series DB startup: {_e}")
