# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01
#
# ─── series.py — Series & Episode Management System ──────────────────────────
#
# Admin commands:   /seriesfil   — create / manage series
#                   /sbatch      — add episode batch from channel link range
#                   /slink       — add single episode from channel link
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

from info import ADMINS, CHANNELS, SDATABASE_CHANNEL
from database.series_db import (
    create_series,
    get_series,
    get_series_by_name,
    search_series,
    update_series,
    list_all_series,
    add_series_file,
    check_episode_exists,
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
    clean_series_title,
)

logger = logging.getLogger(__name__)

from utils import temp, get_poster

# ─── Wizard State Names ───────────────────────────────────────────────────────
S_NAME             = "WAITING_NAME"
S_YEAR             = "WAITING_YEAR"
S_GENRE            = "WAITING_GENRE"
S_RATING           = "WAITING_RATING"
S_DESC             = "WAITING_DESCRIPTION"
S_POSTER           = "WAITING_POSTER"
S_LANGS            = "SELECTING_LANGUAGES"
S_SEASONS          = "SELECTING_SEASONS"
S_QUALITY          = "SELECTING_QUALITY"
S_BATCH_LANG       = "BATCH_SELECT_LANG"
S_BATCH_SEASON     = "BATCH_SELECT_SEASON"
S_BATCH_QUAL       = "BATCH_SELECT_QUAL"
S_CUSTOM_LANG_WAIT = "WAITING_CUSTOM_LANG_INPUT"
S_CUSTOM_LANG_CONF = "CONFIRMING_CUSTOM_LANG"
S_CUSTOM_QUAL_WAIT = "WAITING_CUSTOM_QUAL_INPUT"
S_CUSTOM_QUAL_CONF = "CONFIRMING_CUSTOM_QUAL"
S_BATCH_WAIT       = "WAITING_BATCH"
S_BATCH_CONF       = "CONFIRMING_BATCH"
S_DONE             = "SAVED"



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

# ─── Auto S Add Language & Quality Mapping ──────────────────────────────────
AUTO_LANGUAGE_MAP = {
    "malayalam": "Malayalam", "mal": "Malayalam",
    "english": "English", "eng": "English",
    "hindi": "Hindi", "hin": "Hindi",
    "tamil": "Tamil", "tam": "Tamil",
    "telugu": "Telugu", "tel": "Telugu",
    "kannada": "Kannada", "kan": "Kannada",
    "bengali": "Bengali", "ben": "Bengali",
    "marathi": "Marathi", "mar": "Marathi",
    "german": "German", "ger": "German",
    "korean": "Korean", "kor": "Korean",
    "japanese": "Japanese", "jap": "Japanese", "jpn": "Japanese",
    "spanish": "Spanish", "spa": "Spanish",
    "french": "French", "fre": "French", "fra": "French",
    "arabic": "Arabic", "ara": "Arabic",
    "russian": "Russian", "rus": "Russian",
    "chinese": "Chinese", "chi": "Chinese", "zho": "Chinese",
    "italian": "Italian", "ita": "Italian",
    "portuguese": "Portuguese", "por": "Portuguese",
    "turkish": "Turkish", "tur": "Turkish",
    "thai": "Thai",
}

def extract_quality_from_filename(filename: str) -> str:
    """
    Extract accurate, normalized video quality from a filename.
    Supports resolution, bit-depth, HDR/Dolby Vision, and source tags in priority order.
    """
    if not filename:
        return "Unknown"

    text = str(filename)
    text = re.sub(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts)$", "", text, flags=re.I)
    # Normalize separators into spaces for reliable word boundary matching
    text = re.sub(r"[\._\-\+\[\]\(\)\{\}]", " ", text)
    text = " " + re.sub(r"\s+", " ", text).strip() + " "

    # 1. Detect Resolution (in priority order)
    res = None
    if re.search(r"\b2160p\b", text, re.I):
        res = "2160p"
    elif re.search(r"\b(4k|uhd)\b", text, re.I):
        res = "4K"
    elif re.search(r"\b(1440p|2k)\b", text, re.I):
        res = "1440p"
    elif re.search(r"\b1080p\b", text, re.I):
        res = "1080p"
    elif re.search(r"\b(1080i|fhd)\b", text, re.I):
        res = "1080i"
    elif re.search(r"\b720p\b", text, re.I):
        res = "720p"
    elif re.search(r"\b(576p|576i)\b", text, re.I):
        res = "576p"
    elif re.search(r"\b(480p|480i|sd)\b", text, re.I):
        res = "480p"
    elif re.search(r"\b360p\b", text, re.I):
        res = "360p"
    elif re.search(r"\b240p\b", text, re.I):
        res = "240p"
    elif re.search(r"\bhd\b", text, re.I) and not re.search(r"\b(web\s*hd|hd\s*rip|hdtv)\b", text, re.I):
        res = "720p"

    # 2. Detect Bit-Depth
    bit_depth = None
    if re.search(r"\b10\s*bit\b", text, re.I):
        bit_depth = "10bit"
    elif re.search(r"\b8\s*bit\b", text, re.I):
        bit_depth = "8bit"

    # 3. Detect HDR / Dolby Vision
    hdr = None
    if re.search(r"\b(dolby\s*vision|dovi|\bdv\b)", text, re.I):
        hdr = "Dolby Vision"
    elif re.search(r"\bhdr10\+\b", text, re.I):
        hdr = "HDR10+"
    elif re.search(r"\b(hdr10|hdr)\b", text, re.I):
        hdr = "HDR"

    # If resolution was found, build compound quality
    if res:
        parts = [res]
        if bit_depth:
            parts.append(bit_depth)
        if hdr:
            parts.append(hdr)
        return " ".join(parts)

    # 4. Fallback Source Tags if no resolution was found
    if re.search(r"\b(web\s*hd|web\s*dl|webrip)\b", text, re.I):
        return "WEB-DL"
    if re.search(r"\b(bluray|bdrip|brrip)\b", text, re.I):
        return "BluRay"
    if re.search(r"\b(hdrip|hdtv)\b", text, re.I):
        return "HDRip"
    if re.search(r"\b(dvdrip|dvd)\b", text, re.I):
        return "DVDRip"

    return "Unknown"


def parse_series_filename(filename: str, series_title: str, target_season: int = None) -> dict:
    """
    Parse a media filename to extract series metadata.
    Returns dict:
      {
         "status": "matched" | "other_season" | "invalid",
         "series": series_title,
         "season": int,
         "episode": int,
         "language": str,
         "quality": str,
         "reason": str,
      }
    """
    if not filename:
        return {"status": "invalid", "reason": "empty_filename"}

    raw_name = str(filename)
    raw_name = re.sub(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts)$", "", raw_name, flags=re.I)
    cleaned = ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), raw_name.split()))
    token_text = " " + re.sub(r"[\._\-\+\[\]\(\)\{\}]", " ", cleaned) + " "

    # 1. Season & Episode Extraction
    season_val = None
    episode_val = None

    m = re.search(r"(?i)\b(?:s|season\s*)0?(\d{1,3})\s*e(?:p(?:isode)?)?\s*0?(\d{1,3})\b", token_text)
    if m:
        season_val = int(m.group(1))
        episode_val = int(m.group(2))
    else:
        m = re.search(r"(?i)\b0?(\d{1,3})\s*x\s*0?(\d{1,3})\b", token_text)
        if m:
            season_val = int(m.group(1))
            episode_val = int(m.group(2))
        else:
            m_s = re.search(r"(?i)\b(?:s|season\s*)0?(\d{1,3})\b", token_text)
            m_e = re.search(r"(?i)\b(?:e|ep|episode\s*)0?(\d{1,3})\b", token_text)
            if m_s and m_e:
                season_val = int(m_s.group(1))
                episode_val = int(m_e.group(1))

    if season_val is None or episode_val is None or episode_val <= 0:
        return {"status": "invalid", "reason": "missing_season_or_episode"}

    # 2. Series Title Match Validation
    title_norm = _normalize(series_title)
    title_tokens = [w for w in title_norm.split() if len(w) > 1]
    if not title_tokens:
        title_tokens = [title_norm]

    clean_f_norm = _normalize(cleaned)
    matched_tokens = sum(1 for tok in title_tokens if tok in clean_f_norm)
    min_match = max(1, len(title_tokens) - (1 if len(title_tokens) >= 4 else 0))
    if matched_tokens < min_match:
        return {"status": "invalid", "reason": "title_mismatch"}

    # 3. Check Target Season
    if target_season is not None and int(season_val) != int(target_season):
        return {
            "status": "other_season",
            "series": series_title,
            "season": season_val,
            "episode": episode_val,
            "reason": f"season_{season_val}_not_target_{target_season}"
        }

    # 4. Quality Detection
    detected_quality = extract_quality_from_filename(raw_name)

    # 5. Language Detection
    detected_lang = "English"  # Default fallback when no specific regional tag is present
    f_words = re.split(r"[\s._\-\[\]\(\)\{\}\+]+", cleaned.lower())
    if "dual" in f_words and "audio" in f_words:
        detected_lang = "Dual Audio"
    elif "multi" in f_words and "audio" in f_words:
        detected_lang = "Multi Audio"
    else:
        for w in f_words:
            if w in AUTO_LANGUAGE_MAP:
                detected_lang = AUTO_LANGUAGE_MAP[w]
                break

    return {
        "status": "matched",
        "series": series_title,
        "season": season_val,
        "episode": episode_val,
        "language": detected_lang,
        "quality": detected_quality,
        "reason": "season_episode_quality_detected",
    }


async def scan_sdatabase_for_series(title: str, season: int, series_id: str = None, client: Client = None) -> dict:
    """
    Scan the stored file database (SDatabase) for files matching the given Series and Season.
    Returns structured results with valid files, organized hierarchy, and accurate statistics.
    """
    from database.ia_filterdb import col, sec_col, MULTIPLE_DATABASE
    from database.series_db import check_episode_exists

    clean_title = clean_series_title(title)
    q_tokens = [w for w in _normalize(clean_title).split() if len(w) > 1]
    if not q_tokens:
        q_tokens = [_normalize(clean_title)]

    tok_pattern = ".*".join(re.escape(t) for t in q_tokens)
    query_regex = re.compile(tok_pattern, re.IGNORECASE)

    cursor1 = col.find({"file_name": query_regex}).limit(1000)
    docs = [d for d in cursor1]
    if MULTIPLE_DATABASE:
        cursor2 = sec_col.find({"file_name": query_regex}).limit(1000)
        docs.extend([d for d in cursor2])

    # Direct search in SDATABASE_CHANNEL if client is available
    if client and SDATABASE_CHANNEL:
        try:
            search_query = " ".join(q_tokens[:3])
            async for msg in client.search_messages(chat_id=SDATABASE_CHANNEL, query=search_query, limit=500):
                media = getattr(msg, msg.media.value, None) if msg.media else None
                if not media:
                    continue
                file_name = getattr(media, "file_name", None) or getattr(msg, "caption", "") or ""
                docs.append({
                    "file_name": file_name,
                    "file_id": getattr(media, "file_id", ""),
                    "file_size": getattr(media, "file_size", 0),
                    "caption": msg.caption.html if msg.caption else None,
                    "message_id": msg.id,
                    "chat_id": msg.chat.id,
                })
        except Exception as e:
            logger.warning(f"Telegram channel search in SDATABASE_CHANNEL ({SDATABASE_CHANNEL}): {e}")

    valid_files = []
    total_scanned = len(docs)
    total_matched = 0
    total_new = 0
    total_duplicates = 0
    total_other_season = 0
    total_invalid = 0
    seen_file_keys = set()

    for doc in docs:
        fname = doc.get("file_name", "")
        parsed = parse_series_filename(fname, clean_title, season)

        status = parsed.get("status")
        if status == "invalid":
            total_invalid += 1
            logger.debug(f"[AUTO S ADD SCAN] filename={fname} match=False reason={parsed.get('reason')}")
            continue
        elif status == "other_season":
            total_other_season += 1
            logger.debug(f"[AUTO S ADD SCAN] filename={fname} match=False reason={parsed.get('reason')}")
            continue

        # Status is matched
        total_matched += 1
        lang = parsed["language"]
        ep = parsed["episode"]
        qual = parsed["quality"]

        logger.info(f"[AUTO S ADD SCAN] filename={fname} series={clean_title} season={season} episode={ep} quality={qual} language={lang} match=True reason={parsed.get('reason')}")

        key = (lang, season, ep, qual, doc.get("file_id"))
        if key in seen_file_keys:
            continue
        seen_file_keys.add(key)

        if series_id:
            is_dup = await check_episode_exists(series_id, lang, season, ep, qual)
            if is_dup:
                total_duplicates += 1
                continue

        total_new += 1
        valid_files.append({
            "language": lang,
            "season": season,
            "episode": ep,
            "quality": qual,
            "file_id": doc.get("file_id"),
            "file_name": doc.get("file_name"),
            "file_size": doc.get("file_size", 0),
            "caption": doc.get("caption"),
        })

    valid_files.sort(key=lambda x: (x["language"], x["quality"], x["episode"]))

    organized = {}
    for f in valid_files:
        l = f["language"]
        q = f["quality"]
        if l not in organized:
            organized[l] = {}
        if q not in organized[l]:
            organized[l][q] = []
        organized[l][q].append(f)

    return {
        "valid_files": valid_files,
        "organized": organized,
        "total_scanned": total_scanned,
        "total_matched": total_matched,
        "total_new": total_new,
        "total_duplicates": total_duplicates,
        "total_other_season": total_other_season,
        "total_invalid": total_invalid,
    }





# ═════════════════════════════════════════════════════════════════════════════
# ─── HELPERS ─────────────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════



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
    
    # Exclude resolution indicators to avoid matching 1080/720/480/360 as episode numbers
    clean_text = re.sub(r'\b(2160|1080|720|480|360|4k|8k)p?\b', '', text, flags=re.IGNORECASE)
    
    # Common patterns: S01E01, S1E1, E01, Episode 1, EP 01, [01], etc.
    patterns = [
        r"S\d{1,2}[\s\.\-_]?E(\d{1,4})\b",           # S01E06, S1 E6, S01-E06, S01.E06
        r"\bE[P]?[\s\.\-_]?(\d{1,4})\b",              # E06, EP06, EP 06, E-06, E.06
        r"\bEpisode[\s\.\-_]?(\d{1,4})\b",           # Episode 06, Episode-06
        r"\[(\d{1,4})\]",                             # [06], [12]
        r"\b(\d{1,4})\s*(?:st|nd|rd|th)?\s*episode\b",# 6th episode, 6 episode
        r"\b(?:ep|episode)\.?\s*(\d{1,4})\b",         # ep.06, ep 6
    ]
    for p in patterns:
        match = re.search(p, clean_text, re.IGNORECASE)
        if match:
            try:
                ep_val = int(match.group(1))
                if ep_val > 0:
                    return ep_val
            except Exception:
                continue
    return None


# Reverse lookup: short_id → full_id (populated at runtime)
_SERIES_ID_MAP: dict[str, str] = {}





async def _get_full_id(short_id: str) -> str | None:
    """Resolve a short_id back to full ObjectId string."""
    if len(short_id) == 24:
        return short_id
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


async def _normalize_series_id(value) -> str:
    if value is None:
        return ""
    val_str = str(value).strip()
    if len(val_str) == 24:
        return val_str
    full = await _get_full_id(val_str)
    return full if full else val_str


async def _match_series_id(f_sid, target_full_id) -> bool:
    if not f_sid or not target_full_id:
        return False
    str_f = str(f_sid).strip()
    str_t = str(target_full_id).strip()
    if str_f == str_t:
        return True
    norm_f = await _normalize_series_id(str_f)
    norm_t = await _normalize_series_id(str_t)
    if norm_f and norm_t and norm_f == norm_t:
        return True
    if len(str_t) == 24 and str_f == str_t[-8:]:
        return True
    if len(str_f) == 24 and str_t == str_f[-8:]:
        return True
    return False





def _series_card(series: dict, remaining_seconds: str = None) -> str:
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
        card += f"\n📁 {desc[:300]}"
    if remaining_seconds:
        card += f"\n\n⚡ <b>Result Shown in:</b> {remaining_seconds} <i>seconds</i>"
    return card


