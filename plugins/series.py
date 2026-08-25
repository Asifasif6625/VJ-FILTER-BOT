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
import time
import html
from datetime import datetime, timedelta

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
    get_series_by_key,
    make_series_key,
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
    set_announcement_channel,
    get_announcement_channel,
    delete_announcement_channel,
    is_announcement_sent,
    get_announcement,
    save_announcement,
    delete_announcement,
    get_super_movie,
    create_super_movie,
    update_super_movie,
    delete_super_movie,
    search_super_movies,
    list_all_super_movies,
    super_movies_col,
    sync_movie_filter_for_files,
    sync_existing_movie_filter,
    scan_movie_files_by_identity,
)
try:
    from database.series_db import scan_movie_batch_by_name_year
except ImportError:
    scan_movie_batch_by_name_year = scan_movie_files_by_identity

from utils import (
    temp,
    get_poster,
    get_imdb_metadata_direct,
    get_imdb_public_metadata,
    get_tmdb_public_metadata,
    get_public_movie_metadata,
    set_wizard_session,
    get_wizard_session,
    clear_wizard_session,
    cancel_wizard_session,
    get_size,
    match_movie_identity,
    extract_release_year,
    normalize_title_for_matching,
)

import os
logger = logging.getLogger(__name__)
print("### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###", flush=True)
print("### SERIES PLUGIN LOADED ###", flush=True)
print(f"### SERIES.PY PATH = {os.path.abspath(__file__)} ###", flush=True)
print("[HANDLER REGISTERED] wizard_text_handler", flush=True)
print("[HANDLER REGISTERED] series_wizard_callback", flush=True)
print("[HANDLER REGISTERED] auto_movie_callbacks", flush=True)
logger.warning("### VJ BOT MOVIE SERIES FIX V6 ACTIVE ###")


def _is_admin(user_id: int) -> bool:
    if not user_id:
        return False
    try:
        uid = int(user_id)
        admin_str_set = {str(a).strip() for a in ADMINS if str(a).strip()}
        if str(uid) in admin_str_set:
            return True
        admin_ids = [int(a) for a in ADMINS if str(a).lstrip("-").isdigit()]
        return uid in admin_ids
    except Exception:
        return False


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

