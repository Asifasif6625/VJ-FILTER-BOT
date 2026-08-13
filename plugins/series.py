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

# ─── In-Memory Wizard State ───────────────────────────────────────────────────
# Key = admin user_id (int)
# Value = dict with wizard data and current state name
SERIES_WIZARD: dict = {}

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


def _parse_tg_link(link: str) -> tuple[str | None, int | None]:
    """
    Parse a Telegram message link.
    Supports:
      https://t.me/channelname/12345
      https://t.me/c/1234567890/12345
    Returns (chat_identifier, message_id).
    chat_identifier is either '@username' or '-100<chat_id>'.
    """
    link = link.strip()
    # Private channel: t.me/c/CHAT_ID/MSG_ID
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)", link)
    if m:
        chat_id = int("-100" + m.group(1))
        msg_id  = int(m.group(2))
        return str(chat_id), msg_id

    # Public channel: t.me/USERNAME/MSG_ID
    m = re.match(r"https?://t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        username = "@" + m.group(1)
        msg_id   = int(m.group(2))
        return username, msg_id

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
            tick = "✅ " if lang in selected else ""
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
        InlineKeyboardButton("🔴 Cancel",          callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _quality_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(QUALITY_OPTIONS), 3):
        row = []
        for q in QUALITY_OPTIONS[i:i+3]:
            tick = "✅ " if q in selected else ""
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


def _config_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Languages", callback_data="sw#menu#lang"),
            InlineKeyboardButton("📁 Seasons",   callback_data="sw#menu#season"),
            InlineKeyboardButton("🎞 Quality",   callback_data="sw#menu#quality"),
        ],
        [
            InlineKeyboardButton("📦 Add Files (Batch)", callback_data="sw#menu#batch"),
        ],
        [
            InlineKeyboardButton("🟢 Save Series", callback_data="sw#save"),
            InlineKeyboardButton("🔴 Cancel",       callback_data="sw#cancel"),
        ],
    ])