def _lang_keyboard(
    selected: list[str],
    available_langs: list[str] = None,
    show_custom: bool = False,
    custom_langs: list[str] = None,
) -> InlineKeyboardMarkup:
    if available_langs is not None:
        options = available_langs
        can_custom = False
    else:
        options = list(LANG_OPTIONS)
        if custom_langs:
            for cl in custom_langs:
                if cl not in options:
                    options.append(cl)
        for sl in selected:
            if sl not in options:
                options.append(sl)
        can_custom = show_custom

    rows = []
    for i in range(0, len(options), 3):
        row = []
        for lang in options[i:i+3]:
            tick = "🟢 " if lang in selected else ""
            row.append(InlineKeyboardButton(f"{tick}{lang}", callback_data=f"sw#lang#{lang}"))
        rows.append(row)

    if can_custom:
        rows.append([InlineKeyboardButton("➕ Custom Language", callback_data="sw#custom_lang")])

    rows.append([
        InlineKeyboardButton("🟢 Submit", callback_data="sw#lang#submit"),
        InlineKeyboardButton("⬅️ Back", callback_data="sw#lang#back"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _season_keyboard(
    max_seasons: int,
    selected: list[int],
    show_skip: bool = False,
    available_seasons: list[int] = None,
) -> InlineKeyboardMarkup:
    rows = []
    if available_seasons is not None:
        for i in range(0, len(available_seasons), 3):
            row = []
            for s in available_seasons[i:i+3]:
                tick = "🟢 " if s in selected else ""
                label = f"S{s}" if s > 0 else "Direct Episodes"
                row.append(InlineKeyboardButton(f"{tick}{label}", callback_data=f"sw#season#{s}"))
            rows.append(row)
        control_row = [InlineKeyboardButton("🟢 Submit", callback_data="sw#season#submit")]
        rows.append(control_row)
    else:
        for i in range(1, max_seasons + 1, 3):
            row = []
            for s in range(i, min(i + 3, max_seasons + 1)):
                tick = "🟢 " if s in selected else ""
                row.append(InlineKeyboardButton(f"{tick}S{s}", callback_data=f"sw#season#{s}"))
            rows.append(row)
        
        control_row = [InlineKeyboardButton("🟢 Submit", callback_data="sw#season#submit")]
        if show_skip:
            control_row.append(InlineKeyboardButton("⏭️ Skip Season", callback_data="sw#season#skip"))
        rows.append(control_row)
    
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data="sw#season#back"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _quality_keyboard(
    selected: list[str],
    already_saved: list[str] = None,
    available_qualities: list[str] = None,
    show_custom: bool = False,
    custom_quals: list[str] = None,
) -> InlineKeyboardMarkup:
    """
    selected            — qualities chosen for the CURRENT batch (shown with 🟢)
    already_saved       — qualities already committed to the series (shown with ✅)
    available_qualities — if in edit mode, show only qualities that exist in DB for this Lang+Season
    show_custom         — show [➕ Custom Quality] during first-time Series creation
    """
    already_saved = already_saved or []
    if available_qualities is not None:
        options = available_qualities
        can_custom = False
    else:
        options = list(QUALITY_OPTIONS)
        if custom_quals:
            for cq in custom_quals:
                if cq not in options:
                    options.append(cq)
        for sq in selected:
            if sq not in options:
                options.append(sq)
        can_custom = show_custom

    rows = []
    for i in range(0, len(options), 3):
        row = []
        for q in options[i:i+3]:
            if q in selected:
                tick = "🟢 "
                cb = f"sw#quality#{q}"
            elif available_qualities is None and q in already_saved:
                tick = "✅ "
                cb = f"sw#quality_used#{q}"
            else:
                tick = ""
                cb = f"sw#quality#{q}"
            row.append(InlineKeyboardButton(
                f"{tick}{q}",
                callback_data=cb
            ))
        rows.append(row)

    if can_custom:
        rows.append([InlineKeyboardButton("➕ Custom Quality", callback_data="sw#custom_qual")])

    rows.append([
        InlineKeyboardButton("🟢 Submit", callback_data="sw#quality#submit"),
        InlineKeyboardButton("⬅️ Back", callback_data="sw#quality#back"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel"),
    ])
    return InlineKeyboardMarkup(rows)


async def _get_used_qualities(wiz: dict) -> list[str]:
    series_id = wiz.get("series_id")
    if not series_id:
        return []
    langs = wiz.get("batch_langs") or wiz.get("languages") or []
    seasons = wiz.get("batch_seasons") or wiz.get("seasons") or [0]
    used = set()
    for lang in langs:
        for season in seasons:
            quals = await list_season_qualities(series_id, lang, season)
            used.update(quals)
    return list(used)


async def _get_edit_available_langs(wiz: dict) -> list[str] | None:
    if wiz.get("mode") == "edit" and wiz.get("series_id") and wiz.get("add_mode") == "episode":
        db_langs = await list_series_languages(wiz["series_id"])
        if db_langs:
            return [l for l in LANG_OPTIONS if l in db_langs] + [l for l in db_langs if l not in LANG_OPTIONS]
        return []
    return None


async def _get_edit_available_seasons(wiz: dict) -> list[int] | None:
    if wiz.get("mode") == "edit" and wiz.get("series_id") and wiz.get("add_mode") == "episode":
        langs = wiz.get("batch_langs") or []
        if langs:
            lang = langs[0]
            db_seasons = await list_series_seasons(wiz["series_id"], lang)
            return sorted(db_seasons)
        return []
    return None


async def _get_edit_available_qualities(wiz: dict) -> list[str] | None:
    if wiz.get("mode") == "edit" and wiz.get("series_id") and wiz.get("add_mode") == "episode":
        langs = wiz.get("batch_langs") or []
        seasons = wiz.get("batch_seasons") or []
        if langs and seasons:
            lang = langs[0]
            season = seasons[0]
            db_quals = await list_season_qualities(wiz["series_id"], lang, season)
            return [q for q in QUALITY_OPTIONS if q in db_quals] + [q for q in db_quals if q not in QUALITY_OPTIONS]
        return []
    return None


def _should_show_skip_season(wiz: dict) -> bool:
    """
    Check whether to display [⏭️ Skip Season] button.
    If the previous successful Add Files operation for ALL selected languages was 'explicit', hide Skip Season.
    If 'skipped' or no previous operation for the language, show Skip Season.
    """
    batch_langs = wiz.get("batch_langs") or []
    if not batch_langs:
        return True
    season_modes = wiz.get("season_modes") or {}
    for lang in batch_langs:
        if season_modes.get(lang) == "explicit":
            return False
    return True


def _config_menu_keyboard(series_id: str = None, from_viewseries: bool = False) -> InlineKeyboardMarkup:
    if series_id:
        # Existing series editing mode: show both Add Episode and Add Files
        buttons = [
            [
                InlineKeyboardButton("➕ Add Episode", callback_data="sw#menu#add_ep"),
                InlineKeyboardButton("📁 Add Files", callback_data="sw#menu#batch")
            ]
        ]
        buttons.append([InlineKeyboardButton("🗑 Delete Series", callback_data=f"sw#del_series#{series_id}")])
    else:
        # New series creation mode: only show Add Files
        buttons = [
            [
                InlineKeyboardButton("📁 Add Files", callback_data="sw#menu#batch")
            ]
        ]
    
    save_row = [
        InlineKeyboardButton("🟢 Save", callback_data="sw#save"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sw#cancel")
    ]
    if from_viewseries:
        save_row.append(InlineKeyboardButton("⬅️ Back", callback_data="sw#vser_back"))
        
    buttons.append(save_row)
    return InlineKeyboardMarkup(buttons)





def _batch_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Yes",  callback_data="sw#bconfirm#yes"),
            InlineKeyboardButton("🔴 No",       callback_data="sw#bconfirm#no"),
        ]
    ])





def _duplicate_file_keyboard(data_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Replace", callback_data=f"sw#dup#replace#{data_key}"),
            InlineKeyboardButton("🔴 Keep",    callback_data=f"sw#dup#keep#{data_key}"),
        ]
    ])





# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── USER NAVIGATION KEYBOARD BUILDERS ───────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 



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
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)