def to_series_font(text: str) -> str:
    """Converts regular text to small-caps series styling font."""
    table = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    }
    return "".join(table.get(c, c) for c in str(text))

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
    "punjabi": "Punjabi", "pun": "Punjabi",
    "gujarati": "Gujarati", "guj": "Gujarati",
    "urdu": "Urdu", "urd": "Urdu",
    "odia": "Odia", "ori": "Odia", "oriya": "Odia",
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
    Supports resolution, bit-depth (10bit), HDR/Dolby Vision, and source tags in priority order.
    """
    if not filename:
        return "Unknown"

    text = str(filename)
    text = re.sub(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts)$", "", text, flags=re.I)
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

    if res:
        return res

    # 2. Fallback Source Tags if no resolution was found
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

    # Try combined S01E03 / S1E3 / S01.E03 / S01-E03 / S01_E03
    m = re.search(r"(?i)(?:^|[^A-Z0-9])S(\d{1,3})\s*[\.\-_]?\s*E(\d{1,4})(?:[^A-Z0-9]|$)", token_text)
    if m:
        season_val = int(m.group(1))
        episode_val = int(m.group(2))
    else:
        # Try 01x03 / 1x03
        m = re.search(r"(?i)(?:^|[^A-Z0-9])(\d{1,3})\s*x\s*(\d{1,4})(?:[^A-Z0-9]|$)", token_text)
        if m:
            season_val = int(m.group(1))
            episode_val = int(m.group(2))
        else:
            # Clean resolution strings (e.g. 1080p, 720p, 480p) to avoid matching 1080 as episode/season
            clean_for_ep = re.sub(r'(?i)\b(2160|1440|1080|720|576|480|360|240)p?\b', '', token_text)
            
            # S01 / Season 01
            m_s = re.search(r"(?i)(?:^|[^A-Z0-9])(?:S|SEASON)\s*(\d{1,3})(?:[^A-Z0-9]|$)", clean_for_ep)
            # E01 / Episode 01 / EP 01
            m_e = re.search(r"(?i)(?:^|[^A-Z0-9])(?:E|EP|EPISODE)\s*(\d{1,4})(?:[^A-Z0-9]|$)", clean_for_ep)
            if m_s and m_e:
                season_val = int(m_s.group(1))
                episode_val = int(m_e.group(1))
            elif m_e:
                episode_val = int(m_e.group(1))
                season_val = int(m_s.group(1)) if m_s else (target_season if target_season is not None else 1)
            elif m_s and target_season is not None:
                season_val = int(m_s.group(1))
                m_num = re.search(r"(?:^|[^A-Z0-9])\[?(\d{1,3})\]?(?:[^A-Z0-9]|$)", clean_for_ep)
                if m_num:
                    episode_val = int(m_num.group(1))

    if season_val is None and target_season is not None:
        season_val = target_season
    if season_val is None:
        season_val = 1

    if episode_val is None or episode_val <= 0:
        return {"status": "invalid", "reason": "missing_season_or_episode"}

    # 2. Series Title Match Validation
    from utils import normalize_title_for_matching
    norm_series = normalize_title_for_matching(series_title)
    clean_no_ep = re.sub(r"(?i)\b(?:s\d{1,2}|season\s*\d{1,2}|e\d{1,4}|ep\s*\d{1,4}|\d{1,2}x\d{1,4})\b", " ", cleaned)
    norm_fname = normalize_title_for_matching(clean_no_ep)

    if not norm_fname or not norm_series:
        return {"status": "invalid", "reason": "empty_title"}

    f_toks = norm_fname.split()
    s_toks = norm_series.split()

    if f_toks != s_toks:
        if any(t in f_toks and t not in s_toks for t in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "chapter", "part", "korea"]):
            return {"status": "invalid", "reason": "title_mismatch"}
        if sum(1 for tok in s_toks if tok in f_toks) < max(1, len(s_toks) - (1 if len(s_toks) >= 4 else 0)):
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


def _fetch_movie_candidates_sync(title: str, year: str | int = None, limit: int = 500) -> list:
    """
    Synchronous bounded candidate search for movie files.
    Runs inside background thread pool with explicit cursor closing and max_time_ms.
    """
    from database.ia_filterdb import col, sec_col, MULTIPLE_DATABASE
    clean_title = re.sub(r"[\._\-\+\[\]\(\)\{\}:;!?,/\\~|#*\"\'`]", " ", clean_series_title(title))
    q_tokens = [w for w in clean_title.lower().split() if len(w) > 1]
    if not q_tokens:
        q_tokens = [clean_title.lower().strip()] if clean_title.strip() else ["a"]

    year_str = str(year).strip() if (year and str(year).strip() not in ["N/A", "None", "0", ""]) else None
    results = []
    seen_ids = set()

    logger.info(f"[AUTO MOVIE SCAN] DB QUERY START title={title} year={year_str}")

    # Build targeted regex with title tokens
    tok_pat = ".*".join(re.escape(t) for t in q_tokens[:3])
    try:
        reg = re.compile(tok_pat, re.IGNORECASE)
    except Exception:
        reg = re.compile(re.escape(clean_title), re.IGNORECASE)

    # Execute on primary collection
    cursor = None
    try:
        cursor = col.find({"file_name": reg}).max_time_ms(4000).limit(limit)
        for doc in cursor:
            fid = doc.get("file_id")
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                results.append(doc)
    except Exception as e:
        logger.error(f"[AUTO MOVIE SCAN] DB QUERY ERROR {e}")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

    # Execute on secondary collection if enabled and room remains
    if MULTIPLE_DATABASE and len(results) < limit:
        sec_cursor = None
        try:
            sec_cursor = sec_col.find({"file_name": reg}).max_time_ms(4000).limit(limit - len(results))
            for doc in sec_cursor:
                fid = doc.get("file_id")
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    results.append(doc)
        except Exception as e:
            logger.error(f"[AUTO MOVIE SCAN] DB QUERY SEC ERROR {e}")
        finally:
            if sec_cursor is not None:
                try:
                    sec_cursor.close()
                except Exception:
                    pass

    logger.info(f"[AUTO MOVIE SCAN] DB QUERY DONE count={len(results)}")
    return results


async def get_movie_candidates(chat_id: int | str, title: str, year: str | int = None, limit: int = 500) -> list:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_movie_candidates_sync, title, year, limit)


async def scan_sdatabase_for_series(chat_id: int | str, title: str, season: int = None, series_id: str = None, client: Client = None) -> dict:
    """
    Scan the stored file database for files matching the given Series and Season.
    If season is None (Skip Season mode), automatically scans and detects all available seasons.
    Returns structured results with valid files, organized hierarchy, and accurate statistics.
    """
    from database.series_db import check_episode_exists

    clean_title = clean_series_title(title)
    docs = await get_movie_candidates(chat_id, title, limit=500)

    valid_new_files = []
    duplicate_files = []
    all_matching_files = []
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
        s_val = parsed["season"]
        ep = parsed["episode"]
        qual = parsed["quality"]

        file_entry = {
            "language": lang,
            "season": s_val,
            "episode": ep,
            "quality": qual,
            "file_id": doc.get("file_id"),
            "file_name": doc.get("file_name"),
            "file_size": doc.get("file_size", 0),
            "caption": doc.get("caption"),
        }
        all_matching_files.append(file_entry)

        key = (lang, s_val, ep, qual, doc.get("file_id"))
        if key in seen_file_keys:
            continue
        seen_file_keys.add(key)

        is_dup = False
        if series_id:
            try:
                is_dup = await check_episode_exists(series_id, lang, s_val, ep, qual)
            except Exception:
                pass

        if is_dup:
            total_duplicates += 1
            duplicate_files.append(file_entry)
            logger.info(f"[AUTO_MOVE_ADD] parsed file={fname} season={s_val} episode={ep} quality={qual} language={lang} duplicate=True")
        else:
            total_new += 1
            valid_new_files.append(file_entry)
            logger.info(f"[AUTO_MOVE_ADD] parsed file={fname} season={s_val} episode={ep} quality={qual} language={lang} new=True")

    valid_new_files.sort(key=lambda x: (x["season"], x["language"], x["quality"], x["episode"]))
    all_matching_files.sort(key=lambda x: (x["season"], x["language"], x["quality"], x["episode"]))

    # Grouped by season from all matching files for display
    display_source = all_matching_files if all_matching_files else valid_new_files
    organized_by_season = {}
    for f in display_source:
        s = f["season"]
        l = f["language"]
        q = f["quality"]
        if s not in organized_by_season:
            organized_by_season[s] = {}
        if l not in organized_by_season[s]:
            organized_by_season[s][l] = {}
        if q not in organized_by_season[s][l]:
            organized_by_season[s][l][q] = []
        if not any(x["episode"] == f["episode"] for x in organized_by_season[s][l][q]):
            organized_by_season[s][l][q].append(f)

    # Simple flattened organization for single-season mode
    organized = {}
    for f in display_source:
        l = f["language"]
        q = f["quality"]
        if l not in organized:
            organized[l] = {}
        if q not in organized[l]:
            organized[l][q] = []
        organized[l][q].append(f)

    logger.info(f"[AUTO_SERIES SCAN] series={clean_title} scanned={total_scanned} matched={total_matched} new={total_new} duplicate={total_duplicates}")

    return {
        "valid_files": valid_new_files,
        "valid_new_files": valid_new_files,
        "all_matching_files": all_matching_files,
        "duplicate_files": duplicate_files,
        "matching_files": all_matching_files,
        "rejected_files": [],
        "organized": organized,
        "organized_by_season": organized_by_season,
        "total_scanned": total_scanned,
        "total_matched": total_matched,
        "total_new": total_new,
        "total_duplicates": total_duplicates,
        "total_other_season": total_other_season,
        "total_invalid": total_invalid,
    }


def parse_movie_filename(filename: str, movie_title: str, movie_year: str = None, imdb_id: str = None, tmdb_id: str = None, known_conflicts: set = None, caption: str = "") -> dict:
    """
    Validates whether a candidate file belongs to requested movie using strict identity matching.
    """
    if not filename:
        return {"status": "invalid", "reason": "empty_filename"}

    from utils import match_movie_identity, normalize_title_for_matching, extract_release_year

    logger.info(
        "[AUTO MOVIE MATCH DEBUG] "
        f"requested_title={movie_title!r} "
        f"requested_year={movie_year!r} "
        f"filename={filename!r} "
        f"caption={caption!r} "
        f"imdb_id={imdb_id!r} "
        f"tmdb_id={tmdb_id!r}"
    )

    file_doc = {"file_name": filename, "caption": caption}
    is_match, reason = match_movie_identity(
        file_doc,
        requested_title=movie_title,
        requested_year=movie_year,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        known_conflicts=known_conflicts
    )

    norm_req = normalize_title_for_matching(movie_title)
    norm_fn = normalize_title_for_matching(filename)
    f_yr = extract_release_year(filename, caption)

    if not is_match:
        logger.warning(
            "[AUTO MOVIE MATCH REJECT] "
            f"filename={filename!r} "
            f"requested_title={movie_title!r} "
            f"requested_year={movie_year!r} "
            f"reason={reason}"
        )
        return {"status": "invalid", "reason": reason}

    logger.info(
        f"[AUTO MOVIE MATCH DEBUG] "
        f"requested_normalized={norm_req!r} "
        f"filename_normalized={norm_fn!r} "
        f"requested_year={movie_year!r} "
        f"filename_year={f_yr!r} "
        f"result=MATCHED"
    )

    raw_name = str(filename)
    detected_quality = extract_quality_from_filename(raw_name)

    from plugins.pm_filter import detect_file_languages
    langs = detect_file_languages(raw_name, caption)
    if langs:
        detected_lang = langs[0]
    else:
        detected_lang = "English"

    return {
        "status": "matched",
        "title": movie_title,
        "language": detected_lang,
        "quality": detected_quality,
        "reason": reason,
    }


async def scan_sdatabase_for_movie(
    chat_id: int | str,
    title: str,
    year: str = None,
    client: Client = None,
    imdb_id: str = None,
    tmdb_id: str = None,
    movie_id: str = None
) -> dict:
    """
    Scan database for files belonging strictly to the specified movie (Title + Release Year).
    Calls dedicated scan_movie_files_by_identity for canonical scanning and matching.
    """
    import time
    start_total = time.monotonic()
    from database.series_db import scan_movie_files_by_identity, get_super_movie

    existing_fids = set()
    if movie_id:
        try:
            sm = await get_super_movie(movie_id)
            if sm:
                existing_fids = set(sm.get("file_ids", []))
        except Exception:
            pass

    scan_res = await scan_movie_batch_by_name_year(
        title=title,
        year=year,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id
    )

    all_matching_files = scan_res.get("matching_files", [])
    valid_new_files = []
    duplicate_files = []
    seen_keys = set()

    for doc in all_matching_files:
        fid = doc.get("file_id")
        lang = doc.get("language", "English")
        qual = doc.get("quality", "Unknown")

        file_entry = {
            "title": title,
            "language": lang,
            "quality": qual,
            "file_id": fid,
            "file_name": doc.get("file_name", ""),
            "file_size": doc.get("file_size", 0),
            "caption": doc.get("caption"),
        }

        key = (lang, qual, fid)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        is_dup = (fid in existing_fids) if existing_fids else False
        if is_dup:
            duplicate_files.append(file_entry)
        else:
            valid_new_files.append(file_entry)

    valid_new_files.sort(key=lambda x: (x["language"], x["quality"]))
    all_matching_files.sort(key=lambda x: (x["language"], x["quality"]))

    organized = {}
    for f in (all_matching_files or valid_new_files):
        l = f["language"]
        q = f["quality"]
        if l not in organized:
            organized[l] = []
        if q not in organized[l]:
            organized[l].append(q)

    total_matched = len(all_matching_files)
    total_new = len(valid_new_files)
    total_duplicates = len(duplicate_files)
    total_scanned = scan_res.get("files_scanned", 0)
    total_rej_year = scan_res.get("year_mismatch_count", 0)
    total_rej_title = scan_res.get("title_mismatch_count", 0)
    total_unknown_year = scan_res.get("unknown_year_count", 0)

    total_dur = time.monotonic() - start_total
    logger.info(
        f"[AUTO MOVIE] MATCH DONE matched={total_matched} rejected_year={total_rej_year} rejected_title={total_rej_title} duration={total_dur:.2f}s"
    )

    return {
        "valid_files": valid_new_files,
        "valid_new_files": valid_new_files,
        "all_matching_files": all_matching_files,
        "duplicate_files": duplicate_files,
        "matching_files": all_matching_files,
        "rejected_files": [],
        "rejected_year_mismatch": total_rej_year,
        "rejected_title_mismatch": total_rej_title,
        "unknown_year": total_unknown_year,
        "organized": organized,
        "total_scanned": total_scanned,
        "total_matched": total_matched,
        "total_new": total_new,
        "total_duplicates": total_duplicates,
        "total_rejected_year": total_rej_year,
        "total_rejected_title": total_rej_title,
        "total_unknown_quality": 0,
        "total_invalid": total_scanned - total_matched,
    }


# ??? Auto Movie Add Hierarchical UI Helpers ?????????????????????????????????

LANGUAGE_FLAGS = {
    "Malayalam": "????",
    "Tamil": "????",
    "Hindi": "????",
    "Telugu": "????",
    "Kannada": "????",
    "Bengali": "????",
    "Marathi": "????",
    "Punjabi": "????",
    "Gujarati": "????",
    "Urdu": "????",
    "Odia": "????",
    "English": "????",
    "Dual Audio": "??",
    "Multi Audio": "??",
    "German": "????",
    "Korean": "????",
    "Japanese": "????",
    "Spanish": "????",
    "French": "????",
    "Arabic": "????",
    "Russian": "????",
    "Chinese": "????",
    "Italian": "????",
    "Portuguese": "????",
    "Turkish": "????",
    "Thai": "????",
}

def _group_auto_movie_files(res):
    match_list = res.get("all_matching_files") or res.get("valid_files") or []
    grouped = {}
    for f in match_list:
        l = f.get("language") or "English"
        q = f.get("quality") or "Unknown"
        if l not in grouped:
            grouped[l] = {}
        if q not in grouped[l]:
            grouped[l][q] = []
        grouped[l][q].append(f)
    return grouped

def _build_auto_movie_lang_text(movie_data):
    import html
    res = movie_data.get("scan", {})
    grouped = movie_data.get("grouped", {})
    if not grouped:
        grouped = _group_auto_movie_files(res)
        movie_data["grouped"] = grouped

    title_esc = html.escape(str(movie_data.get('title', '')))
    year_esc = html.escape(str(movie_data.get('year', '')))
    genre_esc = html.escape(str(movie_data.get('genre', '')))
    rating_esc = html.escape(str(movie_data.get('rating', '')))
    runtime_esc = html.escape(str(movie_data.get('runtime', '')))

    rating_str = f"\n⭐ <b>{rating_esc}/10</b>" if rating_esc else ""
    genre_str = f"\n🎭 <b>{genre_esc}</b>" if genre_esc and genre_esc != "N/A" else ""
    runtime_str = f"\n⏱ {runtime_esc}" if runtime_esc else ""

    tot_scanned = res.get('total_scanned', 0)
    tot_matched = res.get('total_matched', 0)
    tot_new = res.get('total_new', 0)
    tot_dup = res.get('total_duplicates', 0)
    tot_rej_year = res.get('total_rejected_year', 0)
    tot_rej_title = res.get('total_rejected_title', 0)

    # Build stats block
    stats_lines = [
        f"📁 <b>Files scanned:</b> {tot_scanned}",
        f"✅ <b>Matching files:</b> {tot_matched}",
    ]
    if tot_rej_year > 0:
        stats_lines.append(f"❌ <b>Other-year files:</b> {tot_rej_year}")
    if tot_rej_title > 0:
        stats_lines.append(f"❌ <b>Other-title files:</b> {tot_rej_title}")
    if tot_new > 0:
        stats_lines.append(f"🆕 <b>New files:</b> {tot_new}")
    if tot_dup > 0:
        stats_lines.append(f"⚠️ <b>Already linked:</b> {tot_dup}")

    stats_block = "\n".join(stats_lines)

    # 1. Zero matching files
    if tot_matched == 0:
        return (
            f"🎬 <b>AUTO MOVIE ADD</b>\n\n"
            f"🎬 <b>{title_esc} ({year_esc})</b>"
            f"{rating_str}"
            f"{genre_str}"
            f"{runtime_str}\n\n"
            f"❌ <b>NO MATCHING MOVIE FILES FOUND</b>\n\n"
            f"{stats_block}\n\n"
            "<i>Make sure files in database contain exact title and year.</i>"
        )

    # 2. Languages & Qualities Breakdown string
    lang_qual_lines = []
    preferred_order = ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English", "Dual Audio", "Multi Audio"]
    langs = sorted(list(grouped.keys()), key=lambda x: (preferred_order.index(x) if x in preferred_order else 99, x))
    for l in langs:
        flag = LANGUAGE_FLAGS.get(l, "🌐")
        lang_qual_lines.append(f"{flag} <b>{html.escape(str(l))}</b>")
        quals_dict = grouped[l]
        quality_order = ["2160p", "4K", "1440p", "1080p", "720p", "480p", "360p", "HDRip", "WEB-DL", "BluRay", "DVDRip", "HEVC", "Unknown"]
        sorted_quals = sorted(list(quals_dict.keys()), key=lambda x: (quality_order.index(x) if x in quality_order else 99, x))
        for q in sorted_quals:
            count = len(quals_dict[q])
            lang_qual_lines.append(f"• {html.escape(str(q))} — {count}")
            logger.info(f"[AUTO_MOVIE GROUP]\nlanguage={l}\nquality={q}\nfiles={count}")
        lang_qual_lines.append("")

    breakdown_str = "\n".join(lang_qual_lines).strip()

    # 3. All matching files already exist (0 new)
    if tot_matched > 0 and tot_new == 0 and tot_dup > 0:
        return (
            f"🎬 <b>AUTO MOVIE ADD</b>\n\n"
            f"🎬 <b>{title_esc} ({year_esc})</b>"
            f"{rating_str}"
            f"{genre_str}"
            f"{runtime_str}\n\n"
            f"📊 <b>Batch Scan Result</b>\n\n"
            f"{stats_block}\n\n"
            f"♻️ <i>All {tot_matched} matching files already exist in the database. Click below to create/sync the Super Movie Filter.</i>\n\n"
            f"🌐 <b>Languages & Qualities:</b>\n\n"
            f"{breakdown_str}"
        )

    # 4. New files found (Scan Result)
    return (
        f"🎬 <b>AUTO MOVIE ADD</b>\n\n"
        f"🎬 <b>{title_esc} ({year_esc})</b>"
        f"{rating_str}"
        f"{genre_str}"
        f"{runtime_str}\n\n"
        f"📊 <b>Batch Scan Result</b>\n\n"
        f"{stats_block}\n\n"
        f"🌐 <b>Languages & Qualities:</b>\n\n"
        f"{breakdown_str}"
    )

def _build_auto_movie_lang_keyboard(session_id, movie_data):
    res = movie_data.get("scan", {})
    tot_matched = res.get("total_matched", 0)
    tot_new = res.get("total_new", 0)
    tot_dup = res.get("total_duplicates", 0)

    buttons = []
    if tot_matched > 0:
        save_label = f"💾 Save Super Movie ({tot_new} New)" if tot_new > 0 else "💾 Save Super Movie Filter"
        buttons.append([InlineKeyboardButton(save_label, callback_data=f"am_save:{session_id}")])

    buttons.append([InlineKeyboardButton("🔍 Scan Database for Files", callback_data=f"am_scan:{session_id}")])
    buttons.append([InlineKeyboardButton("📦 Batch Add Files", callback_data=f"am_batch:{session_id}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data=f"am_cancel:{session_id}")])

    return InlineKeyboardMarkup(buttons)

def _build_auto_movie_qual_text(movie_data, lang):
    import html
    title_esc = html.escape(str(movie_data.get('title', '')))
    year_esc = html.escape(str(movie_data.get('year', '')))
    rating_esc = html.escape(str(movie_data.get('rating', '')))
    rating_str = f"\n⭐ <b>Rating:</b> {rating_esc}/10" if rating_esc else ""
    return (
        f"🎬 <b>{title_esc} ({year_esc})</b>"
        f"{rating_str}\n\n"
        f"🌐 <b>Language:</b> {html.escape(str(lang))}\n\n"
        f"🎞 <b>Select Quality:</b>"
    )

def _build_auto_movie_qual_keyboard(session_id, lang, qualities):
    buttons = []
    quality_order = ["2160p", "4K", "1440p", "1080p", "720p", "480p", "360p", "HDRip", "WEB-DL", "BluRay", "DVDRip", "HEVC", "Unknown"]
    qualities_sorted = sorted(qualities, key=lambda x: (quality_order.index(x) if x in quality_order else 99, x))

    for i in range(0, len(qualities_sorted), 2):
        row = []
        for q in qualities_sorted[i:i+2]:
            row.append(InlineKeyboardButton(q, callback_data=f"am_qual:{session_id}:{lang}:{q}"))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("⬅️ Language", callback_data=f"am_back:{session_id}:lang"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"am_cancel:{session_id}")
    ])
    return InlineKeyboardMarkup(buttons)

def _build_auto_movie_file_text(movie_data, lang, qual):
    import html
    title_esc = html.escape(str(movie_data.get('title', '')))
    year_esc = html.escape(str(movie_data.get('year', '')))
    rating_esc = html.escape(str(movie_data.get('rating', '')))
    rating_str = f"\n? <b>Rating:</b> {rating_esc}/10" if rating_esc else ""
    return (
        f"?? <b>{title_esc} ({year_esc})</b>"
        f"{rating_str}\n\n"
        f"?? <b>Language:</b> {html.escape(str(lang))}\n\n"
        f"?? <b>Quality:</b> {html.escape(str(qual))}\n\n"
        f"?? <b>Select File to Download / Test:</b>"
    )

def _build_auto_movie_file_keyboard(session_id, lang, qual, files, page=0, pre="file"):
    import math
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
                f"📥 [{f_size}] {cleaned_fn[:45]}",
                callback_data=f"{pre}#{f['file_id']}"
            )
        ])

    if total_pages > 1:
        pag_row = []
        if page > 0:
            pag_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"am_page:{session_id}:{lang}:{qual}:{page-1}"))
        pag_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="pages"))
        if page < total_pages - 1:
            pag_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"am_page:{session_id}:{lang}:{qual}:{page+1}"))
        buttons.append(pag_row)

    buttons.append([
        InlineKeyboardButton("⬅️ Quality", callback_data=f"am_lang:{session_id}:{lang}"),
        InlineKeyboardButton("⬅️ Language", callback_data=f"am_back:{session_id}:lang"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"am_cancel:{session_id}")
    ])
    return InlineKeyboardMarkup(buttons)


AUTO_MOVIE_METADATA_TASKS = {}
AUTO_SERIES_METADATA_TASKS = {}

AUTO_MOVIE_SCAN_LOCKS = {}
AUTO_MOVIE_SCAN_TASKS = {}
AUTO_MOVIE_CANCEL_EVENTS = {}

AUTO_MOVIE_METADATA_WATCHDOGS = {}
AUTO_SERIES_METADATA_WATCHDOGS = {}


async def _safe_edit_message(message, text, reply_markup=None, parse_mode=enums.ParseMode.HTML, timeout=5):
    """
    Safely edit a message with a strict timeout to prevent indefinite hangs.
    Returns True if edit succeeded, False otherwise. Never throws.
    """
    if not message:
        return False
    try:
        await asyncio.wait_for(
            message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            ),
            timeout=timeout
        )
        return True
    except asyncio.TimeoutError:
        logger.warning(f"[SAFE EDIT] Telegram edit timed out after {timeout}s")
        return False
    except Exception as e:
        logger.warning(f"[SAFE EDIT] Telegram edit failed: {e}")
        return False


def _log_background_task_result(task):
    try:
        exc = task.exception()
        if exc:
            logger.error(
                "[BACKGROUND TASK FAILED]",
                exc_info=exc
            )
    except asyncio.CancelledError:
        logger.info("[BACKGROUND TASK CANCELLED]")
    except Exception as e:
        logger.exception(
            f"[BACKGROUND TASK RESULT CHECK FAILED] {e}"
        )


async def fetch_auto_movie_metadata(client: Client, chat_id: int | str, loading_msg: Message, session_id: str, text: str, uid: int):
    """
    Dedicated metadata task for Auto Movie Add.
    Executes with hard deadline (15s), manages exact state transitions:
    WAIT_IMDB -> FETCHING_METADATA -> METADATA_COMPLETE -> SCANNING -> RESULT / ERROR / CANCELLED.
    """
    print("### AM_FETCH_ENTERED ###", flush=True)
    try:
        movie_data = temp.AUTO_MOVIE.get(session_id) or temp.AUTO_MOVIE.get(uid) or {}
        movie_data.update({
            "session_id": session_id,
            "user_id": uid,
            "state": "FETCHING_METADATA",
            "metadata_complete": False,
            "title": None,
            "year": None,
            "imdb_id": None,
            "tmdb_id": None,
        })
        temp.AUTO_MOVIE[session_id] = movie_data
        temp.AUTO_MOVIE[uid] = movie_data
        set_wizard_session(uid, workflow="AUTO_MOVIE", state="FETCHING_METADATA", data=movie_data, chat_id=chat_id)

        m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", text, re.I)
        m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)', text, re.I)

        logger.info(f"[AUTO MOVIE] METADATA ROUTE\nimdb={bool(m_imdb)}\ntmdb={bool(m_tmdb)}")
        logger.info("[AUTO MOVIE] METADATA TASK START")

        info = None
        imdb_id = None
        is_timeout = False
        is_error = False

        try:
            if m_tmdb:
                logger.info("[AUTO MOVIE] TMDB REQUEST START")
                print("### AM_STEP_02_BEFORE_TMDB ###", flush=True)
                info = await asyncio.wait_for(get_tmdb_public_metadata(text), timeout=15)
                print("### AM_STEP_03_AFTER_TMDB ###", flush=True)
                logger.info(f"[AUTO MOVIE] TMDB REQUEST DONE\ntitle={info.get('title') if info else None}\nyear={info.get('year') if info else None}")
            elif m_imdb:
                imdb_id = m_imdb.group(1).lower()
                logger.info("[AUTO MOVIE] IMDb REQUEST START")
                print("### AM_STEP_02_BEFORE_IMDB ###", flush=True)
                info = await asyncio.wait_for(get_imdb_public_metadata(imdb_id), timeout=15)
                print("### AM_STEP_03_AFTER_IMDB ###", flush=True)
                if info and info.get("title"):
                    logger.info(f"[AUTO MOVIE] IMDb PUBLIC METADATA COMPLETE\ntitle={info.get('title')}\nyear={info.get('year')}\nkind={info.get('kind')}")
                else:
                    logger.warning(f"[AUTO MOVIE] IMDb PUBLIC METADATA FAILED id={imdb_id}")
        except asyncio.TimeoutError:
            logger.error(f"[AUTO MOVIE] METADATA TIMEOUT query={text}")
            is_timeout = True
            info = None
        except asyncio.CancelledError:
            logger.info(f"[AUTO MOVIE] METADATA CANCELLED query={text}")
            movie_data["state"] = "CANCELLED"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
            try:
                await loading_msg.edit_text("❌ <b>Auto Movie Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
            return
        except Exception as e:
            logger.exception(f"[AUTO MOVIE] METADATA ERROR query={text}: {e}")
            is_error = True
            info = None

        print("### AM_STEP_04_METADATA_HANDLER ###", flush=True)

        cand_title = str(info.get("title", "")).strip() if info else ""
        if (
            not info
            or not cand_title
            or cand_title.lower() in ("the movie database", "tmdb", "themoviedb", "the movie database (tmdb)", "none", "imdb")
            or cand_title.lower().startswith("the movie database")
        ):
            movie_data["state"] = "ERROR"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
                clear_wizard_session(uid)

            retry_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Retry", callback_data="sw#start_auto_movie"),
                    InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
                ]
            ])

            if is_timeout:
                err_text = (
                    "⚠️ <b>Movie metadata timed out.</b>\n\n"
                    f"Query: <code>{text}</code>\n\n"
                    "The metadata service did not respond in time. Please try again."
                )
            elif is_error:
                err_text = (
                    "❌ <b>Movie metadata failed.</b>\n\n"
                    f"Query: <code>{text}</code>\n\n"
                    "Could not fetch movie details. Please verify the URL and try again."
                )
            else:
                err_text = (
                    "❌ <b>Could not retrieve movie data.</b>\n\n"
                    f"Query: <code>{text}</code>\n\n"
                    "Please provide a valid IMDb movie URL or TMDB movie URL."
                )

            try:
                await loading_msg.edit_text(err_text, reply_markup=retry_markup, parse_mode=enums.ParseMode.HTML)
            except Exception:
                try:
                    await client.send_message(chat_id, err_text, reply_markup=retry_markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
            return

        # Check for TV Series
        kind = str(info.get("kind", "")).lower()
        is_series = kind in ["tv series", "tv mini series", "series", "tvseries", "tv mini-series"] or (info.get("seasons") and str(info["seasons"]).isdigit() and int(info["seasons"]) > 0)
        if is_series:
            clear_wizard_session(uid)
            movie_data["state"] = "ERROR"
            temp.AUTO_MOVIE.pop(uid, None)
            try:
                await loading_msg.edit_text(
                    "⚠️ <b>This title is a TV Series.</b>\n\nPlease use Auto Series Add instead.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📺 Auto Series Add", callback_data="sw#start_auto"),
                        InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
                    ]]),
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception:
                pass
            return

        title = str(info["title"]).strip()
        year = str(info.get("year") or "N/A").strip()
        raw_genres = info.get("genres") or "N/A"
        genre = ", ".join(str(g) for g in raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
        rating = str(info.get("rating") or "").strip()
        poster = info.get("poster") or ""
        description = info.get("plot") or ""
        resolved_imdb_id = info.get("imdb_id") or imdb_id
        resolved_tmdb_id = info.get("tmdb_id")

        movie_data.update({
            "session_id": session_id,
            "user_id": uid,
            "title": title,
            "year": year,
            "genre": genre,
            "rating": rating,
            "poster": poster,
            "description": description,
            "imdb_id": resolved_imdb_id,
            "tmdb_id": resolved_tmdb_id,
            "metadata_complete": True,
            "state": "METADATA_COMPLETE",
            "created_at": time.time(),
        })
        temp.AUTO_MOVIE[session_id] = movie_data
        temp.AUTO_MOVIE[uid] = movie_data
        set_wizard_session(uid, workflow="AUTO_MOVIE", state="METADATA_COMPLETE", data=movie_data, chat_id=chat_id)

        logger.info(
            f"[AUTO MOVIE] METADATA COMPLETE\n"
            f"title={title}\n"
            f"year={year}\n"
            f"imdb_id={resolved_imdb_id}\n"
            f"tmdb_id={resolved_tmdb_id}"
        )

        rating_str = f"\n⭐ {rating}/10" if rating else ""
        genre_str = f"\n🎭 {genre}" if genre and genre != "N/A" else ""

        movie_found_text = (
            f"🎬 <b>Movie Found</b>\n\n"
            f"<b>{html.escape(title)}</b> ({year})"
            f"{rating_str}"
            f"{genre_str}\n\n"
            f"🔍 <b>Scanning database for matching files...</b>"
        )

        logger.info("[AUTO MOVIE UI] EDIT START")
        edit_ok = await _safe_edit_message(
            loading_msg,
            movie_found_text,
            parse_mode=enums.ParseMode.HTML,
            timeout=5
        )
        logger.info(f"[AUTO MOVIE UI] EDIT DONE success={edit_ok}")

        logger.info("[AUTO MOVIE] STARTING SCAN")
        print("### AM_STEP_05_START_SCAN ###", flush=True)
        await run_auto_movie_scan(client, chat_id, loading_msg, session_id, movie_data)
    finally:
        AUTO_MOVIE_METADATA_TASKS.pop(session_id, None)


async def fetch_auto_series_metadata(client: Client, chat_id: int | str, loading_msg: Message, session_id: str, text: str, uid: int):
    """
    Dedicated metadata task for Auto Series Add.
    Executes with hard deadline (15s), manages exact state transitions:
    WAIT_IMDB -> FETCHING_METADATA -> METADATA_COMPLETE -> SCANNING -> RESULT / ERROR / CANCELLED.
    """
    print("### AS_FETCH_ENTERED ###", flush=True)
    try:
        s_data = temp.AUTO_SERIES.get(session_id) or temp.AUTO_SERIES.get(uid) or {}
        s_data.update({
            "session_id": session_id,
            "user_id": uid,
            "state": "FETCHING_METADATA",
            "metadata_complete": False,
            "title": None,
            "year": None,
        })
        temp.AUTO_SERIES[session_id] = s_data
        temp.AUTO_SERIES[uid] = s_data
        set_wizard_session(uid, workflow="AUTO_SERIES", state="FETCHING_METADATA", data=s_data, chat_id=chat_id)

        m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", text, re.I)
        m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)', text, re.I)

        logger.info(f"[AUTO SERIES] METADATA ROUTE\nimdb={bool(m_imdb)}\ntmdb={bool(m_tmdb)}")
        logger.info("[AUTO SERIES] METADATA TASK START")

        info = None
        is_timeout = False
        is_error = False

        try:
            if m_tmdb:
                logger.info("[AUTO SERIES] TMDB REQUEST START")
                info = await asyncio.wait_for(get_tmdb_public_metadata(text), timeout=15)
                logger.info(f"[AUTO SERIES] TMDB REQUEST DONE\ntitle={info.get('title') if info else None}\nyear={info.get('year') if info else None}")
            elif m_imdb:
                imdb_id = m_imdb.group(1).lower()
                logger.info("[AUTO SERIES] IMDb REQUEST START")
                info = await asyncio.wait_for(get_imdb_public_metadata(imdb_id), timeout=15)
                if info and info.get("title"):
                    logger.info(f"[AUTO SERIES] IMDb PUBLIC METADATA COMPLETE\ntitle={info.get('title')}\nyear={info.get('year')}\nkind={info.get('kind')}")
                else:
                    logger.warning(f"[AUTO SERIES] IMDb PUBLIC METADATA FAILED id={imdb_id}")
        except asyncio.TimeoutError:
            logger.error(f"[AUTO SERIES] METADATA TIMEOUT query={text}")
            is_timeout = True
            info = None
        except asyncio.CancelledError:
            logger.info(f"[AUTO SERIES] METADATA CANCELLED query={text}")
            s_data["state"] = "CANCELLED"
            temp.AUTO_SERIES[session_id] = s_data
            if uid:
                temp.AUTO_SERIES[uid] = s_data
            try:
                await loading_msg.edit_text("❌ <b>Auto Series Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
            return
        except Exception as e:
            logger.exception(f"[AUTO SERIES] METADATA ERROR query={text}: {e}")
            is_error = True
            info = None

        if not info or not info.get("title"):
            s_data["state"] = "ERROR"
            temp.AUTO_SERIES[session_id] = s_data
            if uid:
                temp.AUTO_SERIES[uid] = s_data
                clear_wizard_session(uid)

            retry_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Retry", callback_data="sw#start_auto"),
                    InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
                ]
            ])

            if is_timeout:
                err_text = "⚠️ <b>Series metadata timed out.</b>\n\nPlease try again."
            elif is_error:
                err_text = "❌ <b>Series metadata failed.</b>\n\nPlease try again."
            else:
                err_text = "❌ <b>Failed to fetch series data.</b>\n\nPlease try again."

            try:
                await loading_msg.edit_text(err_text, reply_markup=retry_markup, parse_mode=enums.ParseMode.HTML)
            except Exception:
                try:
                    await client.send_message(chat_id, err_text, reply_markup=retry_markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
            return

        kind = str(info.get("kind", "")).lower()
        if kind == "movie" and not info.get("seasons"):
            clear_wizard_session(uid)
            s_data["state"] = "ERROR"
            temp.AUTO_SERIES.pop(uid, None)
            try:
                await loading_msg.edit_text(
                    "⚠️ <b>This title is a Movie.</b>\n\nPlease use Auto Movie Add instead.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎬 Auto Movie Add", callback_data="sw#start_auto_movie"),
                        InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
                    ]]),
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception:
                pass
            return

        s_title = str(info["title"]).strip()
        s_year = str(info.get("year") or "").strip()
        raw_genres = info.get("genres") or "Drama"
        s_genre = ", ".join(str(g) for g in raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
        s_rating = str(info.get("rating") or "").strip()
        s_poster = info.get("poster") or ""
        s_plot = info.get("plot") or ""

        s_data.update({
            "session_id": session_id,
            "user_id": uid,
            "title": s_title,
            "year": s_year,
            "genre": s_genre,
            "rating": s_rating,
            "poster": s_poster,
            "description": s_plot,
            "metadata_complete": True,
            "state": "METADATA_COMPLETE",
        })
        temp.AUTO_SERIES[session_id] = s_data
        temp.AUTO_SERIES[uid] = s_data
        set_wizard_session(uid, workflow="AUTO_SERIES", state="METADATA_COMPLETE", data=s_data, chat_id=chat_id)

        logger.info(f"[AUTO SERIES] METADATA COMPLETE\ntitle={s_title}\nyear={s_year}")

        from database.series_db import get_series_by_name, create_series, add_series_file
        existing = await get_series_by_name(_normalize(s_title))
        if existing:
            series_id = str(existing["_id"])
        else:
            series_id = await create_series({
                "name": s_title,
                "year": s_year,
                "genre": s_genre,
                "rating": s_rating,
                "poster": s_poster,
                "description": s_plot,
                "languages": ["Malayalam", "Tamil", "Hindi", "English"],
                "seasons": [1, 2, 3] if not info.get("seasons") else list(range(1, int(info["seasons"]) + 1)),
                "qualities": ["480p", "720p", "1080p"],
                "created_by": uid
            })

        series_found_text = (
            f"📺 <b>Series Found:</b> {html.escape(str(s_title))} ({s_year})\n\n"
            f"🔍 <b>Scanning database for series episodes...</b>"
        )
        logger.info("[AUTO SERIES UI] EDIT START")
        edit_ok = await _safe_edit_message(
            loading_msg,
            series_found_text,
            parse_mode=enums.ParseMode.HTML,
            timeout=5
        )
        logger.info(f"[AUTO SERIES UI] EDIT DONE success={edit_ok}")

        logger.info("[AUTO SERIES] DB SCAN START")
        s_data["state"] = "SCANNING"
        scan_res = await scan_sdatabase_for_series(chat_id, s_title, season=None, series_id=series_id, client=client)
        logger.info("[AUTO SERIES] DB SCAN COMPLETE")
        logger.info(f"[AUTO SERIES] MATCH RESULT matched={scan_res.get('total_matched', 0)}")
        logger.info("[AUTO SERIES] FILTER SAVE")
        new_files = scan_res.get("valid_new_files") or []
        for f in new_files:
            try:
                await add_series_file({
                    "series_id": series_id,
                    "language": f["language"],
                    "season": f["season"],
                    "episode": f["episode"],
                    "quality": f["quality"],
                    "chat_id": chat_id,
                    "file_id": f.get("file_id"),
                    "file_name": f.get("file_name"),
                    "file_size": f.get("file_size", 0)
                })
            except Exception as fe:
                logger.error(f"[AUTO SERIES FILE ADD ERROR] {fe}")

        logger.info("[AUTO SERIES] FILTER VERIFY")
        logger.info(f"[AUTO SERIES COMPLETE] title={s_title} series_id={series_id} matched={scan_res.get('total_matched', 0)} new={len(new_files)}")
        clear_wizard_session(uid)

        try:
            await announce_filter_created(client, filter_type="series", filter_id=str(series_id))
        except Exception as ae:
            logger.warning(f"[AUTO SERIES ANNOUNCEMENT ERROR] {ae}")
        temp.AUTO_SERIES.pop(uid, None)

        s_data["state"] = "RESULT"
        card_text = (
            f"📺 <b>Auto Series Configured</b>\n\n"
            f"<b>{html.escape(str(s_title))}</b> ({s_year})\n"
            f"⭐ Rating: {html.escape(str(s_rating))}/10\n"
            f"🎭 Genre: {html.escape(str(s_genre))}\n\n"
            f"📁 <b>Files Scanned:</b> {scan_res.get('total_scanned', 0)}\n"
            f"✅ <b>Matching Episodes:</b> {scan_res.get('total_matched', 0)}\n"
            f"🆕 <b>New Files Added:</b> {len(new_files)}\n"
            f"⚠️ <b>Duplicates Skipped:</b> {scan_res.get('duplicates_skipped', 0)}\n\n"
            "Series is ready and searchable by users."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add More Episodes", callback_data=f"sw#sfiles:{series_id}")],
            [InlineKeyboardButton("🖼 Change Poster", callback_data=f"sw#sthumb:{series_id}")],
            [InlineKeyboardButton("🗑 Delete Series", callback_data=f"sw#sdel:{series_id}")],
            [InlineKeyboardButton("« Back to Menu", callback_data="sw#menu")]
        ])
        try:
            await loading_msg.edit_text(card_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            await client.send_message(chat_id, card_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    finally:
        AUTO_SERIES_METADATA_TASKS.pop(session_id, None)


async def _auto_movie_metadata_watchdog(client, chat_id, loading_msg, session_id):
    try:
        await asyncio.sleep(25)
        data = getattr(temp, "AUTO_MOVIE", {}).get(session_id)
        if not data:
            return
        if data.get("metadata_complete"):
            return
        try:
            await loading_msg.edit_text(
                "?? <b>Movie metadata is taking too long.</b>\n\n"
                "IMDb/TMDB did not respond in time.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("?? Retry", callback_data="sw#auto_movie"),
                        InlineKeyboardButton("? Cancel", callback_data="sw#auto_cancel")
                    ]
                ]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.warning(f"[AUTO MOVIE WATCHDOG ERROR] {e}")
AUTO_MOVIE_CANCEL_EVENTS = {}

async def run_auto_movie_scan(client, chat_id, target_msg, session_id, movie_data, is_callback=False, callback_query=None):
    """
    Unified execution helper for Auto Movie scan:
    - Session scan locking to prevent duplicate concurrent scans
    - Cancellation support via asyncio.Task and asyncio.Event
    - Guaranteed UI state transitions (WAIT_IMDB -> SCANNING -> RESULT or ERROR or CANCELLED)
    - Always releases lock in finally block
    """
    uid = movie_data.get("user_id")

    # 1. Lock check - use ONLY lock dictionary
    if session_id in AUTO_MOVIE_SCAN_LOCKS:
        logger.info(f"[AUTO MOVIE SCAN] Lock busy / already running for session={session_id}")
        if callback_query:
            return await callback_query.answer("Scan is already in progress...", show_alert=True)
        return

    AUTO_MOVIE_SCAN_LOCKS[session_id] = time.time()
    logger.info(f"[AUTO MOVIE SCAN] LOCK ACQUIRED session={session_id}")

    cancel_event = asyncio.Event()
    AUTO_MOVIE_CANCEL_EVENTS[session_id] = cancel_event
    curr_task = asyncio.current_task()
    AUTO_MOVIE_SCAN_TASKS[session_id] = curr_task

    movie_data["state"] = "SCANNING"
    temp.AUTO_MOVIE[session_id] = movie_data
    if uid:
        temp.AUTO_MOVIE[uid] = movie_data
        _log_wizard_step(uid, "AUTO_MOVIE", "WAIT_IMDB", "SCANNING")
        set_wizard_session(uid, workflow="AUTO_MOVIE", state="SCANNING", data=movie_data, chat_id=chat_id)

    rating_str = f"\n⭐ {movie_data['rating']}/10" if movie_data.get('rating') else ""
    genre_str = f"\n🎭 {movie_data['genre']}" if movie_data.get('genre') and movie_data['genre'] != "N/A" else ""

    loading_text = (
        f"🎬 <b>Movie Found</b>\n\n"
        f"<b>{movie_data['title']}</b> ({movie_data['year']})"
        f"{rating_str}"
        f"{genre_str}\n\n"
        f"🔍 <b>Scanning database for matching files...</b>"
    )

    try:
        await _safe_edit_message(target_msg, loading_text, parse_mode=enums.ParseMode.HTML, timeout=5)

        if cancel_event.is_set():
            raise asyncio.CancelledError()

        logger.info(
            f"[AUTO MOVIE SCAN] DB SCAN START title={movie_data.get('title')} year={movie_data.get('year')} imdb={movie_data.get('imdb_id')} tmdb={movie_data.get('tmdb_id')}"
        )

        try:
            res = await asyncio.wait_for(
                scan_sdatabase_for_movie(
                    chat_id,
                    movie_data["title"],
                    movie_data["year"],
                    client=client,
                    imdb_id=movie_data.get("imdb_id"),
                    tmdb_id=movie_data.get("tmdb_id")
                ),
                timeout=20
            )
        except asyncio.CancelledError:
            logger.info(f"[AUTO MOVIE SCAN] CANCELLED session={session_id}")
            movie_data["state"] = "CANCELLED"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
            await _safe_edit_message(target_msg, "❌ <b>Auto Movie Add cancelled.</b>", parse_mode=enums.ParseMode.HTML, timeout=5)
            return
        except asyncio.TimeoutError:
            logger.error(f"[AUTO MOVIE SCAN] TIMEOUT title={movie_data.get('title')} year={movie_data.get('year')}")
            movie_data["state"] = "ERROR"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
            timeout_txt = (
                "⚠️ <b>Movie file scan timed out.</b>\n\n"
                f"🎬 <b>{movie_data['title']} ({movie_data['year']})</b>\n\n"
                "The database scan took too long. Please try Rescan."
            )
            timeout_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Rescan", callback_data=f"am_rescan:{session_id}")],
                [InlineKeyboardButton("📦 Batch Add Files", callback_data=f"am_batch:{session_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"am_cancel:{session_id}")]
            ])
            edit_ok = await _safe_edit_message(target_msg, timeout_txt, reply_markup=timeout_markup, parse_mode=enums.ParseMode.HTML, timeout=5)
            if not edit_ok:
                try:
                    await client.send_message(chat_id=chat_id, text=timeout_txt, reply_markup=timeout_markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
            if callback_query:
                return await callback_query.answer("Scan timed out.", show_alert=True)
            return

        except Exception as e:
            logger.exception(f"[AUTO MOVIE SCAN] ERROR title={movie_data.get('title')} year={movie_data.get('year')} error={e}")
            movie_data["state"] = "ERROR"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
            err_txt = (
                "❌ <b>Database scan failed.</b>\n\n"
                f"🎬 <b>{movie_data['title']} ({movie_data['year']})</b>\n\n"
                f"<i>Error: {str(e)[:100]}</i>"
            )
            err_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Rescan", callback_data=f"am_rescan:{session_id}")],
                [InlineKeyboardButton("📦 Batch Add Files", callback_data=f"am_batch:{session_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"am_cancel:{session_id}")]
            ])
            edit_ok = await _safe_edit_message(target_msg, err_txt, reply_markup=err_markup, parse_mode=enums.ParseMode.HTML, timeout=5)
            if not edit_ok:
                try:
                    await client.send_message(chat_id=chat_id, text=err_txt, reply_markup=err_markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
            if callback_query:
                return await callback_query.answer("Database scan error.", show_alert=True)
            return

        if cancel_event.is_set():
            logger.info(f"[AUTO MOVIE SCAN] CANCELLED session={session_id}")
            movie_data["state"] = "CANCELLED"
            temp.AUTO_MOVIE[session_id] = movie_data
            if uid:
                temp.AUTO_MOVIE[uid] = movie_data
            await _safe_edit_message(target_msg, "❌ <b>Auto Movie Add cancelled.</b>", parse_mode=enums.ParseMode.HTML, timeout=5)
            return

        # Scan success
        logger.info(
            f"[AUTO MOVIE SCAN] DB SCAN COMPLETE matched={res.get('total_matched', 0)}"
        )
        logger.info(f"[AUTO MOVIE] MATCH RESULT matched={res.get('total_matched', 0)}")
        movie_data["scan"] = res
        movie_data["grouped"] = _group_auto_movie_files(res)
        movie_data["state"] = "RESULT"
        temp.AUTO_MOVIE[session_id] = movie_data
        if uid:
            temp.AUTO_MOVIE[uid] = movie_data
            _log_wizard_step(uid, "AUTO_MOVIE", "SCANNING", "RESULT")

        text_res = _build_auto_movie_lang_text(movie_data)
        markup = _build_auto_movie_lang_keyboard(session_id, movie_data)
        result_ok = await _safe_edit_message(target_msg, text_res, reply_markup=markup, parse_mode=enums.ParseMode.HTML, timeout=5)
        if not result_ok:
            logger.warning("[AUTO MOVIE] RESULT UI EDIT FAILED — sending fallback message")
            try:
                await asyncio.wait_for(
                    client.send_message(chat_id=chat_id, text=text_res, reply_markup=markup, parse_mode=enums.ParseMode.HTML),
                    timeout=5
                )
            except Exception as fe:
                logger.error(f"[AUTO MOVIE] FALLBACK RESULT SEND FAILED: {fe}")

        if callback_query:
            return await callback_query.answer(f"Scan complete: {res['total_matched']} files matched.")

    finally:
        AUTO_MOVIE_SCAN_LOCKS.pop(session_id, None)
        AUTO_MOVIE_SCAN_TASKS.pop(session_id, None)
        AUTO_MOVIE_CANCEL_EVENTS.pop(session_id, None)
        logger.info(f"[AUTO MOVIE SCAN] LOCK RELEASED session={session_id}")


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





# ─── Custom Font Mapping for Series Filter ───────────────────────────────────
MONOSPACE_MAP = {
    # Lowercase
    'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐',
    'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗',
    'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
    'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣',
    # Uppercase
    'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
    'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
    'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
    'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉'
}

def to_series_font(text: str) -> str:
    """
    Converts alphabetical characters to Mathematical Monospace font for Series Filter.
    Preserves HTML tags, entity references, numbers, emojis, and punctuation untouched.
    """
    if not text:
        return text

    # Split by HTML tags e.g. <...>, or HTML entities e.g. &...;
    tokens = re.split(r"(<[^>]+>|&[a-zA-Z0-9#]+;)", str(text))
    result = []
    for token in tokens:
        if token.startswith("<") and token.endswith(">"):
            result.append(token)
        elif token.startswith("&") and token.endswith(";"):
            result.append(token)
        else:
            converted = "".join(MONOSPACE_MAP.get(c, c) for c in token)
            result.append(converted)
    return "".join(result)


def _series_card(series: dict, remaining_seconds: str = None) -> str:
    """Build a formatted text card for a series with custom Series font."""
    name  = series.get("name", "?")
    year  = series.get("year", "N/A")
    genre = series.get("genre", "N/A")
    rating = series.get("rating", "")
    desc  = series.get("description", "")
    
    card = f"📺 <b>{to_series_font(name)}</b>\n\n"
    if year and year != "N/A":
        card += f"📅 <b>{to_series_font('Year')}:</b> {year}\n"
    if genre and genre != "N/A":
        card += f"🎭 <b>{to_series_font('Genre')}:</b> {to_series_font(genre)}\n"
    if rating:
        card += f"⭐ <b>{to_series_font('Rating')}:</b> {rating}\n"
    if desc:
        card += f"\n📁 {to_series_font(desc[:300])}"
    if remaining_seconds:
        card += f"\n\n⚡ <b>{to_series_font('Result Shown in')}:</b> {remaining_seconds} <i>{to_series_font('seconds')}</i>"
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
        buttons = [
            [
                InlineKeyboardButton("🌐 Edit Languages", callback_data="sw#edit#langs"),
                InlineKeyboardButton("📅 Edit Seasons", callback_data="sw#edit#seasons"),
            ],
            [
                InlineKeyboardButton("⚡ Edit Qualities", callback_data="sw#edit#quals"),
                InlineKeyboardButton("🖼 Edit Poster", callback_data="sw#edit#poster"),
            ],
            [
                InlineKeyboardButton("📁 Add Files / Resync", callback_data=f"sw#menu#batch#{series_id}"),
                InlineKeyboardButton("📢 Announcement", callback_data=f"edser#ano#{series_id}")
            ],
            [
                InlineKeyboardButton("🗑 Delete Series", callback_data=f"edser#delete#{series_id}")
            ]
        ]
    else:
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

def _user_lang_keyboard(sid: str, langs: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(langs), 2):
        row = []
        for l in langs[i:i+2]:
            row.append(InlineKeyboardButton(to_series_font(l), callback_data=f"sr#{sid}#l#{l}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _user_season_keyboard(sid: str, lang: str, seasons: list[int]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(seasons), 3):
        row = []
        for s in seasons[i:i+3]:
            label = f"{to_series_font('Season')} {s}" if s > 0 else to_series_font("Direct Episodes")
            row.append(InlineKeyboardButton(label, callback_data=f"sr#{sid}#l#{lang}#s#{s}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(f"⬅️  {to_series_font('Back')}", callback_data=f"sr#{sid}#home"),
    ])
    return InlineKeyboardMarkup(rows)


async def _user_quality_keyboard(user_id: int, full_id: str, sid: str, lang: str, season: int, quals: list[str], rating: str, is_private: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(quals), 3):
        row = []
        for q in quals[i:i+3]:
            row.append(InlineKeyboardButton(to_series_font(q), callback_data=f"sr#{sid}#l#{lang}#s#{season}#q#{q}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(f"⬅️  {to_series_font('Back')}", callback_data=f"sr#{sid}#home" if season == 0 else f"sr#{sid}#l#{lang}"),
        InlineKeyboardButton(f"🏠 {to_series_font('Home')}", callback_data=f"sr#{sid}#home"),
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


@Client.on_message(filters.command(["series"]), group=-1)
async def cmd_series_menu(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    logger.info(f"[SERIES COMMAND] user_id={uid}")

    is_authorized = _is_admin(uid)
    if not is_authorized and message.chat and message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            member = await message.chat.get_member(uid)
            if member and member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        return await message.reply_text(
            f"❌ <b>You are not authorized to use this command.</b>\n\n"
            f"Your User ID: <code>{uid}</code>\n"
            f"<i>Add this ID to ADMINS in info.py or environment variables to enable admin access.</i>",
            parse_mode=enums.ParseMode.HTML
        )

    from utils import clear_wizard_session, temp
    clear_wizard_session(uid)
    temp.AUTO_MOVIE.pop(uid, None)
    temp.AUTO_SERIES.pop(uid, None)
    temp.SERIES_WIZARD.pop(uid, None)

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Manual Adding", callback_data="sw#start_manual"),
            InlineKeyboardButton("📺 Auto S Add", callback_data="sw#start_auto")
        ],
        [
            InlineKeyboardButton("🎬 Auto Movie Add", callback_data="sw#start_auto_movie")
        ]
    ])
    await message.reply_text(
        "🎬 <b>Series & Movie Management</b>\n\nChoose an option below to proceed:",
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    )


# ─── ANNOUNCEMENT CONFIGURATION COMMANDS (/add_ano, /del_ano, /get_ano) ─────────

@Client.on_message(filters.command(["add_ano", "set_ano"]), group=-1)
async def cmd_set_announcement(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not _is_admin(uid):
        return await message.reply_text("❌ <b>You are not authorized.</b>", parse_mode=enums.ParseMode.HTML)

    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/add_ano &lt;channel_id&gt;</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/add_ano -1001234567890</code>",
            parse_mode=enums.ParseMode.HTML
        )

    raw_cid = args[1].strip()
    try:
        cid = int(raw_cid)
    except ValueError:
        cid = raw_cid

    from database.series_db import set_announcement_channel
    await set_announcement_channel(cid)
    logger.info(f"[ANNOUNCEMENT CONFIG] Channel set to {cid} by {uid}")

    await message.reply_text(
        f"✅ <b>Announcement channel configured successfully!</b>\n\n"
        f"📢 Channel ID: <code>{cid}</code>",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["del_ano", "rem_ano"]), group=-1)
async def cmd_del_announcement(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not _is_admin(uid):
        return await message.reply_text("❌ <b>You are not authorized.</b>", parse_mode=enums.ParseMode.HTML)

    from database.series_db import delete_announcement_channel
    await delete_announcement_channel()
    logger.info(f"[ANNOUNCEMENT CONFIG] Channel deleted by {uid}")

    await message.reply_text(
        "✅ <b>Announcement channel setting removed.</b>",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["get_ano", "ano_channel"]), group=-1)
async def cmd_get_announcement(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not _is_admin(uid):
        return await message.reply_text("❌ <b>You are not authorized.</b>", parse_mode=enums.ParseMode.HTML)

    from database.series_db import get_announcement_channel
    cid = await get_announcement_channel()
    if cid:
        await message.reply_text(
            f"📢 <b>Current Announcement Channel:</b> <code>{cid}</code>",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            "⚠️ <b>Announcement channel is not configured.</b>\n\n"
            "Use <code>/add_ano &lt;channel_id&gt;</code> to set one.",
            parse_mode=enums.ParseMode.HTML
        )


@Client.on_message(filters.command(["sync_movies", "resync_movies"]), group=-1)
async def cmd_sync_movies(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not _is_admin(uid):
        return await message.reply_text("❌ <b>You are not authorized.</b>", parse_mode=enums.ParseMode.HTML)

    status_msg = await message.reply_text("🔄 <b>Synchronizing all Super Movie filters with database...</b>", parse_mode=enums.ParseMode.HTML)
    from database.series_db import super_movies_col, sync_existing_movie_filter
    cursor = super_movies_col.find({"status": {"$ne": "deleted"}})
    movies = [doc async for doc in cursor]

    synced = 0
    total_added = 0
    for m in movies:
        mid = str(m["_id"])
        res = await sync_existing_movie_filter(mid)
        if res.get("success"):
            synced += 1
            total_added += res.get("new_files_added", 0)

    await status_msg.edit_text(
        f"✅ <b>Movie Filter Sync Complete!</b>\n\n"
        f"🎬 <b>Movies Synced:</b> <code>{synced}/{len(movies)}</code>\n"
        f"📁 <b>New Files Linked:</b> <code>{total_added}</code>",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(["sync_series", "resync_series"]), group=-1)
async def cmd_sync_series(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if not _is_admin(uid):
        return await message.reply_text("❌ <b>You are not authorized.</b>", parse_mode=enums.ParseMode.HTML)

    status_msg = await message.reply_text("🔄 <b>Synchronizing all Series filters with database...</b>", parse_mode=enums.ParseMode.HTML)
    from database.series_db import series_col, scan_sdatabase_for_series, add_series_file
    cursor = series_col.find({"status": {"$ne": "deleted"}})
    series_list = [doc async for doc in cursor]

    synced = 0
    total_added = 0
    for s in series_list:
        sid = str(s["_id"])
        name = s.get("name", "")
        res = await scan_sdatabase_for_series(message.chat.id, name, season=None, series_id=sid, client=client)
        new_files = res.get("valid_new_files") or []
        for f in new_files:
            try:
                await add_series_file({
                    "series_id": sid,
                    "language": f["language"],
                    "season": f["season"],
                    "episode": f["episode"],
                    "quality": f["quality"],
                    "chat_id": message.chat.id,
                    "file_id": f.get("file_id"),
                    "file_name": f.get("file_name"),
                    "file_size": f.get("file_size", 0)
                })
                total_added += 1
            except Exception:
                pass
        synced += 1

    await status_msg.edit_text(
        f"✅ <b>Series Filter Sync Complete!</b>\n\n"
        f"📺 <b>Series Synced:</b> <code>{synced}/{len(series_list)}</code>\n"
        f"📁 <b>New Episodes Linked:</b> <code>{total_added}</code>",
        parse_mode=enums.ParseMode.HTML
    )


async def announce_filter_created(client: Client, filter_type: str = "series", filter_id: str = None, force: bool = False) -> bool:
    """
    Sends an announcement message/photo to the configured announcement channel.
    Tracks sent state to avoid duplicate broadcasts unless force=True.
    """
    from database.series_db import (
        get_announcement_channel,
        is_announcement_sent,
        save_announcement,
        get_series,
        get_super_movie,
        list_series_languages,
        series_col,
        super_movies_col
    )
    from bson import ObjectId

    if not filter_id:
        return False

    channel_id = await get_announcement_channel()
    if not channel_id:
        logger.warning(f"[ANNOUNCEMENT] Channel not configured for {filter_type}:{filter_id}")
        return False

    ann_key = f"{filter_type}:{filter_id}"
    if not force and await is_announcement_sent(ann_key, filter_type=filter_type, filter_id=str(filter_id)):
        logger.info(f"[ANNOUNCEMENT SKIPPED] Already sent for {ann_key}")
        return True

    bot_username = temp.U_NAME if (hasattr(temp, "U_NAME") and temp.U_NAME) else getattr(getattr(client, "me", None), "username", None)
    if bot_username:
        bot_username = str(bot_username).lstrip("@")
    else:
        bot_username = "Bot"

    try:
        if filter_type == "series":
            series = await get_series(filter_id)
            if not series:
                try:
                    series = await series_col.find_one({"_id": ObjectId(filter_id)})
                except Exception:
                    pass
            if not series:
                logger.warning(f"[ANNOUNCEMENT] Series not found id={filter_id}")
                return False

            name = series.get("name", "Series")
            year = str(series.get("year", ""))
            year_str = f" ({year})" if year and year != "N/A" else ""
            rating = str(series.get("rating", ""))
            rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
            genre = series.get("genre", "")
            genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
            poster = series.get("poster")

            langs = await list_series_languages(str(filter_id))
            if not langs:
                langs = series.get("languages", [])
            lang_str = ", ".join(langs) if langs else "All Languages"

            seasons = series.get("seasons", [])
            if isinstance(seasons, list) and seasons:
                season_str = ", ".join(f"Season {s}" for s in sorted(seasons) if str(s).isdigit())
            else:
                season_str = "Season 1"

            import urllib.parse
            search_query_enc = urllib.parse.quote_plus(name)
            buttons = [
                [
                    InlineKeyboardButton("🔍 Search Series", url=f"https://t.me/{bot_username}?start=search_{search_query_enc}"),
                    InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{bot_username}")
                ]
            ]
            markup = InlineKeyboardMarkup(buttons)

            caption = (
                f"📢 <b>NEW SERIES ADDED!</b> 🎬\n\n"
                f"📺 <b>Title:</b> <code>{html.escape(name)}{year_str}</code>"
                f"{rating_str}"
                f"{genre_str}\n"
                f"🌐 <b>Languages:</b> <code>{html.escape(lang_str)}</code>\n"
                f"🎞 <b>Available:</b> <code>{html.escape(season_str)}</code>\n\n"
                f"<blockquote>⚡ <b>Search in bot or group to download!</b></blockquote>\n\n"
                f"@{bot_username}"
            )

        elif filter_type == "movie":
            movie = await get_super_movie(filter_id)
            if not movie:
                try:
                    movie = await super_movies_col.find_one({"_id": ObjectId(filter_id)})
                except Exception:
                    pass
            if not movie:
                logger.warning(f"[ANNOUNCEMENT] Movie not found id={filter_id}")
                return False

            title = movie.get("title", "Movie")
            year = str(movie.get("year", ""))
            year_str = f" ({year})" if year and year != "N/A" else ""
            rating = str(movie.get("rating", ""))
            rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
            genre = movie.get("genre", "")
            genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
            poster = movie.get("poster")
            langs = movie.get("languages", [])
            lang_str = ", ".join(langs) if langs else "Multi"
            qualities = movie.get("qualities", [])
            qual_str = ", ".join(qualities) if qualities else "1080p, 720p, 480p"

            import urllib.parse
            search_query_enc = urllib.parse.quote_plus(f"{title} {year}".strip() if year and year != "N/A" else title)
            buttons = [
                [
                    InlineKeyboardButton("🎬 Search Movie", url=f"https://t.me/{bot_username}?start=search_{search_query_enc}"),
                    InlineKeyboardButton("🤖 Open Bot", url=f"https://t.me/{bot_username}")
                ]
            ]
            markup = InlineKeyboardMarkup(buttons)

            caption = (
                f"📢 <b>NEW MOVIE ADDED!</b> 🎬\n\n"
                f"🎬 <b>Title:</b> <code>{html.escape(title)}{year_str}</code>"
                f"{rating_str}"
                f"{genre_str}\n"
                f"🌐 <b>Languages:</b> <code>{html.escape(lang_str)}</code>\n"
                f"⚡ <b>Qualities:</b> <code>{html.escape(qual_str)}</code>\n\n"
                f"<blockquote>⚡ <b>Search in bot or group to download!</b></blockquote>\n\n"
                f"@{bot_username}"
            )
        else:
            return False

        # Send to channel
        sent_msg = None
        cid_int = int(channel_id) if str(channel_id).lstrip("-").isdigit() else str(channel_id)

        if poster:
            try:
                sent_msg = await client.send_photo(
                    chat_id=cid_int,
                    photo=poster,
                    caption=caption,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception as pe:
                logger.warning(f"[ANNOUNCEMENT PHOTO FAILED] {pe} - falling back to text")

        if not sent_msg:
            sent_msg = await client.send_message(
                chat_id=cid_int,
                text=caption,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML
            )

        if sent_msg:
            await save_announcement(
                filter_id=str(filter_id),
                channel_id=cid_int,
                message_id=sent_msg.id,
                filter_type=filter_type
            )
            logger.info(f"[ANNOUNCEMENT SENT SUCCESS] type={filter_type} filter_id={filter_id} msg_id={sent_msg.id}")
            return True
        return False
    except Exception as e:
        logger.exception(f"[ANNOUNCEMENT BROADCAST ERROR] {e}")
        return False



# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  
# ─── /viewseries & /viewmovies —” FILTER MANAGERS ──────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═  

async def send_filter_manager(query_or_message, ftype: str = "series", page: int = 0):
    """
    Renders the Series / Super Movie Filter Manager without any close button.
    Supports tab switching and pagination.
    """
    from database.series_db import series_col, super_movies_col
    from pyrogram.types import CallbackQuery

    series_count = await series_col.count_documents({"status": {"$ne": "deleted"}})
    movies_count = await super_movies_col.count_documents({"status": {"$ne": "deleted"}})

    tab_row = [
        InlineKeyboardButton(
            f"📺 Series ({series_count})" if ftype == "series" else f"Series ({series_count})",
            callback_data="vser#ser#0"
        ),
        InlineKeyboardButton(
            f"🎬 Movies ({movies_count})" if ftype == "movies" else f"Movies ({movies_count})",
            callback_data="vser#mov#0"
        )
    ]
    rows = [tab_row]
    page_size = 8

    if ftype == "series":
        cursor = series_col.find({"status": {"$ne": "deleted"}}).sort("created_at", -1).skip(page * page_size).limit(page_size)
        items = [doc async for doc in cursor]
        total_items = series_count

        for s in items:
            s_name = s.get("name", "Series")
            s_id = str(s["_id"])
            rows.append([
                InlineKeyboardButton(
                    f"📺 {s_name}",
                    callback_data=f"edser#{s_id}"
                )
            ])

        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"vser#ser#{page - 1}"))
        if (page + 1) * page_size < total_items:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"vser#ser#{page + 1}"))
        if nav_row:
            rows.append(nav_row)

        header_text = (
            "📺 <b>SERIES FILTER MANAGER</b>\n\n"
            f"Total Series: <b>{series_count}</b> (Page {page + 1})\n"
            "Select a series below to view/edit:"
        )

    else:
        cursor = super_movies_col.find({"status": {"$ne": "deleted"}}).sort("created_at", -1).skip(page * page_size).limit(page_size)
        items = [doc async for doc in cursor]
        total_items = movies_count

        for m in items:
            m_title = m.get("title", "Movie")
            m_year = m.get("year", "")
            m_id = str(m["_id"])
            label = f"🎬 {m_title} ({m_year})" if m_year and m_year != "N/A" else f"🎬 {m_title}"
            rows.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"emovie_select#{m_id}"
                )
            ])

        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"vser#mov#{page - 1}"))
        if (page + 1) * page_size < total_items:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"vser#mov#{page + 1}"))
        if nav_row:
            rows.append(nav_row)

        header_text = (
            "🎬 <b>MOVIE FILTER MANAGER</b>\n\n"
            f"Total Movies: <b>{movies_count}</b> (Page {page + 1})\n"
            "Select a movie below to view/edit:"
        )

    markup = InlineKeyboardMarkup(rows)

    if isinstance(query_or_message, CallbackQuery):
        try:
            await query_or_message.message.edit_text(header_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
    else:
        await query_or_message.reply_text(header_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command(["viewseries", "view_series", "serieslist"]), group=-1)
async def cmd_view_series(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    is_authorized = _is_admin(uid)
    if not is_authorized and message.chat and message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            member = await message.chat.get_member(uid)
            if member and member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                is_authorized = True
        except Exception:
            pass
    if not is_authorized:
        return await message.reply_text("❌ <b>You are not authorized to use this command.</b>", parse_mode=enums.ParseMode.HTML)

    from database.series_db import series_col
    count = await series_col.count_documents({"status": {"$ne": "deleted"}})
    if count == 0:
        logger.info("[VIEW FILTERS EMPTY]\ntype=series")
    else:
        logger.info(f"[VIEW SERIES]\nuser_id={uid}\ncount={count}")

    await send_filter_manager(message, ftype="series", page=0)


@Client.on_message(filters.command(["viewmovies", "view_movies", "movieslist", "movielist"]), group=-1)
async def cmd_view_movies(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    is_authorized = _is_admin(uid)
    if not is_authorized and message.chat and message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            member = await message.chat.get_member(uid)
            if member and member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                is_authorized = True
        except Exception:
            pass
    if not is_authorized:
        return await message.reply_text("❌ <b>You are not authorized to use this command.</b>", parse_mode=enums.ParseMode.HTML)

    from database.series_db import super_movies_col
    count = await super_movies_col.count_documents({"status": {"$ne": "deleted"}})
    if count == 0:
        logger.info("[VIEW FILTERS EMPTY]\ntype=movie")
    else:
        logger.info(f"[VIEW MOVIES]\nuser_id={uid}\ncount={count}")

    await send_filter_manager(message, ftype="movies", page=0)


@Client.on_callback_query(filters.regex(r"^vser#"))
async def cb_vser(client: Client, query: CallbackQuery):
    await query.answer()
    parts = query.data.split("#")
    if len(parts) >= 3:
        ftype = "series" if parts[1] == "ser" else "movies"
        try:
            page = int(parts[2])
        except ValueError:
            page = 0
        return await send_filter_manager(query, ftype=ftype, page=page)


@Client.on_callback_query(filters.regex(r"^edser#"))
async def cb_edser(client: Client, query: CallbackQuery):
    try:
        await query.answer("Opening Series...")
    except Exception:
        pass

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
    from database.series_db import get_series, delete_series_filter, delete_announcement, series_col
    from bson import ObjectId

    if query.data.startswith("edser#ano#"):
        series_id = query.data.split("#")[2]
        exact = await get_series(series_id)
        if not exact:
            return await query.answer("❌ Series not found.", show_alert=True)
        channel_id = await get_announcement_channel()
        if not channel_id:
            return await query.message.reply_text(
                "⚠️ <b>Announcement channel is not configured.</b>\n\n"
                "Use:\n<code>/add_ano &lt;channel_id&gt;</code>",
                parse_mode=enums.ParseMode.HTML
            )
        logger.info(f"[MANUAL ANNOUNCEMENT]\ntype=series\nfilter_id={series_id}")
        try:
            success = await announce_filter_created(client, filter_type="series", filter_id=str(series_id), force=True)
            if success:
                logger.info(f"[MANUAL ANNOUNCEMENT SUCCESS]\ntype=series\nfilter_id={series_id}\nchannel={channel_id}")
                await query.answer("📢 Series announcement sent successfully!", show_alert=True)
                await query.message.reply_text(
                    "✅ <b>Series announcement sent successfully.</b>",
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await query.answer("❌ Failed to send announcement.", show_alert=True)
        except Exception as e:
            logger.error(f"[MANUAL ANNOUNCEMENT ERROR]\ntype=series\nfilter_id={series_id}\nerror={e}")
            await query.answer(f"❌ Error: {e}", show_alert=True)
        return

    if query.data.startswith("edser#delete#"):
        series_id = query.data.split("#")[2]
        exact = await get_series(series_id)
        if not exact:
            return await query.answer("❌ Series not found.", show_alert=True)
        series_name = exact.get("name", "Unknown Series")
        confirm_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Delete", callback_data=f"edser#delete_confirm#{series_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"edser#delete_cancel#{series_id}")]
        ])
        return await query.message.edit_text(
            f"⚠️ <b>Delete Series Filter?</b>\n\n"
            f"🎬 <b>{series_name}</b>\n\n"
            f"This will remove the Series Filter.",
            reply_markup=confirm_markup,
            parse_mode=enums.ParseMode.HTML
        )

    if query.data.startswith("edser#delete_cancel#"):
        series_id = query.data.split("#")[2]
        exact = await get_series(series_id)
        if not exact:
            return await query.answer("❌ Series not found.", show_alert=True)
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
        await query.message.edit_text(
            _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
            reply_markup=_config_menu_keyboard(series_id, True),
            parse_mode=enums.ParseMode.HTML,
        )
        return await query.answer("Deletion cancelled.")

    if query.data.startswith("edser#delete_confirm#"):
        series_id = query.data.split("#")[2]
        logger.info(f"[DELETE SERIES]\nseries_id={series_id}\nuser_id={uid}")
        exact = await get_series(series_id)
        series_name = exact.get("name", "Unknown Series") if exact else "Series"
        await delete_series_filter(series_id)
        try:
            await delete_announcement(f"series:{series_id}")
            await delete_announcement(str(series_id))
        except Exception:
            pass
        temp.SERIES_WIZARD.pop(uid, None)
        logger.info(f"[DELETE SERIES SUCCESS]\nseries_id={series_id}")
        await query.answer("✅ Series Filter Deleted\n📁 Original files were preserved.", show_alert=True)
        return await send_filter_manager(query, ftype="series", page=0)

    parts = query.data.split("#")
    series_id = parts[-1].strip()
    if not series_id:
        return await query.answer("❌ Invalid Series ID.", show_alert=True)

    exact = await get_series(series_id)
    if not exact and ObjectId.is_valid(series_id):
        try:
            exact = await series_col.find_one({"_id": ObjectId(series_id)})
        except Exception:
            pass

    if not exact:
        return await query.answer("❌ Series not found. Please refresh /viewseries.", show_alert=True)

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
    logger.info(
        f"[VIEW FILTER CLICK]\n"
        f"type=series\n"
        f"filter_id={series_id}\n"
        f"user_id={uid}\n\n"
        f"[VIEW FILTER OPEN]\n"
        f"type=series\n"
        f"filter_id={series_id}\n"
        f"name={exact.get('name')}"
    )

    await query.message.edit_text(
        _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
        reply_markup=_config_menu_keyboard(wiz.get("series_id"), True),
        parse_mode=enums.ParseMode.HTML,
    )


@Client.on_callback_query(filters.regex(r"^(?:emovie_select|edmov|emov)#"))
async def cb_movie_management(client: Client, query: CallbackQuery):
    try:
        await query.answer("Opening Movie...")
    except Exception:
        pass

    uid = query.from_user.id
    is_admin = False
    if query.message and query.message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        admin_list = await client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
        is_admin = any(admin.user.id == query.from_user.id for admin in admin_list if admin.user)
    else:
        is_admin = query.from_user.id in ADMINS
    if not is_admin:
        return await query.answer("❌ You are not authorized.", show_alert=True)

    data = query.data
    from database.series_db import super_movies_col, get_super_movie, sync_existing_movie_filter, delete_announcement
    from bson import ObjectId

    if data == "emov#back":
        logger.info(f"[VIEW FILTER BACK]\ntype=movie\nuser_id={uid}")
        return await send_filter_manager(query, ftype="movies", page=0)

    if data.startswith("emov#ano#"):
        movie_id = data.split("#")[2]
        success = await announce_filter_created(client, filter_type="movie", filter_id=str(movie_id), force=True)
        if success:
            await query.answer("📢 Movie announcement sent successfully!", show_alert=True)
        else:
            await query.answer("❌ Failed to send announcement or channel not configured.", show_alert=True)
        return

    if data.startswith("emov#sync#"):
        movie_id = data.split("#")[2]
        await query.message.edit_text("🔄 <b>Synchronizing files for this movie from database...</b>", parse_mode=enums.ParseMode.HTML)
        res = await sync_existing_movie_filter(movie_id)
        if res.get("success"):
            await query.answer(f"✅ Synced {res.get('new_files_added', 0)} new files!", show_alert=True)
        else:
            await query.answer("⚠️ No new files found to sync.", show_alert=True)
        data = f"emovie_select#{movie_id}"

    if data.startswith("emov#del#"):
        movie_id = data.split("#")[2]
        movie = await get_super_movie(movie_id)
        if not movie:
            return await query.answer("❌ Movie not found.", show_alert=True)
        title = movie.get("title", "Movie")
        year = movie.get("year", "")
        confirm_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Delete", callback_data=f"emov#del_confirm#{movie_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"emovie_select#{movie_id}")]
        ])
        return await query.message.edit_text(
            f"⚠️ <b>Delete Movie Filter?</b>\n\n"
            f"🎬 <b>{html.escape(title)} ({year})</b>\n\n"
            f"This will remove the Super Movie Filter. Original files are preserved.",
            reply_markup=confirm_markup,
            parse_mode=enums.ParseMode.HTML
        )

    if data.startswith("emov#edit_poster#"):
        movie_id = data.split("#")[2]
        from utils import set_wizard_session
        set_wizard_session(uid, workflow="MOVIE_EDIT_POSTER", state="WAIT_POSTER", data={"movie_id": movie_id}, chat_id=query.message.chat.id)
        return await query.message.edit_text(
            "🖼 <b>Edit Movie Poster</b>\n\nPlease send the <b>new Poster Photo or URL</b>:\n(or click Cancel to return)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"emovie_select#{movie_id}")]]),
            parse_mode=enums.ParseMode.HTML
        )

    if data.startswith("emov#del_confirm#"):
        movie_id = data.split("#")[2]
        await super_movies_col.update_one(
            {"_id": ObjectId(movie_id)},
            {"$set": {"status": "deleted", "updated_at": datetime.utcnow()}}
        )
        try:
            await delete_announcement(f"movie:{movie_id}")
            await delete_announcement(str(movie_id))
        except Exception:
            pass
        await query.answer("✅ Movie Filter Deleted", show_alert=True)
        return await send_filter_manager(query, ftype="movies", page=0)

    # View movie detail card
    parts = data.split("#")
    movie_id = parts[-1].strip()
    movie = await get_super_movie(movie_id)
    if not movie and ObjectId.is_valid(movie_id):
        try:
            movie = await super_movies_col.find_one({"_id": ObjectId(movie_id)})
        except Exception:
            pass

    if not movie:
        return await query.answer("❌ Movie not found. Please refresh /viewmovies.", show_alert=True)

    title = movie.get("title", "Movie")
    year = str(movie.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = str(movie.get("rating", ""))
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = movie.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
    langs = movie.get("languages", [])
    lang_str = ", ".join(langs) if langs else "Multi"
    quals = movie.get("qualities", [])
    qual_str = ", ".join(quals) if quals else "1080p, 720p, 480p"
    tot_files = len(movie.get("file_ids") or [])

    logger.info(
        f"[VIEW FILTER CLICK]\n"
        f"type=movie\n"
        f"filter_id={movie_id}\n"
        f"user_id={uid}\n\n"
        f"[VIEW FILTER OPEN]\n"
        f"type=movie\n"
        f"filter_id={movie_id}\n"
        f"name={title}"
    )

    card_text = (
        f"🎬 <b>Movie Filter Configuration</b>\n\n"
        f"🎬 <b>Title:</b> <code>{html.escape(title)}{year_str}</code>"
        f"{rating_str}"
        f"{genre_str}\n"
        f"🌐 <b>Languages:</b> <code>{html.escape(lang_str)}</code>\n"
        f"⚡ <b>Qualities:</b> <code>{html.escape(qual_str)}</code>\n"
        f"📁 <b>Linked Files:</b> {tot_files}\n"
        f"<i>ID: <code>{movie_id}</code></i>"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Add Files / Resync", callback_data=f"emov#sync#{movie_id}"),
            InlineKeyboardButton("📢 Announcement", callback_data=f"emov#ano#{movie_id}")
        ],
        [
            InlineKeyboardButton("🖼 Edit Poster", callback_data=f"emov#edit_poster#{movie_id}"),
            InlineKeyboardButton("🗑 Delete Movie", callback_data=f"emov#del#{movie_id}")
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="emov#back")
        ]
    ])

    await query.message.edit_text(card_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)





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

@Client.on_message(filters.command("cancel"), group=-1)
async def cmd_cancel(client: Client, message: Message):
    uid = message.from_user.id if message.from_user else 0

    # 1. Cancel any active metadata tasks for this user
    for sess_id, t in list(AUTO_MOVIE_METADATA_TASKS.items()):
        m_data = getattr(temp, "AUTO_MOVIE", {}).get(sess_id, {})
        if m_data.get("user_id") == uid or m_data.get("admin_id") == uid:
            if t and not t.done():
                t.cancel()
            AUTO_MOVIE_METADATA_TASKS.pop(sess_id, None)

    for sess_id, t in list(AUTO_SERIES_METADATA_TASKS.items()):
        s_data = getattr(temp, "AUTO_SERIES", {}).get(sess_id, {})
        if s_data.get("user_id") == uid or s_data.get("admin_id") == uid:
            if t and not t.done():
                t.cancel()
            AUTO_SERIES_METADATA_TASKS.pop(sess_id, None)

    # 2. Cancel any active running Auto Movie scans for this user
    for sess_id, t in list(AUTO_MOVIE_SCAN_TASKS.items()):
        m_data = getattr(temp, "AUTO_MOVIE", {}).get(sess_id, {})
        if m_data.get("user_id") == uid or m_data.get("admin_id") == uid:
            ev = AUTO_MOVIE_CANCEL_EVENTS.get(sess_id)
            if ev:
                ev.set()
            if t and not t.done():
                t.cancel()
            AUTO_MOVIE_SCAN_TASKS.pop(sess_id, None)

    workflow = cancel_wizard_session(uid)
    clear_wizard_session(uid)
    logger.info(f"[WIZARD CANCEL] user_id={uid} workflow={workflow}")

    if workflow == "AUTO_MOVIE" or uid in getattr(temp, "AUTO_MOVIE", {}):
        temp.AUTO_MOVIE.pop(uid, None)
        return await message.reply_text("❌ <b>Auto Movie Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)
    elif workflow in ("AUTO_SERIES", "SERIES_WIZARD") or uid in getattr(temp, "AUTO_SERIES", {}):
        temp.AUTO_SERIES.pop(uid, None)
        temp.SERIES_WIZARD.pop(uid, None)
        return await message.reply_text("❌ <b>Auto Series Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)
    elif workflow == "THUMBNAIL":
        return await message.reply_text("❌ <b>Series thumbnail update cancelled.</b>", parse_mode=enums.ParseMode.HTML)
    elif workflow:
        return await message.reply_text("❌ <b>Action cancelled.</b>", parse_mode=enums.ParseMode.HTML)
    else:
        return await message.reply_text("No active wizard or session to cancel.")


# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── TEXT HANDLER — WIZARD STEPS ─────────────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 

async def _is_in_wizard_session_filter(_, __, message: Message) -> bool:
    if not message.from_user:
        return False
    from utils import get_wizard_session, temp
    uid = message.from_user.id
    if get_wizard_session(uid) is not None:
        return True
    if (uid in getattr(temp, "AUTO_SERIES", {}) or 
        uid in getattr(temp, "AUTO_MOVIE", {}) or 
        uid in getattr(temp, "SERIES_WIZARD", {}) or
        uid in getattr(temp, "AUTO_MOVIE_BATCH", {}) or
        getattr(temp, "SETTING_SERIES_THUMB", {}).get(uid)):
        return True
    return False

wizard_filter = filters.create(_is_in_wizard_session_filter)


def _log_wizard_step(user_id: int, workflow: str, old_state: str, new_state: str):
    log_str = (
        f"[WIZARD STEP]\n"
        f"user_id={user_id}\n"
        f"workflow={workflow}\n"
        f"old_state={old_state}\n"
        f"new_state={new_state}"
    )
    print(log_str, flush=True)
    logger.info(log_str)


def _log_wizard_prompt(user_id: int, workflow: str, state: str, message_id: int):
    log_str = (
        f"[WIZARD PROMPT]\n"
        f"user_id={user_id}\n"
        f"workflow={workflow}\n"
        f"state={state}\n"
        f"message_id={message_id}"
    )
    print(log_str, flush=True)
    logger.info(log_str)


@Client.on_message(
    (filters.text | filters.photo) & wizard_filter,
    group=-10
)
async def wizard_text_handler(client: Client, message: Message):
    text = message.text.strip() if message.text else ""

    # If it is any slash command (except /skip for wizards), allow normal command handlers to process it!
    if text and text.startswith("/"):
        if not text.lower().startswith("/skip"):
            return

    try:
        message.stop_propagation()
    except Exception:
        pass

    uid = message.from_user.id if message.from_user else 0
    chat_id = message.chat.id if message.chat else uid

    from utils import get_wizard_session, clear_wizard_session, set_wizard_session, temp

    sess = get_wizard_session(uid)
    # Fallback session support
    if not sess:
        if getattr(temp, "AUTO_SERIES", {}).get(uid):
            sess = {"user_id": uid, "workflow": "AUTO_SERIES", "state": temp.AUTO_SERIES[uid].get("state", "WAIT_IMDB"), "data": temp.AUTO_SERIES[uid]}
        elif getattr(temp, "AUTO_MOVIE", {}).get(uid):
            sess = {"user_id": uid, "workflow": "AUTO_MOVIE", "state": temp.AUTO_MOVIE[uid].get("state", "WAIT_IMDB"), "data": temp.AUTO_MOVIE[uid]}
        elif getattr(temp, "SERIES_WIZARD", {}).get(uid):
            sess = {"user_id": uid, "workflow": "SERIES_WIZARD", "state": temp.SERIES_WIZARD[uid].get("state", S_NAME), "data": temp.SERIES_WIZARD[uid]}
        elif getattr(temp, "AUTO_MOVIE_BATCH", {}).get(uid):
            sess = {"user_id": uid, "workflow": "SUPER_MOVIE_BATCH", "state": temp.AUTO_MOVIE_BATCH[uid].get("state", "WAIT_INPUT"), "data": temp.AUTO_MOVIE_BATCH[uid]}

    if not sess:
        return

    workflow = sess.get("workflow")
    state = sess.get("state")
    log_input = (
        f"[WIZARD INPUT]\n"
        f"user_id={uid}\n"
        f"workflow={workflow}\n"
        f"state={state}\n"
        f"text={text}"
    )
    print(log_input, flush=True)
    logger.info(log_input)
    # ── Auto Movie Add IMDb/TMDB Input Handler ─────────────────────────────────
    if workflow == "AUTO_MOVIE":
        movie_data = sess.get("data") or temp.AUTO_MOVIE.get(uid, {})
        if sess.get("state") in ("WAIT_IMDB", "FETCHING_METADATA") or movie_data.get("state") in ("WAIT_IMDB", "FETCHING_METADATA"):
            m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", text, re.I)
            m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)', text, re.I)

            if not m_imdb and not m_tmdb:
                prompt_msg_id = movie_data.get("prompt_msg_id") or movie_data.get("prompt_message_id")
                try:
                    await message.delete()
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        await client.delete_messages(chat_id, prompt_msg_id)
                    except Exception:
                        pass
                pmsg = await client.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ <b>Invalid IMDb or TMDB URL.</b>\n\n"
                        "Please send:\n\n"
                        "<b>IMDb Movie:</b>\n"
                        "<code>https://www.imdb.com/title/tt11948256/</code> or <code>tt11948256</code>\n\n"
                        "<b>TMDB Movie:</b>\n"
                        "<code>https://www.themoviedb.org/movie/863530</code>"
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")
                    ]]),
                    parse_mode=enums.ParseMode.HTML
                )
                movie_data["prompt_msg_id"] = pmsg.id if pmsg else None
                movie_data["prompt_message_id"] = pmsg.id if pmsg else None
                return

            prompt_msg_id = movie_data.get("prompt_msg_id") or movie_data.get("prompt_message_id")
            try:
                await message.delete()
            except Exception:
                pass

            if prompt_msg_id:
                try:
                    await client.delete_messages(chat_id, prompt_msg_id)
                except Exception:
                    pass

            logger.info(f"[AUTO MOVIE INPUT]\ntext={text}")
            loading_msg = await client.send_message(
                chat_id=chat_id,
                text=(
                    "🔎 <b>Processing Movie Data...</b>\n\n"
                    f"Query:\n<code>{text}</code>\n\n"
                    "Please wait..."
                ),
                parse_mode=enums.ParseMode.HTML
            )
            print("### AM_STEP_01_PROCESSING_SENT ###", flush=True)
            logger.info("[AUTO MOVIE] PROCESSING MESSAGE SENT")

            import uuid
            session_id = str(uuid.uuid4())[:8]

            task = asyncio.create_task(
                fetch_auto_movie_metadata(
                    client,
                    chat_id,
                    loading_msg,
                    session_id,
                    text,
                    uid
                )
            )
            AUTO_MOVIE_METADATA_TASKS[session_id] = task

            def _done_movie_cb(t):
                AUTO_MOVIE_METADATA_TASKS.pop(session_id, None)

            task.add_done_callback(_done_movie_cb)
            task.add_done_callback(_log_background_task_result)

            print("### AM_TASK_CREATED ###", flush=True)
            logger.info("[AUTO MOVIE] METADATA TASK CREATED")
            return

    # ── Auto Series Add Handler ──────────────────────────────────────────────
    elif workflow == "AUTO_SERIES":
        s_data = sess.get("data") or temp.AUTO_SERIES.get(uid, {})
        m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", text, re.I)
        m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)', text, re.I)

        if not m_imdb and not m_tmdb:
            return await message.reply_text(
                "❌ <b>Invalid IMDb or TMDB URL.</b>\n\n"
                "Please send a valid Series URL or ID.\n\n"
                "Example:\n<code>https://www.imdb.com/title/tt9288030/</code> or <code>tt9288030</code>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]]),
                parse_mode=enums.ParseMode.HTML
            )

        logger.info(f"[AUTO SERIES INPUT]\ntext={text}")
        loading_msg = await message.reply_text(
            "🔎 <b>Processing Series Data...</b>\n\n"
            f"Query:\n<code>{text}</code>\n\n"
            "Please wait...",
            parse_mode=enums.ParseMode.HTML
        )
        print("### AS_STEP_01_PROCESSING_SENT ###", flush=True)
        logger.info("[AUTO SERIES] PROCESSING MESSAGE SENT")

        import uuid
        session_id = str(uuid.uuid4())[:8]

        task = asyncio.create_task(
            fetch_auto_series_metadata(
                client,
                chat_id,
                loading_msg,
                session_id,
                text,
                uid
            )
        )
        AUTO_SERIES_METADATA_TASKS[session_id] = task

        def _done_series_cb(t):
            AUTO_SERIES_METADATA_TASKS.pop(session_id, None)

        task.add_done_callback(_done_series_cb)
        task.add_done_callback(_log_background_task_result)

        print("### AS_TASK_CREATED ###", flush=True)
        logger.info("[AUTO SERIES] METADATA TASK CREATED")
        return

    # ── Manual Series Wizard Handler ─────────────────────────────────────────
    elif workflow == "SERIES_WIZARD":
        wiz = temp.SERIES_WIZARD.get(uid) or sess.get("data", {})
        cur_state = wiz.get("state", S_NAME)

        if cur_state == S_NAME:
            wiz["name"] = text
            wiz["state"] = S_YEAR
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_YEAR, data=wiz, chat_id=chat_id)
            _log_wizard_step(uid, "SERIES_WIZARD", S_NAME, S_YEAR)
            return await message.reply_text(
                f"Series Name: <b>{html.escape(text)}</b>\n\nPlease send the <b>Release Year</b> (e.g. <code>2021</code>) or /skip:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel")]]),
                parse_mode=enums.ParseMode.HTML
            )
        elif cur_state == S_YEAR:
            wiz["year"] = "" if text.lower() == "/skip" else text
            wiz["state"] = S_GENRE
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_GENRE, data=wiz, chat_id=chat_id)
            _log_wizard_step(uid, "SERIES_WIZARD", S_YEAR, S_GENRE)
            return await message.reply_text(
                f"Release Year: <b>{html.escape(wiz['year'] or 'N/A')}</b>\n\nPlease send the <b>Genre</b> (e.g. <code>Action, Drama</code>) or /skip:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel")]]),
                parse_mode=enums.ParseMode.HTML
            )
        elif cur_state == S_GENRE:
            wiz["genre"] = "" if text.lower() == "/skip" else text
            wiz["state"] = S_POSTER
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_POSTER, data=wiz, chat_id=chat_id)
            _log_wizard_step(uid, "SERIES_WIZARD", S_GENRE, S_POSTER)
            return await message.reply_text(
                f"Genre: <b>{html.escape(wiz['genre'] or 'N/A')}</b>\n\nPlease send a <b>Poster URL / Photo</b> or /skip:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel")]]),
                parse_mode=enums.ParseMode.HTML
            )
        elif cur_state == S_POSTER:
            poster_url = ""
            if message.photo:
                poster_url = message.photo.file_id
            elif text and text.lower() != "/skip":
                poster_url = text
            wiz["poster"] = poster_url
            wiz["state"] = S_LANGS
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_LANGS, data=wiz, chat_id=chat_id)
            _log_wizard_step(uid, "SERIES_WIZARD", S_POSTER, S_LANGS)
            return await message.reply_text(
                _series_card(wiz) + "\n\n🌐 <b>Select Available Languages:</b>",
                reply_markup=_lang_keyboard(wiz.get("languages", []), show_custom=True),
                parse_mode=enums.ParseMode.HTML
            )

    # ── Super Movie Batch Handler ────────────────────────────────────────────
    elif workflow == "SUPER_MOVIE_BATCH":
        batch_data = temp.AUTO_MOVIE_BATCH.get(uid, {})
        movie_id = batch_data.get("movie_id")
        session_id = batch_data.get("session_id")
        # Support batch links or message forwarded
        from database.series_db import sync_existing_movie_filter, get_super_movie
        if movie_id:
            res = await sync_existing_movie_filter(movie_id)
            clear_wizard_session(uid)
            temp.AUTO_MOVIE_BATCH.pop(uid, None)
            return await message.reply_text(
                f"✅ <b>Files batch synced to Super Movie!</b>\n\nTotal Files: <b>{res.get('total_files', 0)}</b>",
                parse_mode=enums.ParseMode.HTML
            )

    elif workflow == "SERIES_WIZARD_EDIT_POSTER":
        wiz = temp.SERIES_WIZARD.get(uid) or sess.get("data", {})
        poster_url = ""
        if message.photo:
            poster_url = message.photo.file_id
        elif text and text.lower() != "/skip":
            poster_url = text
        if poster_url:
            wiz["poster"] = poster_url
            temp.SERIES_WIZARD[uid] = wiz
            if wiz.get("series_id"):
                from database.series_db import series_col
                from bson import ObjectId
                try:
                    await series_col.update_one({"_id": ObjectId(wiz["series_id"])}, {"$set": {"poster": poster_url, "updated_at": datetime.utcnow()}})
                except Exception:
                    pass
        clear_wizard_session(uid)
        return await message.reply_text(
            _series_card(wiz) + "\n\n✅ <b>Poster updated!</b>\n⚙️ <b>Series Configuration:</b>",
            reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
            parse_mode=enums.ParseMode.HTML
        )

    elif workflow == "MOVIE_EDIT_POSTER":
        movie_data = sess.get("data", {})
        movie_id = movie_data.get("movie_id")
        poster_url = ""
        if message.photo:
            poster_url = message.photo.file_id
        elif text and text.lower() != "/skip":
            poster_url = text
        if poster_url and movie_id:
            from database.series_db import super_movies_col
            from bson import ObjectId
            try:
                await super_movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": {"poster": poster_url, "updated_at": datetime.utcnow()}})
            except Exception:
                pass
        clear_wizard_session(uid)
        return await message.reply_text(
            "✅ <b>Movie poster updated!</b>\nUse /viewmovies to inspect.",
            parse_mode=enums.ParseMode.HTML
        )


# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── CANONICAL SERIES WIZARD CALLBACK HANDLER (sw#) ───────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 

@Client.on_callback_query(filters.regex(r"^sw#"), group=-20)
async def series_wizard_callback(client: Client, query: CallbackQuery):
    print(f"### SW BUTTON RECEIVED data={query.data} user={query.from_user.id}", flush=True)
    try:
        await query.answer()
    except Exception:
        pass

    uid = query.from_user.id
    if not _is_admin(uid):
        return await query.answer("❌ Not authorized", show_alert=True)

    data = query.data
    chat_id = query.message.chat.id if query.message and query.message.chat else uid

    if data == "sw#start_manual":
        print("### MANUAL ADD BUTTON REACHED", flush=True)
        clear_wizard_session(uid)
        temp.AUTO_MOVIE.pop(uid, None)
        temp.AUTO_SERIES.pop(uid, None)
        temp.SERIES_WIZARD[uid] = {
            "mode": "create",
            "state": S_NAME,
            "name": "",
            "year": "",
            "genre": "",
            "description": "",
            "poster": "",
            "languages": [],
            "seasons": [],
            "qualities": [],
            "season_modes": {},
            "batch_langs": [], "batch_seasons": [], "batch_qualities": [],
            "batch_data": None,
            "from_viewseries": False
        }
        set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_NAME, data=temp.SERIES_WIZARD[uid], chat_id=chat_id)
        _log_wizard_step(uid, "SERIES_WIZARD", "IDLE", S_NAME)

        prompt_text = (
            "📝 <b>Manual Series Adding</b>\n\n"
            "You selected <b>Manual Adding</b>.\n\n"
            "Please send the <b>Series Name</b>.\n\n"
            "Example:\n<code>Loki</code>"
        )
        return await query.message.edit_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "sw#start_auto":
        print("### AUTO SERIES BUTTON REACHED", flush=True)
        clear_wizard_session(uid)
        temp.AUTO_MOVIE.pop(uid, None)
        temp.SERIES_WIZARD.pop(uid, None)
        auto_data = {
            "state": "WAIT_IMDB",
            "user_id": uid,
            "chat_id": chat_id,
            "created_at": time.time(),
            "prompt_msg_id": query.message.id
        }
        temp.AUTO_SERIES[uid] = auto_data
        set_wizard_session(uid, workflow="AUTO_SERIES", state="WAIT_IMDB", data=auto_data, chat_id=chat_id)
        _log_wizard_step(uid, "AUTO_SERIES", "IDLE", "WAIT_IMDB")

        prompt_text = (
            "📺 <b>Auto Series Add</b>\n\n"
            "You selected <b>Auto S Add</b>.\n\n"
            "Please send the <b>IMDb Series URL or ID</b>.\n\n"
            "Example:\n<code>https://www.imdb.com/title/tt9288030/</code>\n\nor:\n<code>tt9288030</code>"
        )
        return await query.message.edit_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    elif data in ("sw#start_auto_movie", "sw#auto_movie"):
        print("### AUTO MOVIE BUTTON REACHED", flush=True)
        clear_wizard_session(uid)
        temp.AUTO_SERIES.pop(uid, None)
        temp.SERIES_WIZARD.pop(uid, None)
        import uuid
        session_id = str(uuid.uuid4())[:8]
        movie_data = {
            "session_id": session_id,
            "state": "WAIT_IMDB",
            "user_id": uid,
            "chat_id": chat_id,
            "created_at": time.time(),
            "prompt_msg_id": query.message.id
        }
        temp.AUTO_MOVIE[session_id] = movie_data
        temp.AUTO_MOVIE[uid] = movie_data
        set_wizard_session(uid, workflow="AUTO_MOVIE", state="WAIT_IMDB", data=movie_data, chat_id=chat_id)
        _log_wizard_step(uid, "AUTO_MOVIE", "IDLE", "WAIT_IMDB")

        prompt_text = (
            "🎬 <b>Auto Movie Add</b>\n\n"
            "You selected <b>Auto Movie Add</b>.\n\n"
            "Please send the <b>IMDb Movie URL or ID</b>.\n\n"
            "Example:\n<code>https://www.imdb.com/title/tt11948256/</code>\n\nor:\n<code>tt11948256</code>"
        )
        return await query.message.edit_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#auto_cancel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "sw#vser_back":
        logger.info(f"[VIEW SERIES BACK]\nuser_id={uid}")
        temp.SERIES_WIZARD.pop(uid, None)
        return await send_filter_manager(query, ftype="series", page=0)

    elif data == "sw#save":
        wiz = temp.SERIES_WIZARD.get(uid)
        if wiz and wiz.get("series_id"):
            from database.series_db import series_col
            from bson import ObjectId
            try:
                await series_col.update_one(
                    {"_id": ObjectId(wiz["series_id"])},
                    {
                        "$set": {
                            "name": wiz.get("name"),
                            "year": wiz.get("year", ""),
                            "genre": wiz.get("genre", ""),
                            "description": wiz.get("description", ""),
                            "poster": wiz.get("poster", ""),
                            "languages": wiz.get("languages", []),
                            "seasons": wiz.get("seasons", []),
                            "qualities": wiz.get("qualities", []),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            except Exception:
                pass
        if wiz and wiz.get("from_viewseries"):
            temp.SERIES_WIZARD.pop(uid, None)
            await query.answer("✅ Series saved successfully!", show_alert=True)
            return await send_filter_manager(query, ftype="series", page=0)
        else:
            clear_wizard_session(uid)
            temp.SERIES_WIZARD.pop(uid, None)
            return await query.message.edit_text("✅ <b>Series configuration saved!</b>", parse_mode=enums.ParseMode.HTML)

    elif data.startswith("sw#menu#batch"):
        wiz = temp.SERIES_WIZARD.get(uid)
        series_id = wiz.get("series_id") if wiz else None
        if not series_id and "#" in data:
            parts = data.split("#")
            if len(parts) >= 4:
                series_id = parts[3]
        if not series_id:
            return await query.answer("Series ID not found.", show_alert=True)

        from database.series_db import scan_sdatabase_for_series, add_series_file, get_series
        exact = await get_series(series_id)
        s_name = exact.get("name", "Series") if exact else "Series"
        await query.message.edit_text(f"🔄 <b>Scanning database for files matching '{s_name}'...</b>", parse_mode=enums.ParseMode.HTML)
        scan_res = await scan_sdatabase_for_series(chat_id, s_name, season=None, series_id=series_id, client=client)
        new_files = scan_res.get("valid_new_files") or []
        for f in new_files:
            try:
                await add_series_file({
                    "series_id": series_id,
                    "language": f["language"],
                    "season": f["season"],
                    "episode": f["episode"],
                    "quality": f["quality"],
                    "chat_id": chat_id,
                    "file_id": f.get("file_id"),
                    "file_name": f.get("file_name"),
                    "file_size": f.get("file_size", 0)
                })
            except Exception:
                pass
        await query.answer(f"✅ Synced {len(new_files)} files!", show_alert=True)
        if wiz:
            return await query.message.edit_text(
                _series_card(wiz) + f"\n\n📁 <b>Synced {len(new_files)} new files.</b>\n⚙️ <b>Series Configuration:</b>",
                reply_markup=_config_menu_keyboard(series_id, wiz.get("from_viewseries", True)),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            return await send_filter_manager(query, ftype="series", page=0)

    elif data.startswith("sw#menu#add_ep"):
        return await query.answer("Use '📁 Add Files' to scan database or forward episode files to the channel.", show_alert=True)

    elif data.startswith("sw#edit#langs"):
        wiz = temp.SERIES_WIZARD.get(uid)
        if not wiz:
            return await query.answer("Session expired.", show_alert=True)
        langs = wiz.get("languages", [])
        return await query.message.edit_text(
            _series_card(wiz) + "\n\n🌐 <b>Toggle Available Languages:</b>\nClick a language to add/remove, then click Submit:",
            reply_markup=_lang_keyboard(langs, show_custom=False),
            parse_mode=enums.ParseMode.HTML
        )

    elif data.startswith("sw#edit#seasons"):
        wiz = temp.SERIES_WIZARD.get(uid)
        if not wiz:
            return await query.answer("Session expired.", show_alert=True)
        seasons = wiz.get("seasons", [])
        return await query.message.edit_text(
            _series_card(wiz) + "\n\n📅 <b>Toggle Available Seasons:</b>\nClick a season to add/remove, then click Submit:",
            reply_markup=_season_keyboard(MAX_SEASONS, seasons, show_skip=False),
            parse_mode=enums.ParseMode.HTML
        )

    elif data.startswith("sw#edit#quals"):
        wiz = temp.SERIES_WIZARD.get(uid)
        if not wiz:
            return await query.answer("Session expired.", show_alert=True)
        quals = wiz.get("qualities", [])
        return await query.message.edit_text(
            _series_card(wiz) + "\n\n⚡ <b>Toggle Available Qualities:</b>\nClick a quality to add/remove, then click Submit:",
            reply_markup=_quality_keyboard(quals, show_custom=False),
            parse_mode=enums.ParseMode.HTML
        )

    elif data.startswith("sw#edit#poster"):
        wiz = temp.SERIES_WIZARD.get(uid)
        if not wiz:
            return await query.answer("Session expired.", show_alert=True)
        set_wizard_session(uid, workflow="SERIES_WIZARD_EDIT_POSTER", state="WAIT_POSTER", data=wiz, chat_id=chat_id)
        return await query.message.edit_text(
            "🖼 <b>Edit Series Poster</b>\n\nPlease send the <b>new Poster Photo or URL</b>:\n(or click Cancel to return)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#edit#cancel")]]),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "sw#edit#cancel":
        wiz = temp.SERIES_WIZARD.get(uid)
        clear_wizard_session(uid)
        if wiz:
            return await query.message.edit_text(
                _series_card(wiz) + "\n\n⚙️ <b>Series Configuration</b>\nChoose an option to edit:",
                reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            return await send_filter_manager(query, ftype="series", page=0)

    elif data in ("sw#cancel", "sw#auto_cancel", "sw#auto_movie_cancel"):
        wiz = temp.SERIES_WIZARD.get(uid)
        if wiz and wiz.get("from_viewseries"):
            temp.SERIES_WIZARD.pop(uid, None)
            return await send_filter_manager(query, ftype="series", page=0)

        for sess_id, t in list(AUTO_MOVIE_METADATA_TASKS.items()):
            m_data = getattr(temp, "AUTO_MOVIE", {}).get(sess_id, {})
            if m_data.get("user_id") == uid or m_data.get("admin_id") == uid:
                if t and not t.done():
                    t.cancel()
                AUTO_MOVIE_METADATA_TASKS.pop(sess_id, None)

        for sess_id, t in list(AUTO_SERIES_METADATA_TASKS.items()):
            s_data = getattr(temp, "AUTO_SERIES", {}).get(sess_id, {})
            if s_data.get("user_id") == uid or s_data.get("admin_id") == uid:
                if t and not t.done():
                    t.cancel()
                AUTO_SERIES_METADATA_TASKS.pop(sess_id, None)

        for sess_id, t in list(AUTO_MOVIE_SCAN_TASKS.items()):
            m_data = getattr(temp, "AUTO_MOVIE", {}).get(sess_id, {})
            if m_data.get("user_id") == uid or m_data.get("admin_id") == uid:
                ev = AUTO_MOVIE_CANCEL_EVENTS.get(sess_id)
                if ev:
                    ev.set()
                if t and not t.done():
                    t.cancel()
                AUTO_MOVIE_SCAN_TASKS.pop(sess_id, None)

        cancel_wizard_session(uid)
        clear_wizard_session(uid)
        temp.AUTO_MOVIE.pop(uid, None)
        temp.AUTO_SERIES.pop(uid, None)
        temp.SERIES_WIZARD.pop(uid, None)
        return await query.message.edit_text(
            "❌ <b>Action cancelled.</b>",
            parse_mode=enums.ParseMode.HTML
        )

    # ── Wizard Selection Steps ───────────────────────────────────────────────
    wiz = temp.SERIES_WIZARD.get(uid)
    if not wiz:
        return await query.answer("Session expired. Please start over.", show_alert=True)

    if data.startswith("sw#lang#"):
        val = data.split("#")[2]
        if val == "submit":
            if not wiz.get("languages"):
                return await query.answer("Please select at least one language.", show_alert=True)
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            wiz["state"] = S_SEASONS
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_SEASONS, data=wiz, chat_id=chat_id)
            return await query.message.edit_text(
                _series_card(wiz) + "\n\n📅 <b>Select Available Seasons:</b>",
                reply_markup=_season_keyboard(MAX_SEASONS, wiz.get("seasons", []), show_skip=True),
                parse_mode=enums.ParseMode.HTML
            )
        elif val == "back":
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            wiz["state"] = S_POSTER
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_POSTER, data=wiz, chat_id=chat_id)
            return await query.message.edit_text(
                "Please send a <b>Poster URL / Photo</b> or /skip:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sw#cancel")]]),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            langs = wiz.setdefault("languages", [])
            if val in langs:
                langs.remove(val)
            else:
                langs.append(val)
            return await query.message.edit_reply_markup(reply_markup=_lang_keyboard(langs, show_custom=(wiz.get("mode") != "edit")))

    elif data.startswith("sw#season#"):
        val = data.split("#")[2]
        if val in ("submit", "skip"):
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            wiz["state"] = S_QUALITY
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_QUALITY, data=wiz, chat_id=chat_id)
            return await query.message.edit_text(
                _series_card(wiz) + "\n\n🎞 <b>Select Available Qualities:</b>",
                reply_markup=_quality_keyboard(wiz.get("qualities", []), show_custom=True),
                parse_mode=enums.ParseMode.HTML
            )
        elif val == "back":
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            wiz["state"] = S_LANGS
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_LANGS, data=wiz, chat_id=chat_id)
            return await query.message.edit_text(
                _series_card(wiz) + "\n\n🌐 <b>Select Available Languages:</b>",
                reply_markup=_lang_keyboard(wiz.get("languages", []), show_custom=True),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            try:
                s_int = int(val)
                seasons = wiz.setdefault("seasons", [])
                if s_int in seasons:
                    seasons.remove(s_int)
                else:
                    seasons.append(s_int)
                return await query.message.edit_reply_markup(reply_markup=_season_keyboard(MAX_SEASONS, seasons, show_skip=(wiz.get("mode") != "edit")))
            except Exception:
                pass

    elif data.startswith("sw#quality#"):
        val = data.split("#")[2]
        if val == "submit":
            if not wiz.get("qualities"):
                return await query.answer("Please select at least one quality.", show_alert=True)
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            # Create mode: Commit to database!
            from database.series_db import create_series, search_series
            series_id = await create_series({
                "name": wiz["name"],
                "year": wiz.get("year", ""),
                "genre": wiz.get("genre", ""),
                "rating": wiz.get("rating", ""),
                "poster": wiz.get("poster", ""),
                "description": wiz.get("description", ""),
                "languages": wiz.get("languages", []),
                "seasons": wiz.get("seasons", []),
                "qualities": wiz.get("qualities", []),
                "created_by": uid
            })
            logger.info(f"[SERIES SEARCH VERIFY] name={wiz['name']} series_id={series_id}")
            clear_wizard_session(uid)
            temp.SERIES_WIZARD.pop(uid, None)
            return await query.message.edit_text(
                f"✅ <b>Series Filter Created Successfully!</b>\n\n📺 <b>{html.escape(wiz['name'])}</b>\n\n<i>ID: <code>{series_id}</code></i>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📁 Add Files / Batch", callback_data=f"sw#menu#batch#{series_id}")]]),
                parse_mode=enums.ParseMode.HTML
            )
        elif val == "back":
            if wiz.get("mode") == "edit":
                return await query.message.edit_text(
                    _series_card(wiz) + "\n\n⚙️ <b>Edit Series Configuration</b>\nChoose an option to edit:",
                    reply_markup=_config_menu_keyboard(wiz.get("series_id"), wiz.get("from_viewseries", True)),
                    parse_mode=enums.ParseMode.HTML
                )
            wiz["state"] = S_SEASONS
            set_wizard_session(uid, workflow="SERIES_WIZARD", state=S_SEASONS, data=wiz, chat_id=chat_id)
            return await query.message.edit_text(
                _series_card(wiz) + "\n\n📅 <b>Select Available Seasons:</b>",
                reply_markup=_season_keyboard(MAX_SEASONS, wiz.get("seasons", []), show_skip=True),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            quals = wiz.setdefault("qualities", [])
            if val in quals:
                quals.remove(val)
            else:
                quals.append(val)
            return await query.message.edit_reply_markup(reply_markup=_quality_keyboard(quals, show_custom=(wiz.get("mode") != "edit")))


# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── AUTO MOVIE CALLBACK HANDLER (am_) ───────────────────────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 

@Client.on_callback_query(filters.regex(r"^am_"), group=-15)
async def auto_movie_callbacks(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass

    uid = query.from_user.id
    if not _is_admin(uid):
        return await query.answer("❌ Not authorized", show_alert=True)

    data = query.data

    if data.startswith("am_save:"):
        session_id = data.split(":")[1]
        movie_data = temp.AUTO_MOVIE.get(session_id) or temp.AUTO_MOVIE.get(uid)
        if not movie_data:
            return await query.answer("⚠️ Session expired. Please scan again.", show_alert=True)

        logger.info("[AUTO MOVIE] FILTER SAVE")
        from database.series_db import scan_movie_batch_by_name_year, create_super_movie, search_super_movies, get_super_movie

        # Strict gate: Re-verify that actual matching files exist in DB
        logger.info("[AUTO MOVIE] FILTER VERIFY")
        scan_check = await scan_movie_batch_by_name_year(
            title=movie_data["title"],
            year=movie_data.get("year"),
            imdb_id=movie_data.get("imdb_id"),
            tmdb_id=movie_data.get("tmdb_id")
        )
        matching_files = scan_check.get("matching_files", [])
        if not matching_files:
            return await query.answer("❌ No matching movie files available in database to create this filter.", show_alert=True)

        file_ids = [f["file_id"] for f in matching_files if f.get("file_id")]
        if not file_ids:
            return await query.answer("❌ No matching movie files available in database to create this filter.", show_alert=True)

        movie_id = await create_super_movie({
            "title": movie_data["title"],
            "year": movie_data.get("year", "N/A"),
            "genre": movie_data.get("genre", "N/A"),
            "rating": movie_data.get("rating", ""),
            "poster": movie_data.get("poster", ""),
            "description": movie_data.get("description", ""),
            "languages": list(movie_data.get("grouped", {}).keys()),
            "qualities": list({q for l in movie_data.get("grouped", {}).values() for q in l.keys()}),
            "file_ids": file_ids,
            "imdb_id": movie_data.get("imdb_id"),
            "tmdb_id": movie_data.get("tmdb_id"),
            "created_by": uid,
            "status": "active"
        })

        logger.info(
            f"[AUTO MOVIE FILTER CREATE]\n"
            f"movie_id={movie_id}\n"
            f"files={len(file_ids)}"
        )
        verify_check = await search_super_movies(movie_data["title"])
        if verify_check:
            logger.info(f"[AUTO MOVIE FILTER VERIFY] result=SUCCESS movie_id={movie_id}")
        else:
            logger.error(f"[AUTO MOVIE FILTER VERIFY] result=FAILED movie_id={movie_id}")

        clear_wizard_session(uid)
        temp.AUTO_MOVIE.pop(uid, None)
        temp.AUTO_MOVIE.pop(session_id, None)

        try:
            await announce_filter_created(client, filter_type="movie", filter_id=str(movie_id))
        except Exception as ae:
            logger.warning(f"[AUTO MOVIE ANNOUNCEMENT ERROR] {ae}")

        title_esc = html.escape(str(movie_data.get('title', '')))
        year_esc = html.escape(str(movie_data.get('year', '')))
        tot_files = len(file_ids)

        return await query.message.edit_text(
            f"✅ <b>Super Movie Filter Saved Successfully!</b>\n\n"
            f"🎬 <b>{title_esc} ({year_esc})</b>\n\n"
            f"📁 <b>Linked Files:</b> {tot_files}\n"
            f"<i>Super Movie Filter ID: <code>{movie_id}</code></i>",
            parse_mode=enums.ParseMode.HTML
        )

    elif data.startswith("am_scan:"):
        session_id = data.split(":")[1]
        movie_data = temp.AUTO_MOVIE.get(session_id) or temp.AUTO_MOVIE.get(uid)
        if not movie_data:
            return await query.answer("⚠️ Session expired.", show_alert=True)
        return await run_auto_movie_scan(client, query.message.chat.id, query.message, session_id, movie_data)

    elif data.startswith("am_cancel:"):
        session_id = data.split(":")[1]
        clear_wizard_session(uid)
        temp.AUTO_MOVIE.pop(uid, None)
        temp.AUTO_MOVIE.pop(session_id, None)
        return await query.message.edit_text("❌ <b>Auto Movie Add cancelled.</b>", parse_mode=enums.ParseMode.HTML)

    elif data.startswith("am_qual:"):
        parts = data.split(":")
        session_id = parts[1]
        lang = parts[2]
        qual = parts[3]
        movie_data = temp.AUTO_MOVIE.get(session_id) or temp.AUTO_MOVIE.get(uid)
        if not movie_data:
            return await query.answer("⚠️ Session expired.", show_alert=True)
        files = movie_data.get("grouped", {}).get(lang, {}).get(qual, [])
        return await query.message.edit_text(
            _build_auto_movie_file_text(movie_data, lang, qual),
            reply_markup=_build_auto_movie_file_keyboard(session_id, lang, qual, files, page=0),
            parse_mode=enums.ParseMode.HTML
        )

    elif data.startswith("am_back:"):
        session_id = data.split(":")[1]
        movie_data = temp.AUTO_MOVIE.get(session_id) or temp.AUTO_MOVIE.get(uid)
        if not movie_data:
            return await query.answer("⚠️ Session expired.", show_alert=True)
        return await query.message.edit_text(
            _build_auto_movie_lang_text(movie_data),
            reply_markup=_build_auto_movie_lang_keyboard(session_id, movie_data),
            parse_mode=enums.ParseMode.HTML
        )


# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 
# ─── USER SEARCH ROUTERS (Super Movie & Series Search) ───────────────────────
# ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ 

async def render_super_movie_direct(client: Client, message: Message, movie: dict, reply_msg: Message = None) -> bool:
    """Renders the language selection UI for a specific Super Movie."""
    from database.ia_filterdb import get_file_details
    from plugins.pm_filter import group_movie_files, build_movie_language_keyboard, BUTTON_OWNERS

    movie_id = str(movie["_id"])
    file_ids = movie.get("file_ids", [])
    if not file_ids:
        logger.info(f"[SUPER MOVIE SEARCH] matched_filter_but_no_files title={movie.get('title')} id={movie_id}")
        return False

    file_docs = []
    for fid in file_ids:
        fdoc = await get_file_details(fid)
        if fdoc:
            file_docs.append(fdoc)

    if not file_docs:
        return False

    grouped = group_movie_files(file_docs)
    if not grouped:
        return False

    chat_id = message.chat.id if message and message.chat else (reply_msg.chat.id if reply_msg else 0)
    msg_id = message.id if message else (reply_msg.id if reply_msg else 0)
    key = f"{chat_id}-{msg_id}"
    user_id = message.from_user.id if (message and message.from_user) else (reply_msg.from_user.id if reply_msg and reply_msg.from_user else chat_id)

    temp.MOVIE_STATE[key] = {
        "movie_id": movie_id,
        "title": movie.get("title", ""),
        "year": str(movie.get("year", "")),
        "rating": str(movie.get("rating", "")),
        "genre": movie.get("genre", ""),
        "poster": movie.get("poster", ""),
        "description": movie.get("description", ""),
        "grouped": grouped,
        "chat_id": chat_id,
        "user_id": user_id
    }
    BUTTON_OWNERS[key] = user_id

    title = movie.get("title", "")
    year = str(movie.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = str(movie.get("rating", ""))
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = movie.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
    poster = movie.get("poster", "")

    caption_text = (
        f"🎬 <b>{title}{year_str}</b>"
        f"{rating_str}"
        f"{genre_str}\n\n"
        f"🌐 <b>Select Language:</b>"
    )
    markup = build_movie_language_keyboard(key, grouped)

    if reply_msg:
        try:
            if reply_msg.photo or reply_msg.caption:
                await reply_msg.edit_caption(
                    caption=caption_text,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return True
            else:
                await reply_msg.edit_text(
                    text=caption_text,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return True
        except Exception:
            try:
                await reply_msg.delete()
            except Exception:
                pass

    if poster:
        try:
            await (message.reply_photo(
                photo=poster,
                caption=caption_text,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML
            ) if message else client.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=caption_text,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML
            ))
            return True
        except Exception as pe:
            logger.warning(f"[SUPER MOVIE PHOTO ERROR] {pe}")

    await (message.reply_text(
        text=caption_text,
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    ) if message else client.send_message(
        chat_id=chat_id,
        text=caption_text,
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    ))
    return True


async def render_series_direct(client: Client, message: Message, series_doc: dict, reply_msg: Message = None) -> bool:
    """Renders the language selection UI for a specific Series Filter."""
    from database.series_db import list_series_languages
    from plugins.pm_filter import BUTTON_OWNERS

    series_id = str(series_doc["_id"])
    name = series_doc.get("name", "")
    year = str(series_doc.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = str(series_doc.get("rating", ""))
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = series_doc.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""
    poster = series_doc.get("poster", "")

    langs = await list_series_languages(series_id)
    if not langs:
        langs = series_doc.get("languages", [])

    chat_id = message.chat.id if message and message.chat else (reply_msg.chat.id if reply_msg else 0)
    msg_id = message.id if message else (reply_msg.id if reply_msg else 0)
    key = f"{chat_id}-{msg_id}"
    user_id = message.from_user.id if (message and message.from_user) else (reply_msg.from_user.id if reply_msg and reply_msg.from_user else chat_id)
    BUTTON_OWNERS[key] = user_id

    buttons = []
    preferred_order = ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English", "Dual Audio", "Multi Audio"]
    langs_sorted = sorted(langs, key=lambda x: (preferred_order.index(x) if x in preferred_order else 99, x))
    for i in range(0, len(langs_sorted), 2):
        row = []
        for l in langs_sorted[i:i+2]:
            row.append(InlineKeyboardButton(to_series_font(l), callback_data=f"ser_lang#{series_id}#{l}#{key}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"ser_close#{key}")])

    caption_text = (
        f"📺 <b>{name}{year_str}</b>"
        f"{rating_str}"
        f"{genre_str}\n\n"
        f"🌐 <b>Select Language:</b>"
    )
    markup = InlineKeyboardMarkup(buttons)

    if reply_msg:
        try:
            if reply_msg.photo or reply_msg.caption:
                await reply_msg.edit_caption(
                    caption=caption_text,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return True
            else:
                await reply_msg.edit_text(
                    text=caption_text,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return True
        except Exception:
            try:
                await reply_msg.delete()
            except Exception:
                pass

    if poster:
        try:
            await (message.reply_photo(
                photo=poster,
                caption=caption_text,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML
            ) if message else client.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=caption_text,
                reply_markup=markup,
                parse_mode=enums.ParseMode.HTML
            ))
            return True
        except Exception as pe:
            logger.warning(f"[SERIES PHOTO ERROR] {pe}")

    await (message.reply_text(
        text=caption_text,
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    ) if message else client.send_message(
        chat_id=chat_id,
        text=caption_text,
        reply_markup=markup,
        parse_mode=enums.ParseMode.HTML
    ))
    return True


async def process_unified_filter_search(client: Client, message: Message, query_text: str, reply_msg: Message = None) -> bool:
    """
    Unified filter search across Super Movies and Series.
    - If 1 filter matches: opens that filter directly.
    - If multiple filters match (e.g. Aadu 2015, Aadu 2017, Aadu 3): presents unified suggestion list with buttons.
    - If 0 match: returns False.
    """
    q = str(query_text or "").strip()
    if not q:
        return False

    from database.series_db import search_super_movies, search_series, get_series_thumbnail, normalize_movie_search_title

    clean_q = clean_series_title(q)
    super_movies = await search_super_movies(q)
    series_list = await search_series(clean_q)

    # Filter out super movies with 0 files
    valid_movies = [m for m in super_movies if m.get("file_ids")]
    valid_series = series_list

    total_matches = len(valid_movies) + len(valid_series)

    logger.info(
        f"[UNIFIED FILTER SEARCH]\n"
        f"query={q}\n"
        f"super_movies={len(valid_movies)}\n"
        f"series={len(valid_series)}\n"
        f"total={total_matches}"
    )

    if total_matches == 0:
        return False

    # Check if exact year was specified in query
    has_year = bool(re.search(r"\b(19\d\d|20\d\d)\b", q))
    if total_matches == 1 or (has_year and not reply_msg and total_matches > 0):
        if valid_movies:
            return await render_super_movie_direct(client, message, valid_movies[0], reply_msg)
        elif valid_series:
            return await render_series_direct(client, message, valid_series[0], reply_msg)

    # total_matches > 1: Show Unified Suggestion List
    rows = []
    for m in valid_movies:
        title = m.get("title", "")
        year = str(m.get("year", "")).strip()
        year_str = f" ({year})" if year and year != "N/A" else ""
        btn_text = f"🎬 {title}{year_str}"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"sug_mov#{str(m['_id'])}")])

    for s in valid_series:
        name = s.get("name", "")
        year = str(s.get("year", "")).strip()
        year_str = f" ({year})" if year and year != "N/A" else ""
        btn_text = f"📺 {name}{year_str}"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"sug_ser#{str(s['_id'])}")])

    markup = InlineKeyboardMarkup(rows)
    caption_text = "<b>Choose the series/movie you want to view</b>"

    thumb = await get_series_thumbnail()

    if reply_msg:
        try:
            if reply_msg.photo or reply_msg.caption:
                await reply_msg.edit_caption(caption=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                return True
            else:
                await reply_msg.edit_text(text=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                return True
        except Exception:
            try:
                await reply_msg.delete()
            except Exception:
                pass

    if thumb:
        try:
            if message:
                await message.reply_photo(photo=thumb, caption=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            else:
                await client.send_photo(chat_id=message.chat.id, photo=thumb, caption=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            return True
        except Exception as pe:
            logger.warning(f"[UNIFIED SEARCH THUMB ERROR] {pe}")

    if message:
        await message.reply_text(text=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    else:
        await client.send_message(chat_id=message.chat.id, text=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    return True


@Client.on_callback_query(filters.regex(r"^sug_mov#"), group=-15)
async def cb_sug_movie(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass
    parts = query.data.split("#")
    if len(parts) < 2:
        return
    movie_id = parts[1]
    from database.series_db import get_super_movie
    movie = await get_super_movie(movie_id)
    if not movie:
        return await query.answer("❌ Movie not found.", show_alert=True)
    await render_super_movie_direct(client, query.message, movie, reply_msg=query.message)


@Client.on_callback_query(filters.regex(r"^sug_ser#"), group=-15)
async def cb_sug_series(client: Client, query: CallbackQuery):
    try:
        await query.answer()
    except Exception:
        pass
    parts = query.data.split("#")
    if len(parts) < 2:
        return
    series_id = parts[1]
    from database.series_db import get_series
    series_doc = await get_series(series_id)
    if not series_doc:
        return await query.answer("❌ Series not found.", show_alert=True)
    await render_series_direct(client, query.message, series_doc, reply_msg=query.message)


async def process_super_movie_search(client: Client, message: Message, query_text: str, reply_msg: Message = None) -> bool:
    """Backward-compatible alias for process_unified_filter_search."""
    return await process_unified_filter_search(client, message, query_text, reply_msg)


async def process_series_search(client: Client, message: Message, query_text: str, reply_msg: Message = None) -> bool:
    """Backward-compatible alias for process_unified_filter_search."""
    return await process_unified_filter_search(client, message, query_text, reply_msg)


# ─── SERIES FILTER NAVIGATION CALLBACKS ─────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^ser_lang#"))
async def ser_lang_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) < 4:
        return await query.answer("Invalid request.", show_alert=True)
    _, series_id, lang, key = parts[0], parts[1], parts[2], parts[3]
    
    from plugins.pm_filter import is_button_owner
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)

    from database.series_db import get_series, list_series_seasons
    series = await get_series(series_id)
    if not series:
        return await query.answer("⚠️ Series not found in database.", show_alert=True)

    seasons = await list_series_seasons(series_id, lang)
    if not seasons:
        seasons = series.get("seasons", [1])
        if isinstance(seasons, int):
            seasons = list(range(1, seasons + 1))
        elif not isinstance(seasons, list):
            seasons = [1]

    name = series.get("name", "Series")
    year = str(series.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = str(series.get("rating", ""))
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = series.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""

    buttons = []
    seasons_sorted = sorted([int(s) for s in seasons if str(s).isdigit()])
    if not seasons_sorted:
        seasons_sorted = [1]

    for i in range(0, len(seasons_sorted), 2):
        row = []
        for s in seasons_sorted[i:i+2]:
            row.append(InlineKeyboardButton(f"📅 Season {s}", callback_data=f"ser_season#{series_id}#{lang}#{s}#{key}"))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("⬅️ Language", callback_data=f"ser_back#{series_id}#langs#{lang}#{key}"),
        InlineKeyboardButton("❌ Close", callback_data=f"ser_close#{key}")
    ])

    cap = (
        f"📺 <b>{name}{year_str}</b>"
        f"{rating_str}"
        f"{genre_str}\n\n"
        f"🌐 <b>Language:</b> {lang}\n\n"
        f"📅 <b>Select Season:</b>"
    )
    markup = InlineKeyboardMarkup(buttons)
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


@Client.on_callback_query(filters.regex(r"^ser_season#"))
async def ser_season_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) < 5:
        return await query.answer("Invalid request.", show_alert=True)
    _, series_id, lang, season_str, key = parts[0], parts[1], parts[2], parts[3], parts[4]
    season = int(season_str) if season_str.isdigit() else 1

    from plugins.pm_filter import is_button_owner
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)

    from database.series_db import get_series, list_season_qualities, sfiles_col, _sid_query, _num_query
    series = await get_series(series_id)
    if not series:
        return await query.answer("⚠️ Series not found in database.", show_alert=True)

    name = series.get("name", "Series")
    year = str(series.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""

    # Fetch distinct episodes
    ep_vals = await sfiles_col.distinct("episode", {
        "series_id": _sid_query(series_id),
        "language": lang,
        "season": _num_query(season)
    })
    episodes = sorted([int(e) for e in ep_vals if (isinstance(e, int) or (isinstance(e, str) and str(e).isdigit())) and int(e) > 0])

    buttons = []
    if episodes:
        for i in range(0, len(episodes), 4):
            row = []
            for ep in episodes[i:i+4]:
                ep_text = f"🎬 Ep {ep:02d}" if ep < 100 else f"🎬 Ep {ep}"
                row.append(InlineKeyboardButton(ep_text, callback_data=f"ser_ep#{series_id}#{lang}#{season}#{ep}#{key}"))
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("⬅️ Season", callback_data=f"ser_lang#{series_id}#{lang}#{key}"),
            InlineKeyboardButton("⬅️ Language", callback_data=f"ser_back#{series_id}#langs#{lang}#{key}")
        ])
        cap = (
            f"📺 <b>{name}{year_str}</b>\n\n"
            f"🌐 <b>Language:</b> {lang} | 📅 <b>Season {season}</b>\n\n"
            f"🎬 <b>Select Episode:</b>"
        )
    else:
        qualities = await list_season_qualities(series_id, lang, season)
        if not qualities:
            qualities = ["480p", "720p", "1080p"]
        for i in range(0, len(qualities), 2):
            row = []
            for q in qualities[i:i+2]:
                row.append(InlineKeyboardButton(f"⚡ {q}", callback_data=f"ser_qual#{series_id}#{lang}#{season}#0#{q}#{key}"))
            buttons.append(row)
        buttons.append([
            InlineKeyboardButton("⬅️ Season", callback_data=f"ser_lang#{series_id}#{lang}#{key}"),
            InlineKeyboardButton("⬅️ Language", callback_data=f"ser_back#{series_id}#langs#{lang}#{key}")
        ])
        cap = (
            f"📺 <b>{name}{year_str}</b>\n\n"
            f"🌐 <b>Language:</b> {lang} | 📅 <b>Season {season}</b>\n\n"
            f"🎞 <b>Select Quality:</b>"
        )

    markup = InlineKeyboardMarkup(buttons)
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


@Client.on_callback_query(filters.regex(r"^ser_ep#"))
async def ser_ep_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) < 6:
        return await query.answer("Invalid request.", show_alert=True)
    _, series_id, lang, season_str, ep_str, key = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    season = int(season_str) if season_str.isdigit() else 1
    episode = int(ep_str) if ep_str.isdigit() else 1

    from plugins.pm_filter import is_button_owner
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)

    from database.series_db import get_series, list_season_qualities, sfiles_col, _sid_query, _num_query
    series = await get_series(series_id)
    if not series:
        return await query.answer("⚠️ Series not found in database.", show_alert=True)

    name = series.get("name", "Series")
    year = str(series.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""

    qual_vals = await sfiles_col.distinct("quality", {
        "series_id": _sid_query(series_id),
        "language": lang,
        "season": _num_query(season),
        "episode": _num_query(episode)
    })
    qualities = [q for q in qual_vals if q]
    if not qualities:
        qualities = await list_season_qualities(series_id, lang, season)
    if not qualities:
        qualities = ["480p", "720p", "1080p"]

    buttons = []
    for i in range(0, len(qualities), 2):
        row = []
        for q in qualities[i:i+2]:
            row.append(InlineKeyboardButton(f"⚡ {q}", callback_data=f"ser_qual#{series_id}#{lang}#{season}#{episode}#{q}#{key}"))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("⬅️ Episode", callback_data=f"ser_season#{series_id}#{lang}#{season}#{key}"),
        InlineKeyboardButton("⬅️ Season", callback_data=f"ser_lang#{series_id}#{lang}#{key}")
    ])

    cap = (
        f"📺 <b>{name}{year_str}</b>\n\n"
        f"🌐 <b>Language:</b> {lang} | 📅 <b>Season {season}</b> | 🎬 <b>Episode {episode}</b>\n\n"
        f"🎞 <b>Select Quality:</b>"
    )
    markup = InlineKeyboardMarkup(buttons)
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


@Client.on_callback_query(filters.regex(r"^ser_qual#"))
async def ser_qual_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) < 7:
        return await query.answer("Invalid request.", show_alert=True)
    _, series_id, lang, season_str, ep_str, qual, key = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
    season = int(season_str) if season_str.isdigit() else 1
    episode = int(ep_str) if ep_str.isdigit() else 0

    from plugins.pm_filter import is_button_owner
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)

    from database.series_db import get_series, sfiles_col, _sid_query, _num_query, save_temp_request
    series = await get_series(series_id)
    if not series:
        return await query.answer("⚠️ Series not found in database.", show_alert=True)

    title = series.get("name", "Series")
    query_filter = {
        "series_id": _sid_query(series_id),
        "language": lang,
        "season": _num_query(season),
        "quality": qual
    }
    if episode > 0:
        query_filter["episode"] = _num_query(episode)

    cursor = sfiles_col.find(query_filter)
    files = [doc async for doc in cursor]
    if not files:
        cursor = sfiles_col.find({
            "series_id": _sid_query(series_id),
            "language": lang,
            "season": _num_query(season),
            "quality": qual
        })
        files = [doc async for doc in cursor]

    if not files:
        return await query.answer("⚠️ No files found for this quality.", show_alert=True)

    logger.info(f"[SERIES QUALITY DELIVERY]\ntitle={title}\nlang={lang}\nseason={season}\nep={episode}\nqual={qual}\nfiles={len(files)}")

    import uuid, time
    req_key = str(uuid.uuid4())[:8]
    req_data = {
        "request_key": req_key,
        "user": query.from_user.id,
        "user_id": query.from_user.id,
        "type": "series",
        "request_type": "series",
        "source": "SERIES_FILTER",
        "series_id": series_id,
        "full_id": series_id,
        "series_title": title,
        "title": title,
        "language": lang,
        "season": season,
        "episode": episode,
        "quality": qual,
        "files": files,
        "delivery_status": "pending",
        "state": "PENDING",
        "created_at": time.time()
    }
    if not hasattr(temp, "SERIES_STATE"):
        temp.SERIES_STATE = {}
    temp.SERIES_STATE[req_key] = req_data
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

    if query.message.chat.type == enums.ChatType.PRIVATE:
        await query.answer("🚀 Sending files...")
        await deliver_series_request(client, req_key, query.from_user.id, query=query)
        return

    try:
        return await query.answer(url=start_url)
    except Exception as e:
        logger.warning(f"[SERIES QUALITY ROUTING] query.answer(url=start_url) failed: {e}. Replying with fallback button.")
        ep_label = f" (S{season:02d}E{episode:02d})" if episode > 0 else f" (Season {season})"
        fb_msg = await query.message.reply_text(
            f"📩 Open bot to get your requested <b>{title}</b>{ep_label} ({qual}) files:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📂 Open Bot", url=start_url)]
            ])
        )
        from utils import schedule_filter_message_delete
        if fb_msg:
            schedule_filter_message_delete(client, fb_msg.chat.id, fb_msg.id, 600)
        return


@Client.on_callback_query(filters.regex(r"^ser_back#"))
async def ser_back_callback(client: Client, query: CallbackQuery):
    parts = query.data.split("#")
    if len(parts) < 5:
        return await query.answer("Invalid request.", show_alert=True)
    _, series_id, target, lang, key = parts[0], parts[1], parts[2], parts[3], parts[4]

    from plugins.pm_filter import is_button_owner
    is_owner, err_msg = is_button_owner(query, key)
    if not is_owner:
        return await query.answer(err_msg, show_alert=True)

    from database.series_db import get_series, list_series_languages
    series = await get_series(series_id)
    if not series:
        return await query.answer("⚠️ Series not found in database.", show_alert=True)

    name = series.get("name", "")
    year = str(series.get("year", ""))
    year_str = f" ({year})" if year and year != "N/A" else ""
    rating = str(series.get("rating", ""))
    rating_str = f"\n⭐ <b>Rating:</b> {rating}/10" if rating else ""
    genre = series.get("genre", "")
    genre_str = f"\n🎭 <b>Genre:</b> {genre}" if genre and genre != "N/A" else ""

    langs = await list_series_languages(series_id)
    if not langs:
        langs = series.get("languages", [])

    buttons = []
    preferred_order = ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English", "Dual Audio", "Multi Audio"]
    langs_sorted = sorted(langs, key=lambda x: (preferred_order.index(x) if x in preferred_order else 99, x))
    for i in range(0, len(langs_sorted), 2):
        row = []
        for l in langs_sorted[i:i+2]:
            row.append(InlineKeyboardButton(to_series_font(l), callback_data=f"ser_lang#{series_id}#{l}#{key}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"ser_close#{key}")])

    caption_text = (
        f"📺 <b>{name}{year_str}</b>"
        f"{rating_str}"
        f"{genre_str}\n\n"
        f"🌐 <b>Select Language:</b>"
    )
    markup = InlineKeyboardMarkup(buttons)
    try:
        if query.message.photo or query.message.caption:
            await query.message.edit_caption(caption=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.message.edit_text(text=caption_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^ser_close#"))
async def ser_close_callback(client: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Closed.")


async def deliver_series_request(client, req_key, user_id, query=None, timing=None):
    from utils import get_size, temp, schedule_filter_message_delete
    from database.series_db import get_temp_request
    import logging

    log = logging.getLogger(__name__)
    req = temp.SERIES_STATE.get(req_key) if hasattr(temp, "SERIES_STATE") else None
    if not req:
        req = temp.GETALL.get(req_key) if hasattr(temp, "GETALL") else None
    if not req:
        req = await get_temp_request(req_key)
    if not req:
        log.warning(f"[SERIES DELIVERY] Request expired or not found for req_key={req_key}")
        if query:
            await query.answer("⚠️ Request expired. Please search again.", show_alert=True)
        return

    files = req.get("files", [])
    if not files:
        if query:
            await query.answer("⚠️ No files found for this request.", show_alert=True)
        return

    title = req.get("series_title") or req.get("title") or "Series"
    lang = req.get("language")
    season = req.get("season")
    ep = req.get("episode")
    qual = req.get("quality")

    from plugins.commands import send_movie_files_to_user
    ep_str = f" S{season:02d}E{ep:02d}" if (season and ep and int(ep) > 0) else (f" Season {season}" if season else "")
    full_title = f"{title}{ep_str}"
    await send_movie_files_to_user(
        client=client,
        user_id=user_id,
        files=files,
        query=query,
        movie_title=full_title,
        language=lang,
        quality=qual
    )