def _batch_lang_keyboard(langs: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(l, callback_data=f"sw#blang#{l}")] for l in langs]
    rows.append([InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel")])
    return InlineKeyboardMarkup(rows)


def _batch_season_keyboard(seasons: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(seasons), 4):
        row = [
            InlineKeyboardButton(f"Season {s}", callback_data=f"sw#bseason#{s}")
            for s in seasons[i:i+4]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel")])
    return InlineKeyboardMarkup(rows)


def _batch_quality_keyboard(quals: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(q, callback_data=f"sw#bquality#{q}")] for q in quals]
    rows.append([InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel")])
    return InlineKeyboardMarkup(rows)


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
            InlineKeyboardButton(f"Season {s}", callback_data=f"sr#{sid}#l#{lang}#s#{s}")
            for s in seasons[i:i+3]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)


def _user_episode_keyboard(sid: str, lang: str, season: int, quality: str, episodes: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(episodes), 4):
        row = [
            InlineKeyboardButton(
                f"Ep {ep}",
                callback_data=f"sr#{sid}#l#{lang}#s#{season}#q#{quality}#e#{ep}"
            )
            for ep in episodes[i:i+4]
        ]
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#l#{lang}#s#{season}"),
        InlineKeyboardButton("🏠 Home",  callback_data=f"sr#{sid}#home"),
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
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#l#{lang}"),
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
    SERIES_WIZARD[uid] = {
        "state": S_NAME,
        "name": "", "year": "", "genre": "", "description": "",
        "languages": [], "seasons": [], "qualities": [],
        "series_id": None,
        # batch session
        "batch_lang": "", "batch_season": 0, "batch_quality": "",
        "batch_data": None,
    }
    await message.reply_text(
        "🎬 <b>Create New Series</b>\n\n"
        "Please send the <b>series name</b>.",
        parse_mode=enums.ParseMode.HTML,
    )


# ═════════════════════════════════════════════════════════════════════════════
# ─── /cancel — ABORT WIZARD ──────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("cancel") & filters.private, group=1)
async def cmd_cancel(client: Client, message: Message):
    uid = message.from_user.id
    if uid in SERIES_WIZARD:
        del SERIES_WIZARD[uid]
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
    if uid not in SERIES_WIZARD:
        return  # not in wizard — let other handlers process

    wiz = SERIES_WIZARD[uid]
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
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Year ──────────────────────────────────────────────────────────────────
    elif state == S_YEAR:
        if not text: return
        wiz["year"] = text
        wiz["state"] = S_GENRE
        await message.reply_text(
            f"✅ Year: <b>{text}</b>\n\nPlease send the <b>genre(s)</b> (e.g. Drama, Mystery, Sci-Fi).",
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Genre ─────────────────────────────────────────────────────────────────
    elif state == S_GENRE:
        if not text: return
        wiz["genre"] = text
        wiz["state"] = S_RATING
        await message.reply_text(
            f"✅ Genre: <b>{text}</b>\n\nPlease send the <b>Rating</b> (or send <code>skip</code>).",
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Rating ────────────────────────────────────────────────────────────────
    elif state == S_RATING:
        if not text: return
        wiz["rating"] = "" if text.lower() == "skip" else text
        wiz["state"] = S_DESC
        await message.reply_text(
            f"✅ Rating: <b>{wiz.get('rating') or 'Skipped'}</b>\n\nPlease send a short <b>description</b> (or send <code>skip</code>).",
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Description ───────────────────────────────────────────────────────────
    elif state == S_DESC:
        if not text: return
        wiz["description"] = "" if text.lower() == "skip" else text
        wiz["state"] = S_POSTER
        await message.reply_text(
            f"✅ Description saved.\n\nPlease send a <b>Poster image</b> (photo) or send <code>skip</code>.",
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

    if uid not in SERIES_WIZARD:
        return await query.answer("No active wizard. Run /seriesfil first.", show_alert=True)

    wiz  = SERIES_WIZARD[uid]
    action = parts[1] if len(parts) > 1 else ""

    # ── Cancel ────────────────────────────────────────────────────────────────
    if action == "cancel":
        del SERIES_WIZARD[uid]
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
            # Send to batch-language selector
            langs = wiz["languages"]
            if not langs:
                return await query.answer("⚠️ Add languages first!", show_alert=True)
            seasons = wiz["seasons"]
            if not seasons:
                return await query.answer("⚠️ Add seasons first!", show_alert=True)
            quals = wiz["qualities"]
            if not quals:
                return await query.answer("⚠️ Add qualities first!", show_alert=True)
            wiz["state"] = S_BATCH_LANG
            await query.message.edit_text(
                "📦 <b>Add Episode Batch</b>\n\nSelect <b>language</b> for this batch:",
                reply_markup=_batch_lang_keyboard(langs),
                parse_mode=enums.ParseMode.HTML,
            )
        return await query.answer()

    # ── Language toggle ───────────────────────────────────────────────────────
    if action == "lang":
        val = "#".join(parts[2:])
        if val == "submit":
            if not wiz["languages"]:
                return await query.answer("⚠️ Select at least one language.", show_alert=True)
            await query.message.edit_text(
                f"✅ <b>Languages saved:</b>\n" + "\n".join(f"• {l}" for l in wiz["languages"]) +
                "\n\nNow configure seasons, quality, or add batch files.",
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            lang = val
            if lang in wiz["languages"]:
                wiz["languages"].remove(lang)
            else:
                wiz["languages"].append(lang)
            try:
                await query.message.edit_reply_markup(_lang_keyboard(wiz["languages"]))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Season toggle ─────────────────────────────────────────────────────────
    if action == "season":
        val = parts[2] if len(parts) > 2 else ""
        if val == "submit":
            if not wiz["seasons"]:
                return await query.answer("⚠️ Select at least one season.", show_alert=True)
            await query.message.edit_text(
                "✅ <b>Seasons saved:</b>\n" + "\n".join(f"• Season {s}" for s in sorted(wiz["seasons"])) +
                "\n\nNow configure quality or add batch files.",
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            n = int(val)
            if n in wiz["seasons"]:
                wiz["seasons"].remove(n)
            else:
                wiz["seasons"].append(n)
            try:
                await query.message.edit_reply_markup(_season_keyboard(MAX_SEASONS, wiz["seasons"]))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Quality toggle ────────────────────────────────────────────────────────
    if action == "quality":
        val = "#".join(parts[2:])
        if val == "submit":
            if not wiz["qualities"]:
                return await query.answer("⚠️ Select at least one quality.", show_alert=True)
            await query.message.edit_text(
                "✅ <b>Quality options saved:</b>\n" + "\n".join(f"• {q}" for q in wiz["qualities"]) +
                "\n\nNow add batch files or save the series.",
                reply_markup=_config_menu_keyboard(),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            q = val
            if q in wiz["qualities"]:
                wiz["qualities"].remove(q)
            else:
                wiz["qualities"].append(q)
            try:
                await query.message.edit_reply_markup(_quality_keyboard(wiz["qualities"]))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Batch: language selection ─────────────────────────────────────────────
    if action == "blang":
        lang = "#".join(parts[2:])
        wiz["batch_lang"] = lang
        wiz["state"] = S_BATCH_SEASON
        await query.message.edit_text(
            f"📦 Batch — <b>{wiz['name']}</b>\n🌐 Language: <b>{lang}</b>\n\nSelect <b>season</b>:",
            reply_markup=_batch_season_keyboard(sorted(wiz["seasons"])),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    # ── Batch: season selection ───────────────────────────────────────────────
    if action == "bseason":
        s = int(parts[2])
        wiz["batch_season"] = s
        wiz["state"] = S_BATCH_QUAL
        await query.message.edit_text(
            f"📦 Batch — <b>{wiz['name']}</b>\n"
            f"🌐 {wiz['batch_lang']} · 📁 Season {s}\n\n"
            "Select <b>quality</b>:",
            reply_markup=_batch_quality_keyboard(wiz["qualities"]),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    # ── Batch: quality selection ──────────────────────────────────────────────
    if action == "bquality":
        q = "#".join(parts[2:])
        wiz["batch_quality"] = q
        wiz["state"] = S_BATCH_WAIT
        await query.message.edit_text(
            f"📦 <b>Add Episode Batch</b>\n\n"
            f"<b>Series:</b> {wiz['name']}\n"
            f"<b>Language:</b> {wiz['batch_lang']}\n"
            f"<b>Season:</b> {wiz['batch_season']}\n"
            f"<b>Quality:</b> {q}\n\n"
            "Now send:\n"
            "<code>/sbatch FIRST_LINK LAST_LINK</code>\n\n"
            "Example:\n"
            "<code>/sbatch https://t.me/c/123456/1001 https://t.me/c/123456/1010</code>",
            parse_mode=enums.ParseMode.HTML,
        )
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

            # Process batch files
            await query.message.edit_text(
                f"⏳ Processing batch... saving {bd['total_files']} files."
            )
            inserted = 0
            duplicates = 0

            for ep_num, chat_id, msg_id, file_id, file_name, file_size in bd["files"]:
                status, reason = await add_series_file({
                    "series_id": series_id,
                    "language": wiz["batch_lang"],
                    "season": wiz["batch_season"],
                    "episode": ep_num,
                    "quality": wiz["batch_quality"],
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_size": file_size,
                })
                if status:
                    inserted += 1
                else:
                    duplicates += 1

            # Save batch record
            await save_batch({
                "series_id": series_id,
                "language": wiz["batch_lang"],
                "season": wiz["batch_season"],
                "quality": wiz["batch_quality"],
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
                f"🌐 {wiz['batch_lang']} · 📁 Season {wiz['batch_season']} · 🎞 {wiz['batch_quality']}\n\n"
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
        if not wiz["seasons"]:
            return await query.answer("⚠️ Add at least one season.", show_alert=True)

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

        del SERIES_WIZARD[uid]
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

    if uid not in SERIES_WIZARD or SERIES_WIZARD[uid].get("state") != S_BATCH_WAIT:
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
    if total > 500:
        return await message.reply_text(
            f"❌ Range too large ({total} messages). Maximum allowed is 500 per batch."
        )

    wiz = SERIES_WIZARD[uid]
    processing_msg = await message.reply_text(
        f"⏳ Scanning messages {msg1} → {msg2} ({total} total)..."
    )

    # ── Collect files ─────────────────────────────────────────────────────────
    files_found = []
    errors      = 0

    for mid in range(msg1, msg2 + 1):
        try:
            msg = await client.get_messages(chat1, mid)
            if not msg or msg.empty:
                errors += 1
                continue

            media = (
                msg.document or msg.video or msg.audio
                or msg.photo or msg.animation or msg.voice or msg.video_note
            )
            if media:
                file_id   = getattr(media, "file_id", "")
                file_name = getattr(media, "file_name", None) or f"file_{mid}"
                file_size = getattr(media, "file_size", 0)
                
                # Attempt to extract episode number
                ep_num = _extract_episode_number(file_name)
                if not ep_num and msg.caption:
                    ep_num = _extract_episode_number(msg.caption)
                if not ep_num and msg.text:
                    ep_num = _extract_episode_number(msg.text)
                
                files_found.append((chat1, mid, file_id, file_name, file_size, ep_num))
            else:
                errors += 1

        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as ex:
            logger.warning(f"sbatch get_messages error mid={mid}: {ex}")
            errors += 1

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
        f"🌐 <b>Language:</b> {wiz['batch_lang']}\n"
        f"📁 <b>Season:</b> {wiz['batch_season']}\n"
        f"🎞 <b>Quality:</b> {wiz['batch_quality']}\n\n"
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
            await message_or_query.reply_photo(photo=poster, caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
    else:
        try:
            if message_or_query.message.photo:
                await message_or_query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await message_or_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except MessageNotModified:
            pass


async def _resolve_nav_step(full_id: str, sid: str, series: dict, lang=None, season=None, qual=None):
    """
    Auto-advances if there's only 1 option available at a step.
    Returns (text, reply_markup)
    """
    card = _series_card(series)
    
    if not lang:
        langs = await list_series_languages(full_id)
        if not langs: langs = series.get("languages", [])
        if not langs: return "⚠️ No files yet.", None
        if len(langs) == 1:
            return await _resolve_nav_step(full_id, sid, series, lang=langs[0])
        return card + "\n\n🌐 <b>Select Language:</b>", _user_lang_keyboard(sid, langs)
        
    if not season:
        seasons = await list_series_seasons(full_id, lang)
        if not seasons: seasons = sorted(series.get("seasons", []))
        if not seasons: return "⚠️ No seasons found.", None
        if len(seasons) == 1:
            return await _resolve_nav_step(full_id, sid, series, lang=lang, season=seasons[0])
        return card + f"\n\n🌐 <b>{lang}</b>\n📁 <b>Select Season:</b>", _user_season_keyboard(sid, lang, seasons)
        
    if not qual:
        quals = await list_season_qualities(full_id, lang, season)
        if not quals: return "⚠️ No qualities found.", None
        if len(quals) == 1:
            return await _resolve_nav_step(full_id, sid, series, lang=lang, season=season, qual=quals[0])
        return card + f"\n\n🌐 <b>{lang}</b>\n📁 <b>Season {season}</b>\n🎞 <b>Select Quality:</b>", _user_quality_keyboard(sid, lang, season, quals)
        
    episodes = await list_quality_episodes(full_id, lang, season, qual)
    if not episodes:
        return "⚠️ No episodes found.", None
        
    return card + f"\n\n🌐 <b>{lang}</b>  📁 <b>Season {season}</b>  🎞 <b>{qual}</b>\n🎬 <b>Select Episode:</b>", _user_episode_keyboard(sid, lang, season, qual, episodes)


@Client.on_message(filters.group & filters.text & filters.incoming, group=1)
async def series_search_handler(client: Client, message: Message):
    if message.text.startswith("/") or len(message.text) > 100 or len(message.text.strip()) < 2:
        return

    matches = await search_series(_normalize(message.text.strip()))
    if not matches: return

    series = matches[0]
    series_id = str(series["_id"])
    _register_short_id(series_id)
    sid = _series_short_id(series_id)

    text, rm = await _resolve_nav_step(series_id, sid, series)
    if rm:
        await _send_or_edit(message, text, rm, poster=series.get("poster"))


@Client.on_callback_query(filters.regex(r"^sr#"), group=1)
async def series_user_nav(client: Client, query: CallbackQuery):
    data  = query.data
    parts = data.split("#")
    
    if len(parts) < 2: return await query.answer()

    sid = parts[1]
    full_id = await _get_full_id(sid)
    if not full_id: return await query.answer("⚠️ Series not found.", show_alert=True)

    series = await get_series(full_id)
    if not series: return await query.answer("⚠️ Series not found.", show_alert=True)

    lang = None
    season = None
    qual = None
    
    # ── Send file (Episode selected) ──────────────────────────────────────────
    # format: sr#{sid}#l#{lang}#s#{season}#q#{quality}#e#{ep}
    if len(parts) >= 10 and parts[2] == "l" and parts[4] == "s" and parts[6] == "q" and parts[8] == "e":
        lang    = parts[3]
        season  = int(parts[5])
        qual    = parts[7]
        ep      = int(parts[9])

        files = await get_series_files(full_id, lang, season, ep, qual)
        if not files:
            return await query.answer("⚠️ File not found. It may have been removed.", show_alert=True)

        await query.answer("📤 Sending file...")

        for f in files:
            try:
                if f.get("chat_id") and f.get("message_id"):
                    await client.copy_message(
                        chat_id=query.message.chat.id,
                        from_chat_id=f["chat_id"],
                        message_id=f["message_id"],
                    )
                elif f.get("file_id"):
                    await client.send_document(
                        chat_id=query.message.chat.id,
                        document=f["file_id"],
                        caption=f"🎬 {series['name']} S{season:02d}E{ep:02d} | {qual}",
                    )
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception as ex:
                logger.error(f"series file send error: {ex}")
                await query.message.reply_text(f"⚠️ Could not send file: {ex}")
        return
        
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

@Client.on_message(filters.command("serieslist") & filters.private, group=1)
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
            f"   📁 Seasons: {', '.join(str(x) for x in sorted(s.get('seasons',[])))}\n"
            f"   ID: <code>{sid}</code>"
        )

    text = "📋 <b>All Series</b>\n\n" + "\n\n".join(lines)
    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ═════════════════════════════════════════════════════════════════════════════
# ─── /seriesdel — Admin: delete a series ─────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("seriesdel") & filters.private, group=1)
async def cmd_seriesdel(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ Not authorized.")

    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "Usage: <code>/seriesdel SERIES_ID</code>\n"
            "Get IDs with /serieslist",
            parse_mode=enums.ParseMode.HTML,
        )

    from database.series_db import delete_series as _del
    await _del(args[0])
    await message.reply_text(f"✅ Series <code>{args[0]}</code> deleted (soft).", parse_mode=enums.ParseMode.HTML)


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