async def _user_quality_keyboard(user_id: int, full_id: str, sid: str, lang: str, season: int, quals: list[str], rating: str, is_private: bool = False) -> InlineKeyboardMarkup:
    rows = []
    import logging
    log = logging.getLogger(__name__)
    for i in range(0, len(quals), 3):
        row = []
        for q in quals[i:i+3]:
            row.append(InlineKeyboardButton(q, callback_data=f"sr#{sid}#l#{lang}#s#{season}#q#{q}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=f"sr#{sid}#home" if season == 0 else f"sr#{sid}#l#{lang}"),
        InlineKeyboardButton("🏠 Home", callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)





# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ─── GLOBAL THUMBNAIL COMMANDS ───────────────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  



@Client.on_message(filters.command("thumpseries"), group=1)
async def cmd_thumpseries(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")
        
    if not hasattr(temp, "SETTING_SERIES_THUMB"):
        temp.SETTING_SERIES_THUMB = {}
        
    prompt = await message.reply_text(
        "Send me the image you want to use for Series Search.",
        reply_to_message_id=message.id,
        reply_markup=ForceReply(selective=True)
    )
    temp.SETTING_SERIES_THUMB[message.from_user.id] = {
        "command_msg_id": message.id,
        "prompt_msg_id": prompt.id
    }



@Client.on_message(filters.command("delthumbseries") & filters.private, group=1)
async def cmd_delthumbseries(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")
        
    from database.series_db import delete_series_thumbnail, get_series_thumbnail
    existing = await get_series_thumbnail()
    if existing:
        await delete_series_thumbnail()
        await message.reply_text("✅ Series search thumbnail removed.")
    else:
        await message.reply_text("ℹ️  No Series search thumbnail is currently set.")





# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ─── /series & /seriesfil —” ADMIN ENTRY POINTS ──────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  


@Client.on_message(filters.command(["series"]) & filters.private, group=1)
async def cmd_series_menu(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Manual Adding", callback_data="sw#start_manual"),
            InlineKeyboardButton("🤖 Auto S Add", callback_data="sw#start_auto")
        ]
    ])
    await message.reply_text(
        "🎬 <b>Series Management</b>\n\nChoose an option below to proceed:",
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command("seriesfil") & filters.private, group=1)
async def cmd_seriesfil(client: Client, message: Message):
    if not _is_admin(message.from_user.id):
        return await message.reply_text("❌ You are not authorized to use this command.")

    uid = message.from_user.id
    temp.SERIES_WIZARD[uid] = {
        "mode": "add",
        "state": S_NAME,
        "name": "", "year": "", "genre": "", "description": "",
        "languages": [], "seasons": [], "qualities": [],
        "series_id": None,
        "season_modes": {},
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



# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ─── /ed_series —” EDIT WIZARD ────────────────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  



@Client.on_callback_query(filters.regex(r"^edser#"))
async def cb_edser(client: Client, query: CallbackQuery):
    logger.info("[VIEW SERIES EDIT] callback=%s", query.data)
    is_admin = False
    if query.message and query.message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        admin_list = await client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        is_admin = any(admin.user.id == query.from_user.id for admin in admin_list if admin.user)
    else:
        is_admin = query.from_user.id in ADMINS
    if not is_admin:
        return await query.answer("❌ You are not authorized.", show_alert=True)
    
    uid = query.from_user.id
    from utils import temp
    from database.series_db import get_series
    
    series_id = query.data.split("#")[1]
    exact = await get_series(series_id)
    if not exact:
        return await query.answer("Series not found.", show_alert=True)
        
    temp.SERIES_WIZARD[uid] = {
        "mode": "edit",
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
        "season_modes": exact.get("season_modes", {}),
        "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
        "batch_data": None,
        "from_viewseries": True
    }
    
    wiz = temp.SERIES_WIZARD[uid]
    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={series_id}\naction=OPEN")
    
    await query.message.edit_text(
        _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
        reply_markup=_config_menu_keyboard(wiz.get("series_id"), True),
        parse_mode=enums.ParseMode.HTML,
    )
    await query.answer()





@Client.on_message(filters.command(["ed_series"]), group=1)
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
        "mode": "edit",
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
        "season_modes": exact.get("season_modes", {}),
        "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
        "batch_data": None,
        "from_viewseries": False
    }
    
    wiz = temp.SERIES_WIZARD[uid]
    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=OPEN")
    await message.reply_text(
        _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
        reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
        parse_mode=enums.ParseMode.HTML,
    )





# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── /cancel — ABORT WIZARD ──────────────────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 



@Client.on_message(filters.command("cancel") & filters.private, group=1)
async def cmd_cancel(client: Client, message: Message):
    uid = message.from_user.id
    cancelled = False
    
    if hasattr(temp, "SETTING_SERIES_THUMB") and temp.SETTING_SERIES_THUMB.get(uid):
        del temp.SETTING_SERIES_THUMB[uid]
        cancelled = True
        
    if uid in temp.SERIES_WIZARD:
        del temp.SERIES_WIZARD[uid]
        cancelled = True
        
    if cancelled:
        await message.reply_text("❌ Action cancelled.")
    else:
        await message.reply_text("No active wizard or session to cancel.")





# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── TEXT HANDLER — WIZARD STEPS ─────────────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 



@Client.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(
    ["seriesfil", "sbatch", "slink", "cancel", "start", "help", "settings",
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
     "setskip", "deleteall", "channel",
     "viewseries", "serieslist", "delseries", "seriesdel",
     "thumpseries", "delthumbseries", "ed_series"]
), group=1)
async def wizard_text_handler(client: Client, message: Message):
    uid = message.from_user.id
    
    if hasattr(temp, "SETTING_SERIES_THUMB") and temp.SETTING_SERIES_THUMB.get(uid):
        thumb_state = temp.SETTING_SERIES_THUMB.get(uid)
        if message.photo:
            from database.series_db import save_series_thumbnail
            try:
                await save_series_thumbnail(message.photo.file_id)
            except Exception as e:
                return await message.reply_text(f"❌ Failed to save thumbnail: {e}")
                
            del temp.SETTING_SERIES_THUMB[uid]
            
            cmd_msg_id = thumb_state.get("command_msg_id") if isinstance(thumb_state, dict) else None
            prompt_msg_id = thumb_state.get("prompt_msg_id") if isinstance(thumb_state, dict) else None
            
            try:
                await client.delete_messages(message.chat.id, [
                    m_id for m_id in [cmd_msg_id, prompt_msg_id, message.id] if m_id
                ])
            except Exception:
                pass
                
            success_msg = await message.reply_text("✅ Series thumbnail updated successfully!")
            
            import asyncio
            async def del_success(m):
                await asyncio.sleep(5)
                try:
                    await m.delete()
                except Exception:
                    pass
            asyncio.create_task(del_success(success_msg))
            return
        else:
            return await message.reply_text("⚠️ Please send a PHOTO to set as thumbnail, or /cancel to abort.")

    text = message.text.strip() if message.text else ""

    # ── Auto S Add IMDb Input Handler ────────────────────────────────────────
    if uid in temp.AUTO_SERIES:
        auto_data = temp.AUTO_SERIES[uid]
        if auto_data.get("state") == "WAIT_IMDB":
            if not text:
                return await message.reply_text("⚠️ Please send a valid IMDb link or ID.")

            if text.lower() == "/cancel":
                del temp.AUTO_SERIES[uid]
                return await message.reply_text("❌ Auto S Add cancelled.")

            m_imdb = re.search(r"(tt\d{5,10})", text, re.I)
            if not m_imdb:
                return await message.reply_text(
                    "❌ <b>Invalid IMDb link or ID.</b>\n\n"
                    "Please provide a valid IMDb URL (e.g. <code>https://www.imdb.com/title/tt9288030/</code>) or ID (<code>tt9288030</code>).",
                    parse_mode=enums.ParseMode.HTML,
                )

            imdb_id = m_imdb.group(1).lower()
            loading_msg = await message.reply_text("⏳ Fetching IMDb metadata, please wait...")

            info = None
            try:
                info = await get_poster(imdb_id, id=True)
                logger.info(f"[AUTO S ADD IMDb] id={imdb_id} status={'success' if info else 'failed'} title={info.get('title') if info else None}")
            except Exception as e:
                logger.error(f"[AUTO S ADD IMDb] id={imdb_id} error={e}")
                info = None

            if not info or not info.get("title"):
                return await loading_msg.edit_text(
                    f"❌ <b>Could not retrieve IMDb data for <code>{imdb_id}</code>.</b>\n"
                    "Please try again later or check the IMDb link, or send /cancel to abort.",
                    parse_mode=enums.ParseMode.HTML,
                )

            # ── Series Validation ──
            kind = str(info.get("kind", "")).lower()
            if kind in ["movie", "feature"]:
                return await loading_msg.edit_text(
                    f"⚠️ <b>This IMDb title (<code>{info['title']}</code>) is not a TV Series.</b>\n\n"
                    "Please send a valid Series IMDb link, or send /cancel to abort.",
                    parse_mode=enums.ParseMode.HTML,
                )

            existing = await get_series_by_name(info["title"])
            if not existing:
                matches = await search_series(info["title"])
                if matches and _normalize(matches[0]["name"]) == _normalize(info["title"]):
                    existing = matches[0]

            tot_seasons = 15
            if info.get("seasons") and str(info["seasons"]).isdigit():
                tot_seasons = max(1, min(int(info["seasons"]), 15))

            auto_data.update({
                "state": "CONFIRM_IMDB",
                "imdb_id": info.get("imdb_id", imdb_id),
                "title": info["title"],
                "year": str(info.get("year") or "N/A"),
                "genre": info.get("genres", "N/A"),
                "rating": str(info.get("rating") or ""),
                "description": info.get("plot", ""),
                "poster": info.get("poster") or "",
                "total_seasons": tot_seasons,
                "existing_series_id": str(existing["_id"]) if existing else None,
            })

            rating_str = f"\n⭐ <b>Rating:</b> {auto_data['rating']}/10" if auto_data['rating'] else ""
            exist_str = "\n\nℹ️ <i>Existing series found in database. New files will be attached without duplicating existing episodes.</i>" if existing else ""

            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 Select Season", callback_data="sw#auto_sel_season")],
                [InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]
            ])

            caption = (
                f"🎬 <b>{auto_data['title']}</b>\n"
                f"📅 <b>Year:</b> {auto_data['year']}\n"
                f"🎭 <b>Genre:</b> {auto_data['genre']}"
                f"{rating_str}\n"
                f"🆔 <b>IMDb:</b> <code>{auto_data['imdb_id']}</code>"
                f"{exist_str}\n\n"
                "Click below to select season to scan:"
            )

            await loading_msg.delete()
            await message.reply_text(
                caption,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML,
            )
            try:
                message.stop_propagation()
            except Exception:
                pass
            return

    if uid not in temp.SERIES_WIZARD:
        return

    wiz = temp.SERIES_WIZARD[uid]
    state = wiz.get("state")

    # ── Series Name ──────────────────────────────────────────────────────────
    if state == S_NAME:
        if not text:
            return await message.reply_text("Please enter a valid series name.")
        
        # Check duplicate if in add mode
        if wiz["mode"] == "add":
            existing = await get_series_by_name(text)
            if existing:
                return await message.reply_text(
                    f"⚠️ A series named <b>{text}</b> already exists.\n"
                    f"Please send a different name, or /cancel to abort.",
                    parse_mode=enums.ParseMode.HTML,
                )
        wiz["name"] = text
        wiz["state"] = S_YEAR
        await message.reply_text(
            f"✅ Name set to: <b>{text}</b>\n\n"
            f"Now send the <b>release year</b> (e.g. <code>2023</code>) or send /skip.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Year ─────────────────────────────────────────────────────────────────
    elif state == S_YEAR:
        if text.lower() == "/skip":
            wiz["year"] = ""
        else:
            wiz["year"] = text
        wiz["state"] = S_GENRE
        await message.reply_text(
            f"📅 Year saved.\n\nNow send the <b>genre(s)</b> (e.g. <code>Action, Drama, Sci-Fi</code>) or send /skip.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Genre ────────────────────────────────────────────────────────────────
    elif state == S_GENRE:
        if text.lower() == "/skip":
            wiz["genre"] = ""
        else:
            wiz["genre"] = text
        wiz["state"] = S_RATING
        await message.reply_text(
            f"🎭 Genre saved.\n\nNow send the <b>IMDb rating</b> (e.g. <code>8.5/10</code>) or send /skip.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Rating ───────────────────────────────────────────────────────────────
    elif state == S_RATING:
        if text.lower() == "/skip":
            wiz["rating"] = ""
        else:
            wiz["rating"] = text
        wiz["state"] = S_DESC
        await message.reply_text(
            f"⭐ Rating saved.\n\nNow send a <b>short description</b> or send /skip.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Description ───────────────────────────────────────────────────────────
    elif state == S_DESC:
        if text.lower() == "/skip":
            wiz["description"] = ""
        else:
            wiz["description"] = text
        wiz["state"] = S_POSTER
        await message.reply_text(
            f"📝 Description saved.\n\nNow send a <b>poster / banner image</b> or send /skip.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Poster ────────────────────────────────────────────────────────────────
    elif state == S_POSTER:
        if message.photo:
            wiz["poster"] = message.photo.file_id
        elif text.lower() == "/skip":
            wiz["poster"] = ""
        else:
            return await message.reply_text("Please send a photo or /skip.")

        wiz["state"] = S_DONE
        await message.reply_text(
            _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
            reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Custom Language Input ────────────────────────────────────────────────
    elif state == S_CUSTOM_LANG_WAIT:
        raw = text.strip()
        if not raw or len(raw) < 2 or len(raw) > 40 or any(c in raw for c in "\n\r\t<>|{}[]"):
            return await message.reply_text("⚠️ Please enter a valid language name (2-40 characters).")

        norm_lang = raw.title()

        # Duplicate check against standard and current custom languages
        all_existing = list(LANG_OPTIONS) + wiz.get("custom_langs", []) + wiz.get("languages", [])
        if any(norm_lang.lower() == l.lower() for l in all_existing):
            return await message.reply_text(
                f"⚠️ This language already exists: <b>{norm_lang}</b>\n\nPlease send a different custom language name, or send /cancel to abort.",
                parse_mode=enums.ParseMode.HTML,
            )

        wiz["pending_custom_lang"] = norm_lang
        wiz["state"] = S_CUSTOM_LANG_CONF
        await message.reply_text(
            f"🌐 <b>Custom Language:</b>\n{norm_lang}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="sw#conf_custom_lang"),
                    InlineKeyboardButton("✏️ Change", callback_data="sw#custom_lang"),
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel_custom_lang"),
                ]
            ]),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Custom Quality Input ─────────────────────────────────────────────────
    elif state == S_CUSTOM_QUAL_WAIT:
        raw = text.strip()
        if not raw or len(raw) < 2 or len(raw) > 40 or any(c in raw for c in "\n\r\t<>|{}[]"):
            return await message.reply_text("⚠️ Please enter a valid quality name (2-40 characters).")

        norm_qual = re.sub(r"\s+", " ", raw).strip()

        # Duplicate check against standard and current custom qualities
        all_existing = list(QUALITY_OPTIONS) + wiz.get("custom_quals", []) + wiz.get("qualities", [])
        if any(norm_qual.lower() == q.lower() for q in all_existing):
            return await message.reply_text(
                f"⚠️ This quality already exists: <b>{norm_qual}</b>\n\nPlease send a different custom quality name, or send /cancel to abort.",
                parse_mode=enums.ParseMode.HTML,
            )

        wiz["pending_custom_qual"] = norm_qual
        wiz["state"] = S_CUSTOM_QUAL_CONF
        await message.reply_text(
            f"🎞 <b>Custom Quality:</b>\n{norm_qual}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="sw#conf_custom_qual"),
                    InlineKeyboardButton("✏️ Change", callback_data="sw#custom_qual"),
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel_custom_qual"),
                ]
            ]),
            parse_mode=enums.ParseMode.HTML,
        )

    elif state == S_BATCH_WAIT:
        if text and (text.startswith("https://t.me/") or text.startswith("http://t.me/")):
            message.text = f"/slink {text}"
            return await cmd_slink(client, message)


# ══════════════════════════════════════════════════════════════════════════════
# ─── CALLBACK HANDLER — WIZARD BUTTONS ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^sw#"))
async def wizard_callback(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    if not _is_admin(uid):
        return await query.answer("❌ Not authorized.", show_alert=True)

    data = query.data
    parts = data.split("#")
    action = parts[1] if len(parts) > 1 else ""

    if not action:
        return await query.answer()

    # ── Auto S Add & Menu Entry Callbacks ────────────────────────────────────
    if action == "start_manual":
        temp.SERIES_WIZARD[uid] = {
            "mode": "add",
            "state": S_NAME,
            "name": "", "year": "", "genre": "", "description": "",
            "languages": [], "seasons": [], "qualities": [],
            "series_id": None,
            "season_modes": {},
            "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
            "batch_data": None,
        }
        await query.message.edit_text(
            f"🎬 <b>Create New Series</b>\n\n"
            f"Hey {query.from_user.mention}, please send the <b>series name</b>.",
            reply_markup=None,
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    if action == "start_auto":
        temp.AUTO_SERIES[uid] = {
            "state": "WAIT_IMDB",
            "admin_id": uid,
        }
        await query.message.edit_text(
            "🤖 <b>Auto S Add — Series Importer</b>\n\n"
            "🎬 <b>Send IMDb link:</b>\n\n"
            "Example:\n<code>https://www.imdb.com/title/tt4574334/</code>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
            ]]),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    if action == "auto_sel_season":
        auto_data = temp.AUTO_SERIES.get(uid)
        if not auto_data:
            return await query.answer("Session expired. Send /series to start again.", show_alert=True)

        tot = auto_data.get("total_seasons", 15)
        rows = []
        for i in range(1, tot + 1, 3):
            row = []
            for s in range(i, min(i + 3, tot + 1)):
                row.append(InlineKeyboardButton(f"Season {s}", callback_data=f"sw#auto_season#{s}"))
            rows.append(row)
        rows.append([InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")])

        await query.message.edit_text(
            f"🎬 <b>{auto_data['title']}</b>\n\n"
            "Select <b>season</b> to scan from SDatabase:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    if action == "auto_season":
        season_num = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        auto_data = temp.AUTO_SERIES.get(uid)
        if not auto_data:
            return await query.answer("Session expired. Send /series to start again.", show_alert=True)

        auto_data["season"] = season_num
        await query.message.edit_text(
            f"🔍 <b>Scanning SDatabase...</b>\n\n"
            f"Searching for <b>{auto_data['title']} — Season {season_num}</b> files...",
            parse_mode=enums.ParseMode.HTML,
        )

        res = await scan_sdatabase_for_series(auto_data["title"], season_num, auto_data.get("existing_series_id"), client=client)
        auto_data["scan"] = res

        if res["total_new"] == 0 and res["total_duplicates"] == 0:
            text = (
                f"📊 <b>AUTO SCAN RESULT</b>\n\n"
                f"🎬 <b>Series:</b> {auto_data['title']}\n"
                f"📅 <b>Year:</b> {auto_data['year']}\n"
                f"📺 <b>Season:</b> {season_num}\n\n"
                f"⚠️ <b>No matching files found in SDatabase for Season {season_num}.</b>\n\n"
                f"📁 <b>Files scanned:</b> {res['total_scanned']}\n"
                f"✅ <b>Matching files:</b> {res['total_matched']}\n"
                f"➕ <b>New files:</b> {res['total_new']}\n"
                f"♻️ <b>Existing duplicates:</b> {res['total_duplicates']}\n"
                f"⏭ <b>Other season:</b> {res['total_other_season']}\n"
                f"❌ <b>Invalid:</b> {res['total_invalid']}\n\n"
                "Make sure files in SDatabase contain proper title and episode tags (e.g. <code>Reacher.S01E03.480p.WEB-HD.x264.mkv</code>)."
            )
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Rescan", callback_data="sw#auto_rescan")],
                [InlineKeyboardButton("📺 Change Season", callback_data="sw#auto_sel_season")],
                [InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]
            ])
            await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            return await query.answer("Scan complete: 0 matching files found.")

        lines = []
        for lang, quals in res["organized"].items():
            for qual, flist in quals.items():
                ep_strs = [f"E{f['episode']:02d}" for f in flist]
                lines.append(f"• <b>{lang} / {qual}:</b> {', '.join(ep_strs)} ({len(flist)} files)")

        episodes_summary = "\n".join(lines)
        langs_list = ", ".join(res["organized"].keys())

        text = (
            f"📊 <b>AUTO SCAN RESULT</b>\n\n"
            f"🎬 <b>Series:</b> {auto_data['title']}\n"
            f"📅 <b>Year:</b> {auto_data['year']}\n"
            f"📺 <b>Season:</b> {season_num}\n\n"
            f"📁 <b>Files scanned:</b> {res['total_scanned']}\n"
            f"✅ <b>Matching files:</b> {res['total_matched']}\n"
            f"➕ <b>New files:</b> {res['total_new']}\n"
            f"♻️ <b>Existing duplicates:</b> {res['total_duplicates']}\n"
            f"⏭ <b>Other season:</b> {res['total_other_season']}\n"
            f"❌ <b>Invalid:</b> {res['total_invalid']}\n\n"
            f"🌐 <b>Languages:</b> {langs_list}\n\n"
            f"🎞 <b>Qualities & Episodes:</b>\n{episodes_summary}"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Save Series", callback_data="sw#auto_save")],
            [InlineKeyboardButton("🔄 Rescan", callback_data="sw#auto_rescan")],
            [InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]
        ])
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return await query.answer(f"Scan complete: {res['total_new']} new files ready to import!")

    if action == "auto_rescan":
        auto_data = temp.AUTO_SERIES.get(uid)
        if not auto_data or "season" not in auto_data:
            return await query.answer("Session expired. Send /series to start again.", show_alert=True)

        season_num = auto_data["season"]
        await query.message.edit_text(
            f"🔄 <b>Rescanning SDatabase...</b>\n\n"
            f"Searching for <b>{auto_data['title']} — Season {season_num}</b> files...",
            parse_mode=enums.ParseMode.HTML,
        )

        res = await scan_sdatabase_for_series(auto_data["title"], season_num, auto_data.get("existing_series_id"), client=client)
        auto_data["scan"] = res

        if res["total_new"] == 0 and res["total_duplicates"] == 0:
            text = (
                f"📊 <b>AUTO SCAN RESULT</b>\n\n"
                f"🎬 <b>Series:</b> {auto_data['title']}\n"
                f"📅 <b>Year:</b> {auto_data['year']}\n"
                f"📺 <b>Season:</b> {season_num}\n\n"
                f"⚠️ <b>No matching files found in SDatabase for Season {season_num}.</b>\n\n"
                f"📁 <b>Files scanned:</b> {res['total_scanned']}\n"
                f"✅ <b>Matching files:</b> {res['total_matched']}\n"
                f"➕ <b>New files:</b> {res['total_new']}\n"
                f"♻️ <b>Existing duplicates:</b> {res['total_duplicates']}\n"
                f"⏭ <b>Other season:</b> {res['total_other_season']}\n"
                f"❌ <b>Invalid:</b> {res['total_invalid']}"
            )
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Rescan", callback_data="sw#auto_rescan")],
                [InlineKeyboardButton("📺 Change Season", callback_data="sw#auto_sel_season")],
                [InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]
            ])
            await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            return await query.answer("Rescan complete: 0 matching files found.")

        lines = []
        for lang, quals in res["organized"].items():
            for qual, flist in quals.items():
                ep_strs = [f"E{f['episode']:02d}" for f in flist]
                lines.append(f"• <b>{lang} / {qual}:</b> {', '.join(ep_strs)} ({len(flist)} files)")

        episodes_summary = "\n".join(lines)
        langs_list = ", ".join(res["organized"].keys())

        text = (
            f"📊 <b>AUTO SCAN RESULT</b>\n\n"
            f"🎬 <b>Series:</b> {auto_data['title']}\n"
            f"📅 <b>Year:</b> {auto_data['year']}\n"
            f"📺 <b>Season:</b> {season_num}\n\n"
            f"📁 <b>Files scanned:</b> {res['total_scanned']}\n"
            f"✅ <b>Matching files:</b> {res['total_matched']}\n"
            f"➕ <b>New files:</b> {res['total_new']}\n"
            f"♻️ <b>Existing duplicates:</b> {res['total_duplicates']}\n"
            f"⏭ <b>Other season:</b> {res['total_other_season']}\n"
            f"❌ <b>Invalid:</b> {res['total_invalid']}\n\n"
            f"🌐 <b>Languages:</b> {langs_list}\n\n"
            f"🎞 <b>Qualities & Episodes:</b>\n{episodes_summary}"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Save Series", callback_data="sw#auto_save")],
            [InlineKeyboardButton("🔄 Rescan", callback_data="sw#auto_rescan")],
            [InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]
        ])
        await query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return await query.answer(f"Rescan complete: {res['total_new']} new files ready to import!")

    if action == "auto_save":
        auto_data = temp.AUTO_SERIES.get(uid)
        if not auto_data or "scan" not in auto_data or not auto_data["scan"].get("valid_files"):
            return await query.answer("⚠️ No valid scan data to save.", show_alert=True)

        res = auto_data["scan"]
        season = auto_data["season"]
        existing_series_id = auto_data.get("existing_series_id")

        if not existing_series_id:
            series_id = await create_series({
                "name": auto_data["title"],
                "year": auto_data["year"],
                "genre": auto_data["genre"],
                "rating": auto_data["rating"],
                "description": auto_data["description"],
                "poster": auto_data["poster"],
                "languages": list(res["organized"].keys()),
                "seasons": [season],
                "qualities": list(set(f["quality"] for f in res["valid_files"])),
                "season_modes": {},
                "created_by": uid,
            })
        else:
            series_id = existing_series_id
            cur = await get_series(series_id)
            new_langs = list(set((cur.get("languages") or []) + list(res["organized"].keys())))
            new_seasons = list(set((cur.get("seasons") or []) + [season]))
            new_quals = list(set((cur.get("qualities") or []) + [f["quality"] for f in res["valid_files"]]))
            await update_series(series_id, {
                "languages": new_langs,
                "seasons": new_seasons,
                "qualities": new_quals,
            })

        added_count = 0
        for f in res["valid_files"]:
            ok, _ = await add_series_file({
                "series_id": series_id,
                "language": f["language"],
                "season": f["season"],
                "episode": f["episode"],
                "quality": f["quality"],
                "file_id": f["file_id"],
                "file_name": f["file_name"],
                "file_size": f["file_size"],
                "is_batch": False,
            })
            if ok:
                added_count += 1

        ep_lines = []
        for lang, quals in res["organized"].items():
            for qual, flist in quals.items():
                min_ep = min(f["episode"] for f in flist)
                max_ep = max(f["episode"] for f in flist)
                if min_ep == max_ep:
                    ep_lines.append(f"• E{min_ep:02d} {lang} ({qual})")
                else:
                    ep_lines.append(f"• E{min_ep:02d} – E{max_ep:02d} {lang} ({qual})")

        ep_summary = "\n".join(ep_lines)
        langs_summary = "\n".join(f"• {l}" for l in res["organized"].keys())

        del temp.AUTO_SERIES[uid]

        success_text = (
            f"✅ <b>AUTO SERIES ADD COMPLETED</b>\n\n"
            f"🎬 <b>{auto_data['title']}</b>\n"
            f"📅 {auto_data['year']}\n\n"
            f"📺 <b>Season:</b> {season}\n\n"
            f"🌐 <b>Languages:</b>\n{langs_summary}\n\n"
            f"📁 <b>Files Added:</b> {added_count}\n\n"
            f"🎞 <b>Episodes:</b>\n{ep_summary}"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Search Series", switch_inline_query_current_chat=auto_data['title'])],
            [InlineKeyboardButton("✏️ Edit Series", callback_data=f"edser#{series_id}")],
            [InlineKeyboardButton("🏠 Close", callback_data="sw#auto_close")]
        ])

        await query.message.edit_text(success_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        return await query.answer("🎉 Series files saved successfully!")

    if action == "auto_cancel":
        if uid in temp.AUTO_SERIES:
            del temp.AUTO_SERIES[uid]
        await query.message.edit_text("❌ <b>Auto S Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)
        return await query.answer("Cancelled.")

    if action == "auto_close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return await query.answer()

    if uid not in temp.SERIES_WIZARD:
        return await query.answer("No active wizard. Run /series first.", show_alert=True)

    wiz = temp.SERIES_WIZARD[uid]

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
        
    if action == "vser_back":
        if uid in temp.SERIES_WIZARD:
            del temp.SERIES_WIZARD[uid]
        from database.series_db import list_all_series
        all_series = await list_all_series()
        seen = set()
        unique_series = []
        for s in all_series:
            name = s.get("name", "").strip()
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_series.append(s)
        unique_series.sort(key=lambda x: x.get("name", "").lower())
        return await send_series_list(query, unique_series, page=0)
        
    if action == "back_to_menu":
        wiz["state"] = S_DONE
        return await query.message.edit_text(
            _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nClick Add Files to add episodes or click Save:",
            reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Cancel ────────────────────────────────────────────────────────────────
    if action == "cancel":
        if wiz.get("state") in [S_BATCH_LANG, S_BATCH_SEASON, S_BATCH_QUAL, S_BATCH_WAIT, S_LANGS, S_SEASONS, S_QUALITY]:
            wiz["state"] = S_DONE
            await query.message.edit_text(
                _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nClick Add Files to add episodes or click Save:",
                reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            if uid in temp.SERIES_WIZARD:
                del temp.SERIES_WIZARD[uid]
            await query.message.edit_text("❌ Series configuration cancelled.")
        return await query.answer()

    # ── Save ──────────────────────────────────────────────────────────────────
    if action == "save":
        if not wiz.get("name"):
            return await query.answer("⚠️ Series name is missing.", show_alert=True)
        if not wiz.get("languages"):
            return await query.answer("⚠️ Please add at least one file/language before saving.", show_alert=True)

        if not wiz.get("series_id"):
            series_id = await create_series({
                "name": wiz["name"],
                "year": wiz.get("year", ""),
                "genre": wiz.get("genre", ""),
                "rating": wiz.get("rating", ""),
                "description": wiz.get("description", ""),
                "poster": wiz.get("poster"),
                "languages": wiz.get("languages", []),
                "seasons": wiz.get("seasons", []),
                "qualities": wiz.get("qualities", []),
                "season_modes": wiz.get("season_modes", {}),
            })
            wiz["series_id"] = series_id
            logger.info(f"[SERIES ADD]\nuser_id={uid}\nseries_id={series_id}\naction=SERIES_SAVED")
        else:
            await update_series(wiz["series_id"], {
                "languages": wiz.get("languages", []),
                "seasons": wiz.get("seasons", []),
                "qualities": wiz.get("qualities", []),
                "season_modes": wiz.get("season_modes", {}),
            })
            logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=SERIES_SAVED")

        if uid in temp.SERIES_WIZARD:
            del temp.SERIES_WIZARD[uid]

        await query.message.edit_text(
            f"✅ <b>Series saved successfully!</b>\n\n<b>{wiz['name']}</b> is now live.",
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    # ── Config Menu shortcuts ─────────────────────────────────────────────────
    if action == "menu":
        sub = parts[2] if len(parts) > 2 else ""
        if sub == "add_ep":
            wiz["add_mode"] = "episode"
            wiz["state"] = S_BATCH_LANG
            wiz["batch_langs"] = []
            wiz["batch_seasons"] = []
            wiz["batch_qualities"] = []
            logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz.get('series_id')}\naction=ADD_EPISODE")
            avail_langs = await _get_edit_available_langs(wiz)
            if avail_langs is not None and len(avail_langs) == 0:
                return await query.answer("⚠️ No files stored in database for this series yet.", show_alert=True)
            await query.message.edit_text(
                f"➕ <b>Add Episode</b> — <b>{wiz['name']}</b>\n\nSelect <b>language</b>:",
                reply_markup=_lang_keyboard(wiz["batch_langs"], available_langs=avail_langs),
                parse_mode=enums.ParseMode.HTML,
            )
        elif sub == "batch":
            wiz["add_mode"] = "batch"
            wiz["state"] = S_BATCH_LANG
            wiz["batch_langs"] = []
            wiz["batch_seasons"] = []
            wiz["batch_qualities"] = []
            logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz.get('series_id')}\naction=ADD_FILES")
            is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
            await query.message.edit_text(
                f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n\nSelect <b>language</b> for this batch:",
                reply_markup=_lang_keyboard(wiz["batch_langs"], show_custom=is_first_time, custom_langs=wiz.get("custom_langs", [])),
                parse_mode=enums.ParseMode.HTML,
            )
        return await query.answer()

    # ── Custom Language Callbacks ─────────────────────────────────────────────
    if action == "custom_lang":
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        if not is_first_time:
            return await query.answer("⚠️ Custom language is only available during new series creation.", show_alert=True)
        wiz["prev_lang_state"] = wiz.get("state", S_BATCH_LANG)
        wiz["state"] = S_CUSTOM_LANG_WAIT
        await query.message.reply_text(
            "🌐 <b>Send custom language name:</b>\n\n"
            f"Hey {query.from_user.mention}, please enter the custom language (e.g. <code>Korean</code>, <code>Japanese</code>, <code>Spanish</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    if action == "conf_custom_lang":
        val = wiz.get("pending_custom_lang")
        if val:
            if "custom_langs" not in wiz:
                wiz["custom_langs"] = []
            if val not in wiz["custom_langs"]:
                wiz["custom_langs"].append(val)
            target_list = wiz["batch_langs"] if wiz.get("state") in [S_BATCH_LANG, S_CUSTOM_LANG_CONF] or wiz.get("prev_lang_state") == S_BATCH_LANG else wiz["languages"]
            target_list[:] = [val]
            wiz["pending_custom_lang"] = None
        wiz["state"] = wiz.get("prev_lang_state", S_BATCH_LANG)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        await query.message.edit_text(
            f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n\nSelect <b>language</b> for this batch:",
            reply_markup=_lang_keyboard(
                wiz["batch_langs"] if wiz.get("state") == S_BATCH_LANG else wiz["languages"],
                show_custom=is_first_time,
                custom_langs=wiz.get("custom_langs", [])
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("✅ Custom language confirmed!")

    if action == "cancel_custom_lang":
        wiz["pending_custom_lang"] = None
        wiz["state"] = wiz.get("prev_lang_state", S_BATCH_LANG)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        await query.message.edit_text(
            f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n\nSelect <b>language</b> for this batch:",
            reply_markup=_lang_keyboard(
                wiz["batch_langs"] if wiz.get("state") == S_BATCH_LANG else wiz["languages"],
                show_custom=is_first_time,
                custom_langs=wiz.get("custom_langs", [])
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("Cancelled custom language.")

    # ── Custom Quality Callbacks ──────────────────────────────────────────────
    if action == "custom_qual":
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        if not is_first_time:
            return await query.answer("⚠️ Custom quality is only available during new series creation.", show_alert=True)
        wiz["prev_qual_state"] = wiz.get("state", S_BATCH_QUAL)
        wiz["state"] = S_CUSTOM_QUAL_WAIT
        await query.message.reply_text(
            "🎞 <b>Send custom quality:</b>\n\n"
            f"Hey {query.from_user.mention}, please enter the custom quality (e.g. <code>4K HDR</code>, <code>1080p HEVC</code>, <code>REMUX</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer()

    if action == "conf_custom_qual":
        val = wiz.get("pending_custom_qual")
        if val:
            if "custom_quals" not in wiz:
                wiz["custom_quals"] = []
            if val not in wiz["custom_quals"]:
                wiz["custom_quals"].append(val)
            target_list = wiz["batch_qualities"] if wiz.get("state") in [S_BATCH_QUAL, S_CUSTOM_QUAL_CONF] or wiz.get("prev_qual_state") == S_BATCH_QUAL else wiz["qualities"]
            target_list[:] = [val]
            wiz["pending_custom_qual"] = None
        wiz["state"] = wiz.get("prev_qual_state", S_BATCH_QUAL)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        used_qualities = await _get_used_qualities(wiz)
        seasons_str = ', '.join(f"S{s}" if s > 0 else "Direct Episodes" for s in sorted(wiz.get('batch_seasons', []))) if wiz.get('batch_seasons') else 'None'
        await query.message.edit_text(
            f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n"
            f"🌐 {', '.join(wiz.get('batch_langs', []))} · 📁 Season: <b>{seasons_str}</b>\n\n"
            "Select <b>quality</b>:\n"
            "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>",
            reply_markup=_quality_keyboard(
                wiz.get("batch_qualities", []),
                already_saved=used_qualities,
                show_custom=is_first_time,
                custom_quals=wiz.get("custom_quals", [])
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("✅ Custom quality confirmed!")

    if action == "cancel_custom_qual":
        wiz["pending_custom_qual"] = None
        wiz["state"] = wiz.get("prev_qual_state", S_BATCH_QUAL)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        used_qualities = await _get_used_qualities(wiz)
        seasons_str = ', '.join(f"S{s}" if s > 0 else "Direct Episodes" for s in sorted(wiz.get('batch_seasons', []))) if wiz.get('batch_seasons') else 'None'
        await query.message.edit_text(
            f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n"
            f"🌐 {', '.join(wiz.get('batch_langs', []))} · 📁 Season: <b>{seasons_str}</b>\n\n"
            "Select <b>quality</b>:\n"
            "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>",
            reply_markup=_quality_keyboard(
                wiz.get("batch_qualities", []),
                already_saved=used_qualities,
                show_custom=is_first_time,
                custom_quals=wiz.get("custom_quals", [])
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("Cancelled custom quality.")

    # ── Language toggle ───────────────────────────────────────────────────────
    if action == "lang":
        val = "#".join(parts[2:])
        target_list = wiz["batch_langs"] if wiz["state"] == S_BATCH_LANG else wiz["languages"]
        avail_langs = await _get_edit_available_langs(wiz)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        if val == "submit":
            if len(target_list) == 0:
                return await query.answer("⚠️ Please select one language.", show_alert=True)
            if len(target_list) > 1:
                target_list[:] = [target_list[-1]]
            if wiz["state"] == S_BATCH_LANG:
                wiz["languages"] = list(set(wiz.get("languages", []) + target_list))
                wiz["state"] = S_BATCH_SEASON
                avail_seasons = await _get_edit_available_seasons(wiz)
                if avail_seasons is not None and len(avail_seasons) == 0:
                    return await query.answer("⚠️ No seasons with files found for this language.", show_alert=True)
                show_skip = _should_show_skip_season(wiz) if avail_seasons is None else False
                heading = "➕ <b>Add Episode</b>" if wiz.get("add_mode") == "episode" else "📁 <b>Add Files</b>"
                await query.message.edit_text(
                    f"{heading} — <b>{wiz['name']}</b>\n🌐 Language: <b>{', '.join(target_list)}</b>\n\nSelect <b>season</b>:",
                    reply_markup=_season_keyboard(MAX_SEASONS, wiz.get("batch_seasons", []), show_skip=show_skip, available_seasons=avail_seasons),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                if wiz.get("series_id"):
                    await update_series(wiz["series_id"], {"languages": wiz["languages"]})
                    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=UPDATE_SUCCESS")
                await query.message.edit_text(
                    f"✅ <b>Language saved:</b>\n" + "\n".join(f"• {l}" for l in wiz["languages"]) +
                    "\n\nNow configure seasons, quality, or add batch files.",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        elif val == "back":
            await query.message.edit_text(
                _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
                reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            lang = val
            target_list[:] = [lang]
            try:
                await query.message.edit_reply_markup(_lang_keyboard(
                    target_list,
                    available_langs=avail_langs,
                    show_custom=is_first_time,
                    custom_langs=wiz.get("custom_langs", [])
                ))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Season toggle ─────────────────────────────────────────────────────────
    if action == "season":
        val = parts[2] if len(parts) > 2 else ""
        target_list = wiz["batch_seasons"] if wiz["state"] == S_BATCH_SEASON else wiz["seasons"]
        avail_seasons = await _get_edit_available_seasons(wiz)
        show_skip = _should_show_skip_season(wiz) if avail_seasons is None else False
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        if val == "submit":
            if len(target_list) == 0:
                return await query.answer("⚠️ Please select one season.", show_alert=True)
            if len(target_list) > 1:
                target_list[:] = [target_list[-1]]
            if wiz["state"] == S_BATCH_SEASON:
                wiz["batch_seasons"] = list(target_list)
                wiz["seasons"] = list(set(wiz.get("seasons", []) + target_list))
                wiz["state"] = S_BATCH_QUAL
                avail_quals = await _get_edit_available_qualities(wiz)
                if avail_quals is not None and len(avail_quals) == 0:
                    return await query.answer("⚠️ No qualities with files found for this language and season.", show_alert=True)
                used_qualities = await _get_used_qualities(wiz) if avail_quals is None else []
                seasons_str = ', '.join(f"S{s}" if s > 0 else "Direct Episodes" for s in sorted(target_list))
                heading = "➕ <b>Add Episode</b>" if wiz.get("add_mode") == "episode" else "📁 <b>Add Files</b>"
                await query.message.edit_text(
                    f"{heading} — <b>{wiz['name']}</b>\n"
                    f"🌐 {', '.join(wiz.get('batch_langs', []))} · 📁 Season: <b>{seasons_str}</b>\n\n"
                    "Select <b>quality</b>:\n"
                    + ("" if avail_quals is not None else "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>"),
                    reply_markup=_quality_keyboard(
                        wiz.get("batch_qualities", []),
                        already_saved=used_qualities,
                        available_qualities=avail_quals,
                        show_custom=is_first_time,
                        custom_quals=wiz.get("custom_quals", [])
                    ),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                if wiz.get("series_id"):
                    await update_series(wiz["series_id"], {"seasons": wiz["seasons"]})
                    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=UPDATE_SUCCESS")
                await query.message.edit_text(
                    "✅ <b>Seasons saved:</b>\n" + ("\n".join(f"• Season {s}" for s in sorted(wiz["seasons"])) if wiz["seasons"] else "None") +
                    "\n\nNow configure quality or add batch files.",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        elif val == "skip":
            if not _should_show_skip_season(wiz) or avail_seasons is not None:
                return await query.answer("⚠️ Season is already added for this language. Please select a season.", show_alert=True)
            if wiz["state"] == S_BATCH_SEASON:
                wiz["batch_seasons"] = [0]
                wiz["state"] = S_BATCH_QUAL
                used_qualities = await _get_used_qualities(wiz)
                await query.message.edit_text(
                    f"📁 <b>Add Files</b> — <b>{wiz['name']}</b>\n"
                    f"🌐 {', '.join(wiz.get('batch_langs', []))} · 📁 Seasons: <b>Direct Episodes (Skipped)</b>\n\n"
                    "Select <b>quality</b>:\n"
                    "<i>✅ = already saved to series  |  🟢 = selected for this batch</i>",
                    reply_markup=_quality_keyboard(
                        wiz.get("batch_qualities", []),
                        already_saved=used_qualities,
                        show_custom=is_first_time,
                        custom_quals=wiz.get("custom_quals", [])
                    ),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                if wiz.get("series_id"):
                    await update_series(wiz["series_id"], {"seasons": wiz["seasons"]})
                    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=UPDATE_SUCCESS")
                seasons_text = "\n".join(f"• Season {s}" for s in sorted(wiz["seasons"])) if wiz.get("seasons") else "None (Direct Episodes)"
                await query.message.edit_text(
                    f"✅ <b>Existing seasons retained:</b>\n{seasons_text}\n\nNow configure quality or add batch files.",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        elif val == "back":
            if wiz["state"] == S_BATCH_SEASON:
                wiz["state"] = S_BATCH_LANG
                avail_langs = await _get_edit_available_langs(wiz)
                heading = "➕ <b>Add Episode</b>" if wiz.get("add_mode") == "episode" else "📁 <b>Add Files</b>"
                await query.message.edit_text(
                    f"{heading} — <b>{wiz['name']}</b>\n\nSelect <b>language</b>:",
                    reply_markup=_lang_keyboard(
                        wiz.get("batch_langs", []),
                        available_langs=avail_langs,
                        show_custom=is_first_time,
                        custom_langs=wiz.get("custom_langs", [])
                    ),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        else:
            n = int(val)
            target_list[:] = [n]
            try:
                await query.message.edit_reply_markup(_season_keyboard(MAX_SEASONS, target_list, show_skip=show_skip, available_seasons=avail_seasons))
            except MessageNotModified:
                pass
        return await query.answer()

    # ── Quality toggle ────────────────────────────────────────────────────────
    if action == "quality":
        val = "#".join(parts[2:])
        target_list = wiz["batch_qualities"] if wiz["state"] == S_BATCH_QUAL else wiz["qualities"]
        avail_quals = await _get_edit_available_qualities(wiz)
        is_first_time = (wiz.get("mode") == "add" and not wiz.get("series_id"))
        if val == "submit":
            if len(target_list) == 0:
                return await query.answer("⚠️ Select one quality.", show_alert=True)
            if len(target_list) > 1:
                target_list[:] = [target_list[-1]]
            if wiz["state"] == S_BATCH_QUAL:
                wiz["qualities"] = list(set(wiz["qualities"] + target_list))
                wiz["state"] = S_BATCH_WAIT
                seasons_str = ', '.join(f"S{s}" if s > 0 else "Direct Episodes" for s in sorted(wiz.get('batch_seasons', []))) if wiz.get('batch_seasons') else 'None (Direct Episodes)'
                await query.message.edit_text(
                    f"📁 <b>Add Episode / File</b>\n\n"
                    f"📺 <b>Series:</b> {wiz['name']}\n"
                    f"🌐 <b>Language:</b> {', '.join(wiz.get('batch_langs', []))}\n"
                    f"📁 <b>Season:</b> {seasons_str}\n"
                    f"🎞 <b>Quality:</b> {', '.join(wiz.get('batch_qualities', []))}\n\n"
                    "Now send the channel link for the file(s):\n\n"
                    "• <b>Single File / Episode:</b>\n"
                    "<code>/slink https://t.me/c/123456/1001</code>\n\n"
                    "• <b>Batch Files / Episodes:</b>\n"
                    "<code>/sbatch https://t.me/c/123456/1001 https://t.me/c/123456/1010</code>",
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                if wiz.get("series_id"):
                    await update_series(wiz["series_id"], {"qualities": wiz["qualities"]})
                    logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={wiz['series_id']}\naction=UPDATE_SUCCESS")
                await query.message.edit_text(
                    "✅ <b>Quality options saved:</b>\n" + "\n".join(f"• {q}" for q in wiz["qualities"]) +
                    "\n\nNow add batch files or save the series.",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        elif val == "back":
            if wiz["state"] == S_BATCH_QUAL:
                wiz["state"] = S_BATCH_SEASON
                avail_seasons = await _get_edit_available_seasons(wiz)
                show_skip = _should_show_skip_season(wiz) if avail_seasons is None else False
                heading = "➕ <b>Add Episode</b>" if wiz.get("add_mode") == "episode" else "📁 <b>Add Files</b>"
                await query.message.edit_text(
                    f"{heading} — <b>{wiz['name']}</b>\n🌐 Language: <b>{', '.join(wiz.get('batch_langs', []))}</b>\n\nSelect <b>season</b>:",
                    reply_markup=_season_keyboard(MAX_SEASONS, wiz.get("batch_seasons", []), show_skip=show_skip, available_seasons=avail_seasons),
                    parse_mode=enums.ParseMode.HTML,
                )
            else:
                await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit or click Save:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
                    parse_mode=enums.ParseMode.HTML,
                )
        else:
            q = val
            target_list[:] = [q]
            if wiz["state"] == S_BATCH_QUAL:
                used_qualities = await _get_used_qualities(wiz) if avail_quals is None else []
            else:
                used_qualities = []
            try:
                await query.message.edit_reply_markup(_quality_keyboard(
                    target_list,
                    already_saved=used_qualities,
                    available_qualities=avail_quals,
                    show_custom=is_first_time,
                    custom_quals=wiz.get("custom_quals", [])
                ))
            except MessageNotModified:
                pass
        return await query.answer()

    if action == "quality_used":
        q = parts[2]
        return await query.answer(f"⚠️ {q} files are already added for the selected language and season.", show_alert=True)



    # ── Batch confirm ─────────────────────────────────────────────────────────
    if action == "bconfirm":
        choice = parts[2] if len(parts) > 2 else "no"
        if choice == "no":
            wiz["batch_data"] = None
            wiz["state"] = S_BATCH_LANG
            await query.message.edit_text(
                "Batch cancelled. Use the menu to try again.",
                reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
            )
            return await query.answer("Batch cancelled.")

        if choice == "yes":
            bd = wiz.get("batch_data")
            if not bd:
                return await query.answer("⚠️ No batch data found.", show_alert=True)

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

            langs_to_add = wiz.get("batch_langs") or wiz.get("languages") or ["Unknown"]
            seasons_to_add = wiz.get("batch_seasons") or wiz.get("seasons") or [0]
            if not seasons_to_add:
                seasons_to_add = [0]
            quals_to_add = wiz.get("batch_qualities") or wiz.get("qualities") or ["Default"]

            added_eps = []
            skipped_eps = []

            for lang in langs_to_add:
                for season in seasons_to_add:
                    for quality in quals_to_add:
                        for ep_num, ep_chat_id, ep_msg_id, ep_file_id, ep_file_name, ep_file_size in bd["files"]:
                            try:
                                is_dup = await check_episode_exists(series_id, lang, season, ep_num, quality)
                                if is_dup:
                                    skipped_eps.append(ep_num)
                                    logger.info(f"[SERIES SBATCH]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=DUPLICATE_SKIPPED")
                                else:
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
                                        "is_batch":   False,
                                        "total_episodes": 1
                                    })
                                    if status:
                                        added_eps.append(ep_num)
                                        logger.info(f"[SERIES SBATCH]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=ADDED")
                                    else:
                                        skipped_eps.append(ep_num)
                                        logger.info(f"[SERIES SBATCH]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=DUPLICATE_SKIPPED")
                            except Exception as e:
                                logger.warning(f"add_series_file error for batch episode {ep_num}: {e}")
                                skipped_eps.append(ep_num)

                        await save_batch({
                            "series_id": series_id,
                            "language": lang,
                            "season": season,
                            "quality": quality,
                            "chat_id": bd["chat_id"],
                            "first_message_id": bd["first_msg_id"],
                            "last_message_id": bd["last_msg_id"],
                            "total_files": len(added_eps),
                        })

            if len(added_eps) > 0:
                is_explicit = bool(wiz.get("batch_seasons") and wiz["batch_seasons"] != [0])
                mode = "explicit" if is_explicit else "skipped"
                if "season_modes" not in wiz:
                    wiz["season_modes"] = {}
                for l in langs_to_add:
                    wiz["season_modes"][l] = mode

            all_langs = list(set(wiz.get("languages", []) + langs_to_add))
            all_seasons = list(set(wiz.get("seasons", []) + seasons_to_add))
            all_quals = list(set(wiz.get("qualities", []) + quals_to_add))
            wiz["languages"] = all_langs
            wiz["seasons"] = all_seasons
            wiz["qualities"] = all_quals

            await update_series(series_id, {
                "languages": all_langs,
                "seasons": all_seasons,
                "qualities": all_quals,
                "season_modes": wiz.get("season_modes", {}),
            })

            wiz["batch_data"] = None
            wiz["state"] = S_DONE
            logger.info(f"[SERIES SBATCH]\nuser_id={uid}\nseries_id={series_id}\ntotal_added={len(added_eps)}\ntotal_skipped={len(skipped_eps)}\naction=COMPLETED")

            unique_added = sorted(list(set(added_eps)))
            unique_skipped = sorted(list(set(skipped_eps)))
            added_str = ", ".join(f"E{e:02d}" for e in unique_added) if unique_added else "None"
            skipped_str = ", ".join(f"E{e:02d}" for e in unique_skipped) if unique_skipped else "None"

            await query.message.edit_text(
                f"✅ <b>Batch processing completed!</b>\n\n"
                f"📺 <b>Series:</b> {wiz['name']}\n"
                f"🌐 <b>Languages:</b> {', '.join(langs_to_add)}\n"
                f"📁 <b>Seasons:</b> {', '.join(str(s) for s in seasons_to_add) if seasons_to_add and seasons_to_add != [0] else 'None'}\n"
                f"🎞 <b>Qualities:</b> {', '.join(quals_to_add)}\n\n"
                f"✅ <b>Added ({len(added_eps)}):</b> {added_str}\n"
                f"⚠️ <b>Already existed ({len(skipped_eps)}):</b> {skipped_str}\n\n"
                f"Existing episodes were not modified.\nAdd more batches or save the series.",
                reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
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
                "season_modes": wiz.get("season_modes", {}),
            })
            series_id = wiz["series_id"]
            logger.info(f"[SERIES EDIT]\nuser_id={uid}\nseries_id={series_id}\naction=UPDATE_SUCCESS")
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
                "season_modes": wiz.get("season_modes", {}),
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





@Client.on_callback_query(filters.regex(r"^send_fsall#"))
async def handle_send_fsall(client: Client, query: CallbackQuery):
    key = query.data.split("#")[1]
    
    # Ownership validation
    if query.message.reply_to_message and query.message.reply_to_message.from_user:
        req_user = query.message.reply_to_message.from_user.id
    else:
        from database.series_db import get_temp_request
        req = await get_temp_request(key)
        req_user = req.get("user") if req else 0
        
    if req_user == 0:
        return await query.answer("⚠️ Search context expired. Please search again.", show_alert=True)
        
    if query.from_user.id != req_user:
        return await query.answer("⚠️ This is not your button.", show_alert=True)
            
    from utils import temp
    start_url = f"https://t.me/{temp.U_NAME}?start=all_{key}"
    await query.answer(url=start_url)



# ──────────────────────────────────────────────────────────────────
# ─── /sbatch — BATCH FILE IMPORTER ────────────────────────────────
# ──────────────────────────────────────────────────────────────────



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



    # ── Collect files using chunked get_messages (same as /batch in genlink.py) ──
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
        f"📤 <b>First Message:</b> {msg1}\n"
        f"📥 <b>Last Message:</b> {msg2}\n"
        f"🔢 <b>Total Files:</b> {len(files_found)}\n"
        f"⚠️ <b>Skipped:</b> {errors}\n\n"
        f"<b>Episodes:</b>\n{ep_preview}\n\n"
        "Save this batch?",
        reply_markup=_batch_confirm_keyboard(),
        parse_mode=enums.ParseMode.HTML,
    )





# ──────────────────────────────────────────────────────────────────
# ─── /slink — SINGLE SERIES FILE IMPORTER ─────────────────────────
# ──────────────────────────────────────────────────────────────────



@Client.on_message(filters.command("slink") & filters.private, group=1)
async def cmd_slink(client: Client, message: Message):
    uid = message.from_user.id
    if not _is_admin(uid):
        return await message.reply_text("❌ You are not authorized to use this command.")

    if uid not in temp.SERIES_WIZARD:
        return await message.reply_text(
            "⚠️ Run <code>/seriesfil</code> or edit a series from <code>/viewseries</code> first "
            "before adding a single link.",
            parse_mode=enums.ParseMode.HTML,
        )

    wiz = temp.SERIES_WIZARD[uid]
    
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(
            "Usage: <code>/slink TELEGRAM_MESSAGE_LINK</code>\n\n"
            "Example:\n<code>/slink https://t.me/c/123456/1001</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    link = args[1].strip().strip('"').strip("'")
    chat_id, msg_id = _parse_tg_link(link)
    if not chat_id or not msg_id:
        return await message.reply_text(
            "❌ <b>Invalid Telegram link.</b>\n\n"
            "Accepted formats:\n"
            "• <code>https://t.me/channelname/12345</code>\n"
            "• <code>https://t.me/c/1234567890/12345</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    processing_msg = await message.reply_text("⏳ Processing single file link...")

    try:
        msg = await client.get_messages(chat_id, msg_id)
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ <b>Cannot read message from channel.</b>\n\n"
            f"Make sure the bot is an <b>admin</b> in the source channel.\n\n"
            f"<code>{e}</code>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    if not msg or not msg.media:
        return await processing_msg.edit_text("❌ Message does not contain any file/media.")

    file_type = msg.media
    media = getattr(msg, file_type.value, None)
    if not media:
        return await processing_msg.edit_text("❌ Could not extract media from message.")

    file_id = getattr(media, "file_id", "")
    file_name = getattr(media, "file_name", None) or f"file_{msg.id}"
    file_size = getattr(media, "file_size", 0) or 0
    ep_num = (
        _extract_episode_number(file_name)
        or (msg.caption and _extract_episode_number(msg.caption))
        or (msg.text and _extract_episode_number(msg.text))
        or 1
    )

    # Ensure series is saved or updated
    if not wiz.get("series_id"):
        series_id = await create_series({
            "name": wiz["name"],
            "year": wiz.get("year", ""),
            "genre": wiz.get("genre", ""),
            "rating": wiz.get("rating", ""),
            "description": wiz.get("description", ""),
            "poster": wiz.get("poster", ""),
            "languages": wiz.get("languages", []),
            "seasons": wiz.get("seasons", []),
            "qualities": wiz.get("qualities", []),
            "created_by": uid,
        })
        wiz["series_id"] = series_id
        _register_short_id(series_id)
    else:
        series_id = wiz["series_id"]

    langs = wiz.get("batch_langs") or wiz.get("languages") or ["Unknown"]
    seasons = wiz.get("batch_seasons") or wiz.get("seasons") or [0]
    qualities = wiz.get("batch_qualities") or wiz.get("qualities") or ["Default"]

    inserted = 0
    duplicates = 0
    for lang in langs:
        for season in seasons:
            for quality in qualities:
                try:
                    logger.info(f"[SERIES SLINK]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=ADD_SINGLE")
                    is_dup = await check_episode_exists(series_id, lang, season, ep_num, quality)
                    if is_dup:
                        duplicates += 1
                        logger.info(f"[SERIES SLINK]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=DUPLICATE_SKIPPED")
                    else:
                        status, reason = await add_series_file({
                            "series_id": series_id,
                            "language": lang,
                            "season": season,
                            "episode": ep_num,
                            "quality": quality,
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "file_id": file_id,
                            "file_name": file_name,
                            "file_size": file_size,
                            "is_batch": False,
                            "total_episodes": 1
                        })
                        if status:
                            inserted += 1
                            logger.info(f"[SERIES SLINK]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=ADDED")
                        else:
                            duplicates += 1
                            logger.info(f"[SERIES SLINK]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=DUPLICATE_SKIPPED")
                except Exception as ex:
                    logger.warning(f"add_series_file error for slink: {ex}")
                    duplicates += 1
                    logger.info(f"[SERIES SLINK]\nuser_id={uid}\nseries_id={series_id}\nseason={season}\nepisode={ep_num}\nlanguage={lang}\nquality={quality}\naction=DUPLICATE_SKIPPED")

    if inserted > 0:
        is_explicit = bool(seasons and seasons != [0])
        mode = "explicit" if is_explicit else "skipped"
        if "season_modes" not in wiz:
            wiz["season_modes"] = {}
        for l in langs:
            wiz["season_modes"][l] = mode

    all_langs = list(set(wiz.get("languages", []) + langs))
    all_seasons = list(set(wiz.get("seasons", []) + seasons))
    all_quals = list(set(wiz.get("qualities", []) + qualities))
    wiz["languages"] = all_langs
    wiz["seasons"] = all_seasons
    wiz["qualities"] = all_quals

    await update_series(series_id, {
        "languages": all_langs,
        "seasons": all_seasons,
        "qualities": all_quals,
        "season_modes": wiz.get("season_modes", {}),
    })

    wiz["state"] = S_DONE

    if inserted > 0:
        feedback_title = f"✅ <b>Episode {ep_num:02d} added successfully. Existing episodes were not modified.</b>"
    else:
        feedback_title = f"⚠️ <b>Episode {ep_num:02d} already exists.</b>"

    await processing_msg.edit_text(
        f"{feedback_title}\n\n"
        f"📺 <b>Series:</b> {wiz['name']}\n"
        f"📁 <b>File:</b> {file_name}\n"
        f"🌐 <b>Language(s):</b> {', '.join(langs)}\n"
        f"📁 <b>Season(s):</b> {', '.join(str(s) for s in seasons) if seasons != [0] else 'None'}\n"
        f"🎞 <b>Quality(s):</b> {', '.join(qualities)}\n\n"
        f"✅ Added: {inserted} | ⚠️ Already existed: {duplicates}",
        reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", False)),
        parse_mode=enums.ParseMode.HTML,
    )

# ──────────────────────────────────────────────────────────────────
# ─── USER SEARCH & NAVIGATION LOGIC ──────────────────────────────
# ──────────────────────────────────────────────────────────────────



def schedule_series_auto_delete(message, delay: int = 300):
    from info import AUTO_DELETE
    if not AUTO_DELETE or not message:
        return
    from utils import temp
    if not hasattr(temp, "SERIES_SCHEDULED_DELETES"):
        temp.SERIES_SCHEDULED_DELETES = set()

    chat_id = getattr(getattr(message, "chat", None), "id", None)
    msg_id = getattr(message, "id", None)
    if not chat_id or not msg_id:
        return
    msg_key = (chat_id, msg_id)
    if msg_key in temp.SERIES_SCHEDULED_DELETES:
        return
    temp.SERIES_SCHEDULED_DELETES.add(msg_key)

    async def _auto_delete():
        try:
            import asyncio
            await asyncio.sleep(delay)
            await message.delete()
        except Exception:
            pass
        finally:
            temp.SERIES_SCHEDULED_DELETES.discard(msg_key)

    import asyncio
    asyncio.create_task(_auto_delete())


async def _send_or_edit(message_or_query, text, reply_markup, poster=None):
    if isinstance(message_or_query, Message):
        if poster:
            m = await message_or_query.reply_photo(photo=poster, caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            m = await message_or_query.reply_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        if m:
            schedule_series_auto_delete(m, delay=300)
        return m
    else:
        try:
            if message_or_query.message.photo:
                if poster and message_or_query.message.photo.file_id != poster:
                    from pyrogram.types import InputMediaPhoto
                    m = await message_or_query.message.edit_media(
                        media=InputMediaPhoto(poster, caption=text),
                        reply_markup=reply_markup
                    )
                else:
                    m = await message_or_query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                m = await message_or_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            if m:
                schedule_series_auto_delete(m, delay=300)
            return m
        except MessageNotModified:
            return message_or_query.message





async def _resolve_nav_step(user_id: int, full_id: str, sid: str, series: dict, lang=None, season=None, qual=None, is_private: bool = False, remaining_seconds: str = None):
    """
    Returns (text, reply_markup)
    """
    card = _series_card(series, remaining_seconds)
    
    if lang is None:
        langs = await list_series_languages(full_id)
        if not langs: langs = series.get("languages", [])
        if not langs: return "⚠️ No files yet.", None
        return card + "\n\n🌐  <b>Select Language:</b>", _user_lang_keyboard(sid, langs)
        
    if season is None:
        seasons = await list_series_seasons(full_id, lang)
        if not seasons: seasons = sorted(series.get("seasons", []))
        if not seasons: return "⚠️ No seasons found.", None
        if seasons == [0]:
            season = 0
        else:
            return card + f"\n\n🌐  <b>{lang}</b>\n📁  <b>Select Season:</b>", _user_season_keyboard(sid, lang, seasons)
        
    if qual is None:
        quals = await list_season_qualities(full_id, lang, season)
        if not quals: return "⚠️ No qualities found.", None
        
        season_str = f"Season {season}" if season > 0 else "Direct Episodes"
        rating = series.get("rating", "N/A")
        kb = await _user_quality_keyboard(user_id, full_id, sid, lang, season, quals, rating, is_private=is_private)
        return card + f"\n\n🌐  <b>{lang}</b>\n📁  <b>{season_str}</b>\n🎞️ <b>Select Quality:</b>", kb
        
    return "⚠️ Invalid step.", None





def _user_suggestions_keyboard(matches: list[dict], user_id: int) -> InlineKeyboardMarkup:
    rows = []
    import uuid, logging
    log = logging.getLogger(__name__)
    from utils import temp
    from database.series_db import save_temp_request
    if not hasattr(temp, "SERIES_STATE"):
        temp.SERIES_STATE = {}
    for m in matches:
        sid = str(m["_id"])
        key = str(uuid.uuid4())[:8]
        nav_state = {
            "user": user_id,
            "user_id": user_id,
            "sid": sid,
            "series_id": sid,
            "full_id": sid,
            "path": "SUGGESTION",
            "is_direct": False
        }
        temp.SERIES_STATE[key] = nav_state
        try:
            import asyncio
            asyncio.create_task(save_temp_request(key, nav_state))
        except Exception:
            pass
        log.info(
            f"[SERIES SUGGESTION STATE]\n"
            f"user_id={user_id}\n"
            f"series_id={sid}\n"
            f"sid={sid}\n"
            f"full_id={sid}\n"
            f"path=SUGGESTION\n"
            f"is_direct=False"
        )
        rows.append([InlineKeyboardButton(m["name"], callback_data=f"sr#{key}")])
    return InlineKeyboardMarkup(rows)





async def process_series_search(client: Client, message: Message, txt: str, reply_msg: Message = None):
    import logging, time
    logger = logging.getLogger(__name__)
    start_time = time.time()

    user_id = message.from_user.id if (hasattr(message, "from_user") and message.from_user) else (message.sender_chat.id if getattr(message, "sender_chat", None) else 0)

    matches = await search_series(txt)
    candidate_count = len(matches) if matches else 0
    
    if not matches:
        logger.info(
            f"[SERIES SEARCH]\n"
            f"query={txt}\n"
            f"candidate_count={candidate_count}\n"
            f"matched_series=0\n"
            f"decision=MOVIE_FILTER"
        )
        return False

    seen = set()
    unique_matches = []
    for m in matches:
        name = m.get("name", "").strip()
        name_lower = name.lower()
        if name_lower not in seen:
            seen.add(name_lower)
            unique_matches.append(m)

    matched_names = [m.get("name", "") for m in unique_matches]
    decision = "SERIES_DIRECT" if len(unique_matches) == 1 else "SERIES_SUGGESTIONS"

    logger.info(
        f"[SERIES SEARCH]\n"
        f"query={txt}\n"
        f"candidate_count={candidate_count}\n"
        f"matched_series={len(unique_matches)}\n"
        f"series_names={matched_names}\n"
        f"decision={decision}"
    )

    remaining_seconds = "{:.2f}".format(time.time() - start_time)

    if len(unique_matches) == 1:
        logger.info(
            f"[SEARCH ROUTING]\n"
            f"stage=SERIES\n"
            f"decision=SERIES_DIRECT"
        )
        series = unique_matches[0]
        series_id = str(series["_id"])
        _register_short_id(series_id)
        
        import uuid
        from utils import temp
        from database.series_db import save_temp_request
        if not hasattr(temp, "SERIES_STATE"):
            temp.SERIES_STATE = {}
        key = str(uuid.uuid4())[:8]
        nav_state = {
            "user": user_id,
            "user_id": user_id,
            "sid": series_id,
            "series_id": series_id,
            "full_id": series_id,
            "path": "DIRECT",
            "is_direct": True
        }
        temp.SERIES_STATE[key] = nav_state
        try:
            await save_temp_request(key, nav_state)
        except Exception:
            pass

        logger.info(
            f"[SERIES DIRECT SEARCH STATE]\n"
            f"user_id={user_id}\n"
            f"series_id={series_id}\n"
            f"sid={series_id}\n"
            f"full_id={series_id}\n"
            f"path=DIRECT\n"
            f"is_direct=True"
        )
        
        sid = series_id

        is_private = (message.chat.type == enums.ChatType.PRIVATE)
        text, rm = await _resolve_nav_step(user_id, series_id, key, series, is_private=is_private, remaining_seconds=remaining_seconds)
        poster = series.get("poster")
    else:
        logger.info(
            f"[SEARCH ROUTING]\n"
            f"stage=SERIES\n"
            f"decision=SERIES_SUGGESTIONS"
        )
        from database.series_db import get_series_thumbnail
        poster = await get_series_thumbnail()
        
        for m in unique_matches:
            _register_short_id(str(m["_id"]))
            
        text = f"🍿 <b>Choose the series/movie you want to view:</b>\n\n⚡ <b>Result Shown in:</b> {remaining_seconds} <i>seconds</i>"
        rm = _user_suggestions_keyboard(unique_matches, user_id)

    if rm:
        if reply_msg:
            try:
                await reply_msg.delete()
            except:
                pass
        await _send_or_edit(message, text, rm, poster=poster)
    return True



# series_search_handler removed to prevent competing with auto_filter





async def resolve_exact_series_files(
    client: Client,
    full_id: str,
    lang: str,
    season: int,
    qual: str,
    ep: int | None = None,
    rating: str = "N/A",
    req_key: str = "",
    path: str = "DIRECT"
) -> list[dict]:
    """
    Resolve and return the exact list of file records corresponding to the specific Quality/Episode request.
    Only files that are ACTUALLY SAVED in the Series database (series_files collection) are accepted.
    Unsaved files from raw batch JSON are strictly rejected.
    """
    from database.series_db import list_quality_episodes, get_series_files, find_saved_series_file, _sid_query
    import json, os, logging
    log = logging.getLogger(__name__)

    full_id = await _normalize_series_id(full_id)
    files = []

    log.info(
        f"[SERIES DB REQUEST]\n"
        f"request_key={req_key}\n"
        f"source={path}\n"
        f"full_id={full_id}\n"
        f"language={lang}\n"
        f"season={season}\n"
        f"quality={qual}\n"
        f"episode={ep}"
    )

    async def _validate_and_get_batch_file(bf, fallback_ep):
        bf_file_id = bf.get("file_id")
        bf_name = bf.get("file_name", "")

        def _get_batch_ep(item, fb):
            if "episode" in item and str(item["episode"]).isdigit() and int(item["episode"]) > 0:
                return int(item["episode"])
            if "episode_index" in item and str(item["episode_index"]).isdigit() and int(item["episode_index"]) > 0:
                return int(item["episode_index"])
            extracted = _extract_episode_number(item.get("file_name", ""))
            if extracted is not None and extracted > 0:
                return extracted
            return fb

        bf_ep = _get_batch_ep(bf, fallback_ep)

        if not bf_file_id:
            log.warning(
                f"[SERIES BATCH VALIDATION]\n"
                f"request_key={req_key}\n"
                f"file_id=None\n"
                f"file_name={bf_name}\n"
                f"series_id={full_id}\n"
                f"language={lang}\n"
                f"season={season}\n"
                f"quality={qual}\n"
                f"episode={bf_ep}\n"
                f"saved_in_database=False"
            )
            log.warning(
                f"[SERIES DELIVERY REJECTED]\n"
                f"reason=UNSAVED_BATCH_FILE\n"
                f"file_id=None\n"
                f"file_name={bf_name}"
            )
            return None

        # Authoritative validation against series_files collection in database
        saved_record = await find_saved_series_file(
            series_id=full_id,
            language=lang,
            season=season,
            quality=qual,
            file_id=bf_file_id,
            episode=bf_ep
        )

        if not saved_record:
            log.warning(
                f"[SERIES BATCH VALIDATION]\n"
                f"request_key={req_key}\n"
                f"file_id={bf_file_id}\n"
                f"file_name={bf_name}\n"
                f"series_id={full_id}\n"
                f"language={lang}\n"
                f"season={season}\n"
                f"quality={qual}\n"
                f"episode={bf_ep}\n"
                f"saved_in_database=False"
            )
            log.warning(
                f"[SERIES DELIVERY REJECTED]\n"
                f"reason=UNSAVED_BATCH_FILE\n"
                f"file_id={bf_file_id}\n"
                f"file_name={bf_name}"
            )
            return None

        saved_ep = int(saved_record.get("episode", bf_ep))
        log.info(
            f"[SERIES BATCH VALIDATION]\n"
            f"request_key={req_key}\n"
            f"file_id={bf_file_id}\n"
            f"file_name={bf_name}\n"
            f"series_id={full_id}\n"
            f"language={lang}\n"
            f"season={season}\n"
            f"quality={qual}\n"
            f"episode={saved_ep}\n"
            f"saved_in_database=True"
        )
        log.info(
            f"[SERIES DELIVERY ACCEPTED]\n"
            f"source=SAVED_SERIES_DATABASE\n"
            f"file_id={bf_file_id}\n"
            f"episode={saved_ep}"
        )

        doc = dict(saved_record)
        doc["is_series"] = True
        doc["series_rating"] = rating
        doc["episode"] = saved_ep
        doc["episode_index"] = saved_ep
        return doc

    if ep is not None and (isinstance(ep, int) or (isinstance(ep, str) and str(ep).isdigit())) and int(ep) > 0:
        ep_num = int(ep)
        raw_ep_files = await get_series_files(full_id, lang, season, ep_num, qual)
        for f in raw_ep_files:
            if f.get("is_batch"):
                try:
                    file_path = await client.download_media(f["file_id"])
                    with open(file_path, "r", encoding="utf-8") as json_file:
                        batch_files = json.loads(json_file.read())
                    os.remove(file_path)

                    for b_idx, bf in enumerate(batch_files, start=1):
                        validated_doc = await _validate_and_get_batch_file(bf, b_idx)
                        if validated_doc and validated_doc.get("episode") == ep_num:
                            validated_doc["total_episodes"] = 1
                            files.append(validated_doc)
                except Exception as e:
                    log.error(f"Failed to fetch JSON batch: {e}")
            else:
                f_sid = str(f.get("series_id", ""))
                f_lang = str(f.get("language", ""))
                f_season = int(f.get("season", 0))
                f_qual = str(f.get("quality", ""))
                if await _match_series_id(f_sid, full_id) and f_lang == str(lang) and f_season == int(season) and f_qual == str(qual):
                    doc = dict(f)
                    doc["is_series"] = True
                    doc["series_rating"] = rating
                    doc["episode"] = ep_num
                    doc["episode_index"] = ep_num
                    doc["total_episodes"] = 1
                    log.info(f"[SERIES DELIVERY ACCEPTED]\nsource=SAVED_SERIES_DATABASE\nfile_id={doc.get('file_id')}\nepisode={ep_num}")
                    files.append(doc)
    else:
        episodes = await list_quality_episodes(full_id, lang, season, qual)
        log.info(
            f"[SERIES DB EPISODES]\n"
            f"request_key={req_key}\n"
            f"full_id={full_id}\n"
            f"language={lang}\n"
            f"season={season}\n"
            f"quality={qual}\n"
            f"episodes={episodes}"
        )
        if not episodes:
            log.warning(
                f"[SERIES DB MISMATCH DEBUG]\n"
                f"requested:\n"
                f"full_id={full_id}\n"
                f"language={lang}\n"
                f"season={season}\n"
                f"quality={qual}"
            )
            try:
                from database.series_db import sfiles_col
                candidates = sfiles_col.find({"series_id": _sid_query(full_id)})
                async for c in candidates:
                    log.info(
                        f"[SERIES DB CANDIDATE RECORD]\n"
                        f"series_id={c.get('series_id')}\n"
                        f"language={c.get('language')}\n"
                        f"season={c.get('season')}\n"
                        f"quality={c.get('quality')}\n"
                        f"episode={c.get('episode')}\n"
                        f"file_id={c.get('file_id')}"
                    )
            except Exception:
                pass

        sorted_episodes = sorted([
            int(e) for e in episodes 
            if (isinstance(e, int) or (isinstance(e, str) and str(e).isdigit())) and int(e) > 0
        ])
        other_eps = [e for e in episodes if e not in sorted_episodes]
        all_eps = sorted_episodes + other_eps
        total_eps = len(all_eps)

        if all_eps:
            all_ep_files = await asyncio.gather(*[
                get_series_files(full_id, lang, season, ep_val, qual)
                for ep_val in all_eps
            ])

            for i, (ep_val, ep_files) in enumerate(zip(all_eps, all_ep_files), start=1):
                log.info(
                    f"[SERIES EPISODE TRACE]\n"
                    f"episode={ep_val}\n"
                    f"file_count={len(ep_files)}"
                )
                for f in ep_files:
                    if f.get("is_batch"):
                        try:
                            file_path = await client.download_media(f["file_id"])
                            with open(file_path, "r", encoding="utf-8") as json_file:
                                batch_files = json.loads(json_file.read())
                            os.remove(file_path)

                            for b_idx, bf in enumerate(batch_files, start=1):
                                validated_doc = await _validate_and_get_batch_file(bf, b_idx)
                                if validated_doc:
                                    validated_doc["total_episodes"] = total_eps
                                    files.append(validated_doc)
                        except Exception as e:
                            log.error(f"Failed to fetch JSON batch: {e}")
                    else:
                        f_sid = str(f.get("series_id", ""))
                        f_lang = str(f.get("language", ""))
                        f_season = int(f.get("season", 0))
                        f_qual = str(f.get("quality", ""))
                        if await _match_series_id(f_sid, full_id) and f_lang == str(lang) and f_season == int(season) and f_qual == str(qual):
                            doc = dict(f)
                            doc["is_series"] = True
                            doc["series_rating"] = rating
                            doc["episode"] = ep_val if (isinstance(ep_val, int) and ep_val > 0) else i
                            doc["episode_index"] = ep_val if (isinstance(ep_val, int) and ep_val > 0) else i
                            doc["total_episodes"] = total_eps
                            log.info(f"[SERIES DELIVERY ACCEPTED]\nsource=SAVED_SERIES_DATABASE\nfile_id={doc.get('file_id')}\nepisode={doc['episode']}")
                            files.append(doc)

    # If episode-loop produced no files, attempt direct query for all files in this season & quality
    if not files and (ep is None or (isinstance(ep, int) and ep <= 0)):
        try:
            from database.series_db import sfiles_col
            direct_cursor = sfiles_col.find({
                "series_id": _sid_query(full_id),
                "language": lang,
                "season": {"$in": [int(season), str(season)]},
                "quality": qual
            })
            direct_files = [doc async for doc in direct_cursor]
            for i, f in enumerate(direct_files, start=1):
                if f.get("is_batch"):
                    try:
                        file_path = await client.download_media(f["file_id"])
                        with open(file_path, "r", encoding="utf-8") as json_file:
                            batch_files = json.loads(json_file.read())
                        os.remove(file_path)

                        for b_idx, bf in enumerate(batch_files, start=1):
                            validated_doc = await _validate_and_get_batch_file(bf, b_idx)
                            if validated_doc:
                                validated_doc["total_episodes"] = len(direct_files)
                                files.append(validated_doc)
                    except Exception as e:
                        log.error(f"Failed to fetch JSON batch: {e}")
                else:
                    doc = dict(f)
                    doc["is_series"] = True
                    doc["series_rating"] = rating
                    doc["episode"] = int(f.get("episode", i)) if str(f.get("episode", "")).isdigit() else i
                    doc["episode_index"] = doc["episode"]
                    doc["total_episodes"] = len(direct_files)
                    log.info(f"[SERIES DELIVERY ACCEPTED]\nsource=SAVED_SERIES_DATABASE_DIRECT\nfile_id={doc.get('file_id')}\nepisode={doc['episode']}")
                    files.append(doc)
        except Exception as e:
            log.error(f"Fallback direct file query failed: {e}")

    # Deduplicate exact duplicate file IDs
    seen = set()
    unique_files = []
    for f in files:
        fid = f.get("file_id")
        if fid:
            if fid in seen:
                continue
            seen.add(fid)
        unique_files.append(f)

    # Sort numerically by episode
    def _sort_key(item):
        e = item.get("episode")
        if isinstance(e, int) and e > 0:
            return (0, e)
        if isinstance(e, str) and e.isdigit() and int(e) > 0:
            return (0, int(e))
        return (1, 0)

    unique_files.sort(key=_sort_key)

    log.info(
        f"[SERIES RESOLVER RESULT]\n"
        f"request_key={req_key}\n"
        f"path={path}\n"
        f"full_id={full_id}\n"
        f"language={lang}\n"
        f"season={season}\n"
        f"quality={qual}\n"
        f"episode={ep}\n"
        f"files_count={len(unique_files)}"
    )

    if not unique_files:
        log.warning(
            f"[SERIES ZERO FILE DEBUG]\n"
            f"request_key={req_key}\n"
            f"source={path}\n"
            f"sid={req_key}\n"
            f"full_id={full_id}\n"
            f"language={lang}\n"
            f"season={season}\n"
            f"quality={qual}\n"
            f"episode={ep}\n"
            f"available_episodes={episodes if 'episodes' in locals() else None}"
        )
        try:
            from database.series_db import sfiles_col
            candidates = sfiles_col.find({"language": lang, "season": int(season), "quality": qual})
            async for c in candidates:
                log.info(
                    f"[SERIES DB CANDIDATES]\n"
                    f"stored_series_id={c.get('series_id')}\n"
                    f"stored_language={c.get('language')}\n"
                    f"stored_season={c.get('season')}\n"
                    f"stored_episode={c.get('episode')}\n"
                    f"stored_quality={c.get('quality')}\n"
                    f"stored_file_id={c.get('file_id')}"
                )
        except Exception:
            pass

    return unique_files


async def deliver_series_request(client: Client, req_key: str, user_id: int, query: CallbackQuery = None, timing: dict = None) -> bool:
    """
    Single unified Series file delivery engine.
    Retrieves the exact request context for `req_key`, validates membership and ownership,
    verifies file attributes, and sends ONLY the exact files associated with that request.
    """
    from utils import temp
    import logging, time
    log = logging.getLogger(__name__)

    t0 = timing.get("start") if timing and "start" in timing else time.perf_counter()
    t_received = time.perf_counter()

    log.info(f"[SERIES DELIVERY]\naction=START\nrequest_key={req_key}")
    log.info(f"[SERIES DELIVERY]\nrequest_key={req_key}\naction=START")

    # 1. Retrieve request context from memory or DB
    req = getattr(temp, "SERIES_STATE", {}).get(req_key)
    if not req:
        req = getattr(temp, "GETALL", {}).get(req_key)
    if not req:
        from database.series_db import get_temp_request
        req = await get_temp_request(req_key)
        if req:
            temp.SERIES_STATE[req_key] = req
            temp.GETALL[req_key] = req

    t_loaded = time.perf_counter()

    if not req:
        log.warning(f"[SERIES DELIVERY] Request expired for key={req_key}")
        if query:
            await query.answer("⚠️ Request expired. Please search again.", show_alert=True)
        else:
            try:
                await client.send_message(user_id, "⚠️ Request expired. Please search the series again.")
            except Exception:
                pass
        return False

    # 2. Check ownership
    owner = req.get("user_id", req.get("user"))
    if owner and int(owner) != int(user_id):
        log.warning(f"[SERIES DELIVERY] Ownership mismatch for key={req_key}: owner={owner}, actual={user_id}")
        if query:
            await query.answer("⚠️ This is not your button.", show_alert=True)
        else:
            try:
                await client.send_message(user_id, "⚠️ This link is not for you!")
            except Exception:
                pass
        return False

    # 3. Check delivery status
    status = str(req.get("delivery_status", req.get("state", ""))).lower()
    if status == "completed":
        log.info(f"[SERIES DELIVERY] Already completed for key={req_key}")
        if query:
            await query.answer("✅ Files already sent.", show_alert=True)
        return False
    if status == "sending":
        log.info(f"[SERIES DELIVERY] Already sending for key={req_key}")
        if query:
            await query.answer("⏳ Files are already being sent.", show_alert=True)
        return False

    req["delivery_status"] = "sending"
    req["state"] = "SENDING"

    t_membership = time.perf_counter()

    query_ctx = req.get("query", {}) if isinstance(req.get("query"), dict) else {}
    full_id = query_ctx.get("full_id") or req.get("full_id") or req.get("series_id")
    if not full_id and req.get("sid"):
        full_id = await _get_full_id(req["sid"])
    lang = query_ctx.get("lang") or req.get("language")
    season = int(query_ctx.get("season") if query_ctx.get("season") is not None else req.get("season", 0))
    qual = query_ctx.get("qual") or req.get("quality")
    ep = req.get("episode")
    rating = query_ctx.get("rating") or req.get("rating", "N/A")
    path = req.get("path", "DIRECT" if req.get("is_direct") else "SUGGESTION")

    t_resolved = time.perf_counter()

    log.info(
        f"[SERIES DELIVERY REQUEST]\n"
        f"request_key={req_key}\n"
        f"path={path}\n"
        f"user_id={user_id}\n"
        f"series_id={req.get('series_id')}\n"
        f"full_id={full_id}\n"
        f"language={lang}\n"
        f"season={season}\n"
        f"quality={qual}\n"
        f"episode={ep}"
    )

    # 4. Get exact files stored in the request
    files = req.get("files")
    if not files:
        files = await resolve_exact_series_files(client, full_id, lang, season, qual, ep, rating, req_key=req_key, path=path)
        req["files"] = files

    t_files = time.perf_counter()

    req_file_ids = set(req.get("file_ids") or [f.get("file_id") for f in files if f.get("file_id")])

    # 5. Strict Verification & Logging
    verified_files = []
    for f in files:
        f_sid = str(f.get("series_id", ""))
        f_lang = str(f.get("language", ""))
        f_season = int(f.get("season", 0))
        f_qual = str(f.get("quality", ""))
        f_id = f.get("file_id")

        # Check matching context
        if not await _match_series_id(f_sid, full_id) or str(f_lang).strip().lower() != str(lang).strip().lower() or int(f_season) != int(season) or str(f_qual).strip().lower() != str(qual).strip().lower():
            log.warning(f"[SERIES DELIVERY REJECTED] reason=NOT_IN_REQUEST series_id={f_sid} season={f_season} lang={f_lang} qual={f_qual} file_id={f_id} file_name={f.get('file_name')}")
            continue

        # Check file is in exact requested set
        if req_file_ids and f_id not in req_file_ids:
            log.warning(f"[SERIES DELIVERY REJECTED] reason=NOT_IN_REQUEST file_id={f_id} file_name={f.get('file_name')}")
            continue

        log.info(
            f"[SERIES REQUEST FILE]\n"
            f"request_key={req_key}\n"
            f"file_id={f_id}\n"
            f"file_name={f.get('file_name')}\n"
            f"episode={f.get('episode')}\n"
            f"series_id={f_sid}\n"
            f"language={f_lang}\n"
            f"season={f_season}\n"
            f"quality={f_qual}\n"
            f"source=EXACT_REQUEST_FILE_ID"
        )
        verified_files.append(f)

    t_verified = time.perf_counter()

    log.info(
        f"[SERIES FINAL FILE CHECK]\n"
        f"request_key={req_key}\n"
        f"source={path}\n"
        f"full_id={full_id}\n"
        f"language={lang}\n"
        f"season={season}\n"
        f"quality={qual}\n"
        f"episode={ep}\n"
        f"resolver_count={len(files)}\n"
        f"verified_count={len(verified_files)}"
    )

    if not verified_files:
        req["delivery_status"] = "failed"
        req["state"] = "FAILED"
        log.warning(f"[SERIES DELIVERY] No verified files to send for key={req_key}")
        log.info(f"[SERIES DELIVERY]\naction=FILES_FOUND\ncount=0\nrequest_key={req_key}")
        if query:
            await query.answer("⚠️ No files found for this request.", show_alert=True)
        else:
            try:
                await client.send_message(user_id, "⚠️ No files found for this request.")
            except Exception:
                pass
        return False

    log.info(f"[SERIES DELIVERY]\naction=FILES_FOUND\ncount={len(verified_files)}\nrequest_key={req_key}")
    log.info(f"[SERIES DELIVERY]\nrequest_key={req_key}\nfiles_count={len(verified_files)}")

    # 6. Delete Join Request message if exists
    if query and query.message:
        is_join_msg = False
        if getattr(query, "data", "") and "checksub" in str(query.data):
            is_join_msg = True
        elif query.message.text and ("Channel Join" in query.message.text or "Join Request" in query.message.text or "Try Again" in str(getattr(query.message, "reply_markup", ""))):
            is_join_msg = True
        elif req.get("join_message_id") and getattr(query.message, "id", None) == req["join_message_id"]:
            is_join_msg = True
            
        if is_join_msg:
            try:
                await query.message.delete()
                log.info(f"[SERIES DELIVERY] Deleted Join Request message for key={req_key}")
            except Exception as e:
                log.warning(f"[SERIES DELIVERY] Failed to delete Join Request message: {e}")
    elif req.get("join_message_id"):
        try:
            await client.delete_messages(chat_id=user_id, message_ids=req["join_message_id"])
            log.info(f"[SERIES DELIVERY] Deleted join_message_id={req['join_message_id']} for key={req_key}")
        except Exception:
            pass

    if query:
        try:
            await query.answer()
        except Exception:
            pass

    # 7. Deliver files via send_series_files_to_user
    t_send_start = time.perf_counter()
    from plugins.commands import send_series_files_to_user
    log.info(f"[SERIES DELIVERY] Sending {len(verified_files)} verified files for key={req_key} to user_id={user_id}")
    await send_series_files_to_user(client, user_id, verified_files, query=query)
    t_send_end = time.perf_counter()
    
    req["delivery_status"] = "completed"
    req["state"] = "COMPLETED"
    log.info(f"[SERIES DELIVERY]\naction=COMPLETED\nrequest_key={req_key}")

    log.info(
        f"[SERIES DELIVERY TIMING]\n"
        f"request_received={t_received - t0:.3f}s\n"
        f"request_loaded={t_loaded - t0:.3f}s\n"
        f"membership_checked={t_membership - t0:.3f}s\n"
        f"series_resolved={t_resolved - t0:.3f}s\n"
        f"episodes_loaded={t_files - t_resolved:.3f}s\n"
        f"files_loaded={t_files - t0:.3f}s\n"
        f"files_verified={t_verified - t0:.3f}s\n"
        f"send_started={t_send_start - t0:.3f}s\n"
        f"send_completed={t_send_end - t0:.3f}s\n"
        f"total_time={t_send_end - t0:.3f}s"
    )
    return True


@Client.on_callback_query(filters.regex(r"^sr#"))
async def series_user_nav(client: Client, query: CallbackQuery):
    from utils import temp
    import logging
    log = logging.getLogger(__name__)

    log.info(
        f"[SERIES CALLBACK RECEIVED]\n"
        f"callback_data={query.data}\n"
        f"user_id={query.from_user.id}\n"
        f"chat_id={query.message.chat.id if query.message else 'N/A'}\n"
        f"chat_type={query.message.chat.type if query.message else 'N/A'}"
    )

    parts = query.data.split("#")
    
    if len(parts) < 2:
        return await query.answer("⚠️ Invalid request.", show_alert=True)
        
    key = parts[1]
    if key == "close":
        return await query.message.delete()
        
    req = getattr(temp, "SERIES_STATE", {}).get(key)
    if not req:
        from database.series_db import get_temp_request
        req = await get_temp_request(key)
        if req:
            if not hasattr(temp, "SERIES_STATE"):
                temp.SERIES_STATE = {}
            temp.SERIES_STATE[key] = req

    if not req:
        return await query.answer("⚠️ Request expired. Please search again.", show_alert=True)
        
    owner_id = req.get("user", req.get("user_id"))
    if owner_id and int(query.from_user.id) != int(owner_id):
        log.info("[SERIES CALLBACK] ownership=DENIED")
        return await query.answer("⚠️ This is not your button.", show_alert=True)
    log.info("[SERIES CALLBACK] ownership=ALLOWED")
        
    sid = req.get("sid", req.get("series_id"))
    if not sid:
        return await query.answer("⚠️ Unable to process this Series request. Please search again.", show_alert=True)
    
    full_id = await _get_full_id(sid)
    if not full_id:
        log.error(
            f"[SERIES ID ERROR]\n"
            f"sid={sid}\n"
            f"full_id=None"
        )
        return await query.answer("⚠️ Unable to process this Series request. Please search again.", show_alert=True)
    
    series = await get_series(full_id)
    if not series:
        return await query.answer("⚠️ Unable to process this Series request. Please search again.", show_alert=True)

    lang = None
    season = None
    qual = None
    path_type = req.get("path", "DIRECT" if req.get("is_direct") else "SUGGESTION")
    is_direct_val = bool(req.get("is_direct", (path_type == "DIRECT")))
    
    # ── Send file (Quality selected) ──────────────────────────────────
    if len(parts) >= 8 and parts[2] == "l" and parts[4] == "s" and parts[6] == "q":
        try:
            import time
            lang    = parts[3]
            season  = int(parts[5])
            qual    = parts[7]
            ep      = int(parts[9]) if (len(parts) >= 10 and parts[8] == "e") else None
            
            rating = series.get("rating", "N/A")
            chat_type = "PRIVATE" if query.message.chat.type == enums.ChatType.PRIVATE else "GROUP"

            import uuid as _uuid
            from utils import temp as _temp
            from database.series_db import save_temp_request, get_temp_request
            
            req_key = str(_uuid.uuid4())[:8]

            # Trace working suggestion vs direct test
            if path_type == "SUGGESTION":
                log.info(
                    f"[SERIES SUGGESTION WORKING]\n"
                    f"sid={sid}\n"
                    f"full_id={full_id}\n"
                    f"language={lang}\n"
                    f"season={season}\n"
                    f"quality={qual}\n"
                    f"episodes={ep}"
                )
                log.info(
                    f"[SERIES SUGGESTION QUALITY]\n"
                    f"request_key={req_key}\n"
                    f"sid={sid}\n"
                    f"full_id={full_id}\n"
                    f"language={lang}\n"
                    f"season={season}\n"
                    f"quality={qual}\n"
                    f"episode={ep}"
                )
            else:
                log.info(
                    f"[SERIES DIRECT TEST]\n"
                    f"sid={sid}\n"
                    f"full_id={full_id}\n"
                    f"language={lang}\n"
                    f"season={season}\n"
                    f"quality={qual}\n"
                    f"episodes={ep}"
                )
                log.info(
                    f"[SERIES DIRECT QUALITY]\n"
                    f"request_key={req_key}\n"
                    f"sid={sid}\n"
                    f"full_id={full_id}\n"
                    f"language={lang}\n"
                    f"season={season}\n"
                    f"quality={qual}\n"
                    f"episode={ep}"
                )

            # ── 10-Second Cooldown Protection (PM Series Quality Button) ──
            if query.message.chat.type == enums.ChatType.PRIVATE:
                import math
                now = time.time()
                if not hasattr(temp, "SERIES_PM_QUALITY_COOLDOWNS"):
                    temp.SERIES_PM_QUALITY_COOLDOWNS = {}

                for k, t in list(temp.SERIES_PM_QUALITY_COOLDOWNS.items()):
                    if now - t > 60:
                        temp.SERIES_PM_QUALITY_COOLDOWNS.pop(k, None)

                cooldown_key = (query.from_user.id, key, lang, season, qual)
                last_click_time = temp.SERIES_PM_QUALITY_COOLDOWNS.get(cooldown_key)

                if last_click_time is not None:
                    elapsed = now - last_click_time
                    if elapsed < 10:
                        remaining = math.ceil(10 - elapsed)
                        log.info(f"[SERIES PM QUALITY]\nuser_id={query.from_user.id}\nquality={qual}\naction=COOLDOWN_BLOCKED\nremaining={remaining}")
                        alert_text = f"⏳ Please wait {remaining} seconds." if remaining > 1 else f"⏳ Please wait {remaining} second."
                        return await query.answer(alert_text, show_alert=True)

                temp.SERIES_PM_QUALITY_COOLDOWNS[cooldown_key] = now

            if path_type == "DIRECT" or is_direct_val:
                log.info(
                    f"[SERIES DIRECT TRACE]\n"
                    f"user_id={query.from_user.id}\n"
                    f"sid={sid}\n"
                    f"full_id={full_id}\n"
                    f"language={lang}\n"
                    f"season={season}\n"
                    f"quality={qual}\n"
                    f"request_key={req_key}"
                )

            req_data = {
                "request_key": req_key,
                "user": query.from_user.id,
                "user_id": query.from_user.id,
                "type": "series",
                "request_type": "series",
                "source": "DIRECT" if (path_type == "DIRECT" or is_direct_val) else "SUGGESTION",
                "path": path_type,
                "is_direct": is_direct_val,
                "sid": sid,
                "series_id": full_id,
                "full_id": full_id,
                "language": lang,
                "season": int(season),
                "quality": qual,
                "episode": ep if (ep is not None and ep > 0) else None,
                "rating": series.get("rating", "N/A"),
                "delivery_status": "pending",
                "state": "PENDING",
                "created_at": time.time(),
                "query": {
                    "full_id": full_id,
                    "lang": lang,
                    "season": int(season),
                    "qual": qual,
                    "rating": series.get("rating", "N/A")
                }
            }
            _temp.SERIES_STATE[req_key] = req_data
            _temp.GETALL[req_key] = req_data
            try:
                await save_temp_request(req_key, req_data)
                test_req = await get_temp_request(req_key)
                if test_req:
                    log.info(f"[SERIES GROUP QUALITY]\naction=REQUEST_SAVED\nrequest_key={req_key}")
                else:
                    log.warning(f"[SERIES GROUP QUALITY]\naction=REQUEST_SAVE_VERIFY_FAILED\nrequest_key={req_key}")
            except Exception as ex:
                log.error(f"[SERIES GROUP QUALITY]\naction=REQUEST_SAVE_VERIFY_FAILED\nrequest_key={req_key}\nerror={ex}")

            log.info(
                f"[SERIES QUALITY ROUTING]\n"
                f"path={path_type}\n"
                f"chat_type={chat_type}\n"
                f"user_id={query.from_user.id}\n"
                f"sid={sid}\n"
                f"full_id={full_id}\n"
                f"language={lang}\n"
                f"season={season}\n"
                f"quality={qual}\n"
                f"request_key={req_key}"
            )

            bot_username = temp.U_NAME if (hasattr(temp, "U_NAME") and temp.U_NAME) else getattr(getattr(client, "me", None), "username", None)
            if bot_username:
                bot_username = str(bot_username).lstrip("@")
            else:
                bot_username = "Bot"

            start_url = f"https://t.me/{bot_username}?start=all_{req_key}"
            log.info(
                f"[SERIES QUALITY ROUTING]\n"
                f"action=OPEN_PM\n"
                f"start_url={start_url}"
            )
            try:
                return await query.answer(url=start_url)
            except Exception as e:
                log.warning(f"[SERIES QUALITY ROUTING] query.answer(url=start_url) failed: {e}. Replying with fallback button.")
                return await query.message.reply_text(
                    "📩 Open bot to get your requested Series files:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📂 Open Bot", url=start_url)]
                    ])
                )
        except Exception as e:
            log.exception(f"[SERIES QUALITY ERROR] {e}")
            return await query.answer("⚠️ Unable to process this Series request.", show_alert=True)

    # Navigation mapping
    if len(parts) >= 4 and parts[2] == "l":
        lang = parts[3]
    if len(parts) >= 6 and parts[4] == "s":
        season = int(parts[5])
    if len(parts) >= 8 and parts[6] == "q":
        qual = parts[7]
        
    try:
        await query.answer()
    except Exception:
        pass

    text, rm = await _resolve_nav_step(query.from_user.id, full_id, key, series, lang, season, qual, is_private=(query.message.chat.type == enums.ChatType.PRIVATE))
    if rm:
        poster = series.get("poster")
        await _send_or_edit(query, text, rm, poster=poster)
        return
    
    return





# ═════════════════════════════════════════════════════════════════════════════
# ─── /serieslist —” Admin: list all series ────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════



import math



async def send_series_list(message_or_query, unique_series, page=0):
    per_page = 10
    total_pages = math.ceil(len(unique_series) / per_page)
    if total_pages == 0:
        total_pages = 1
        
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    page_series = unique_series[start_idx:end_idx]
    
    text = f"📁š <b>Added Series —” Page {page + 1}/{total_pages}</b>\n\n"
    for i, s in enumerate(page_series, start=start_idx + 1):
        text += f"{i}. {s['name']}\n"
    text += f"\nTotal: {len(unique_series)} Series"
    
    rows = []
    for s in page_series:
        series_id = str(s["_id"])
        rows.append([InlineKeyboardButton(f"âœï¸ {s['name']}", callback_data=f"edser#{series_id}")])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"vser#{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next âž¡ï¸", callback_data=f"vser#{page + 1}"))
        
    if nav_buttons:
        rows.append(nav_buttons)
        
    rows.append([InlineKeyboardButton("🔴 Cancel", callback_data="vser#close")])
        
    markup = InlineKeyboardMarkup(rows)
    
    if isinstance(message_or_query, Message):
        await message_or_query.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    else:
        await message_or_query.message.edit_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)





@Client.on_callback_query(filters.regex(r"^vser#"))
async def cb_vser_page(client: Client, query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        return await query.answer("âŒ You are not authorized.", show_alert=True)
        
    action = query.data.split("#")[1]
    if action in ["close", "cancel"]:
        try:
            await query.message.delete()
        except Exception:
            pass
        return await query.answer()
        
    page = int(action)
    from database.series_db import list_all_series
    all_series = await list_all_series()
    
    seen = set()
    unique_series = []
    for s in all_series:
        name = s.get("name", "").strip()
        name_lower = name.lower()
        if name_lower not in seen:
            seen.add(name_lower)
            unique_series.append(s)



    unique_series.sort(key=lambda x: x.get("name", "").lower())
    await send_series_list(query, unique_series, page=page)



import logging
logger = logging.getLogger(__name__)
logger.info("[VIEWSERIES] handler registered")



@Client.on_message(filters.command(["serieslist", "viewseries"]), group=1)
async def cmd_serieslist(client: Client, message: Message):
    is_admin = False
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        admin_list = await client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        is_admin = any(admin.user.id == message.from_user.id for admin in admin_list if admin.user)
    else:
        is_admin = message.from_user.id in ADMINS
    
    if not is_admin:
        return await message.reply_text("âŒ You are not authorized to use this command.")



    from database.series_db import list_all_series
    all_series = await list_all_series()
    
    logger.info("[VIEWSERIES] fetched series count=%s", len(all_series))
    
    if not all_series:
        return await message.reply_text(
            "No Series have been added yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Cancel", callback_data="vser#close")]])
        )



    seen = set()
    unique_series = []
    for s in all_series:
        name = s.get("name", "").strip()
        name_lower = name.lower()
        if name_lower not in seen:
            seen.add(name_lower)
            unique_series.append(s)



    unique_series.sort(key=lambda x: x.get("name", "").lower())
    await send_series_list(message, unique_series, page=0)





# ═════════════════════════════════════════════════════════════════════════════
# ─── /seriesdel —” Admin: delete a series ─────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════



@Client.on_message(filters.command(["seriesdel", "delseries"]) & (filters.private | filters.group), group=1)
async def cmd_seriesdel(client: Client, message: Message):
    is_admin = False
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        admin_list = await client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        is_admin = any(admin.user.id == message.from_user.id for admin in admin_list if admin.user)
    else:
        is_admin = message.from_user.id in ADMINS
    if not is_admin:
        return await message.reply_text("âŒ Not authorized.")



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
        return await message.reply_text(f"âŒ No series found matching '<b>{arg}</b>'.", parse_mode=enums.ParseMode.HTML)
    
    match = matches[0]
    await _del(str(match["_id"]))
    await message.reply_text(f"✅ Series <b>{match['name']}</b> deleted (soft).", parse_mode=enums.ParseMode.HTML)





# ═════════════════════════════════════════════════════════════════════════════
# ─── STARTUP: Ensure DB indexes ──────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════



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
@Client.on_callback_query(filters.regex(r"^series_getall#"))
async def handle_series_getall(client: Client, query: CallbackQuery):
    try:
        key = query.data.split("#")[1]
        
        # Verify ownership
        req = temp.GETALL.get(key)
        if not req:
            return await query.answer("⚠️ Request expired. Please search again.", show_alert=True)
            
        if req.get("user") and query.from_user.id != req["user"]:
            return await query.answer("⚠️ This is not your button.", show_alert=True)
            
        # Success: open the deep link
        start_url = f"https://t.me/{temp.U_NAME}?start=all_{key}"
        await query.answer(url=start_url)
        
    except Exception as e:
        logger.error(f"Error in handle_series_getall: {e}")
        await query.answer("⚠️ An error occurred.", show_alert=True)

