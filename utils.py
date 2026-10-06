# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client
from info import *
from imdb import Cinemagoer 
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from pyrogram.errors import *
from typing import Union
from Script import script
from datetime import datetime, date
from typing import List
from database.users_chats_db import db
from database.join_reqs import JoinReqs
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
print("### VJ UTILS RUNTIME BUILD = AM_DEBUG_20260825_V1 ###", flush=True)
print(f"### UTILS.PY PATH = {os.path.abspath(__file__)} ###", flush=True)
join_db = JoinReqs
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))")

try:
    imdb = Cinemagoer(uri="sqlite:///cinemagoer.db")
except Exception:
    try:
        imdb = Cinemagoer(uri="sqlite:////tmp/cinemagoer.db")
    except Exception:
        try:
            imdb = Cinemagoer(accessSystem="http")
        except Exception:
            imdb = Cinemagoer() 
TOKENS = {}
VERIFIED = {}
BANNED = {}
SECOND_SHORTENER = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

# temp db for banned 
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    BOT = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    SERIES_WIZARD = {}
    MOVIE_WIZARD = {}
    SERIES_STATE = {}
    AUTO_SERIES = {}
    AUTO_MOVIE = {}
    AUTO_MOVIE_BATCH = {}
    MOVIE_STATE = {}
    MOVIE_EDIT = {}
    WIZARD_SESSIONS = {}
    U_NAME = None
    B_NAME = None
    GETALL = {}
    SHORT = {}
    SETTINGS = {}
    IMDB_CAP = {}
    SERIES_PM_QUALITY_COOLDOWNS = {}
    YINDEX_RUNNING = {}
    YINDEX_CANCEL = {}
    YINDEX_SESSIONS = {}
    EPISODE_TITLES_CACHE = {}


def set_wizard_session(user_id: int, workflow: str, state: str, data: dict = None, chat_id: int = None):
    """
    Store or update an active wizard session for a user.
    workflow: 'AUTO_MOVIE' | 'AUTO_SERIES' | 'SERIES_WIZARD' | 'THUMBNAIL'
    state: e.g. 'WAIT_IMDB', 'SCANNING', 'RESULT', 'SAVING'
    """
    import time
    session_info = {
        "user_id": user_id,
        "chat_id": chat_id or user_id,
        "workflow": workflow,
        "state": state,
        "created_at": time.time(),
        "data": data or {}
    }
    temp.WIZARD_SESSIONS[user_id] = session_info
    logger.info(f"[SESSION SET] user_id={user_id} workflow={workflow} state={state}")
    return session_info


def get_wizard_session(user_id: int, max_age_seconds: int = 900) -> dict | None:
    """
    Retrieve active wizard session with automatic 15-minute stale session expiry.
    """
    import time
    sess = temp.WIZARD_SESSIONS.get(user_id)
    if not sess:
        # Fallback to legacy dictionary checks
        if getattr(temp, "AUTO_MOVIE", {}).get(user_id):
            mdata = temp.AUTO_MOVIE[user_id]
            return {"user_id": user_id, "workflow": "AUTO_MOVIE", "state": mdata.get("state", "UNKNOWN"), "data": mdata}
        if getattr(temp, "AUTO_MOVIE_BATCH", {}).get(user_id):
            bdata = temp.AUTO_MOVIE_BATCH[user_id]
            return {"user_id": user_id, "workflow": "SUPER_MOVIE_BATCH", "state": bdata.get("state", "UNKNOWN"), "data": bdata}
        if getattr(temp, "AUTO_SERIES", {}).get(user_id):
            sdata = temp.AUTO_SERIES[user_id]
            return {"user_id": user_id, "workflow": "AUTO_SERIES", "state": sdata.get("state", "UNKNOWN"), "data": sdata}
        if getattr(temp, "SERIES_WIZARD", {}).get(user_id):
            wdata = temp.SERIES_WIZARD[user_id]
            return {"user_id": user_id, "workflow": "SERIES_WIZARD", "state": wdata.get("state", "UNKNOWN"), "data": wdata}
        if getattr(temp, "MOVIE_WIZARD", {}).get(user_id):
            mdata = temp.MOVIE_WIZARD[user_id]
            return {"user_id": user_id, "workflow": "MANUAL_MOVIE", "state": mdata.get("state", "UNKNOWN"), "data": mdata}
        return None

    # Check timeout
    created_at = sess.get("created_at", 0)
    # If scanning or saving, allow longer timeout (30 min)
    effective_max = 1800 if sess.get("state") in ("SCANNING", "SAVING") else max_age_seconds
    if time.time() - created_at > effective_max:
        logger.info(f"[SESSION EXPIRED] user_id={user_id} workflow={sess.get('workflow')} state={sess.get('state')}")
        clear_wizard_session(user_id)
        return None

    return sess


def clear_wizard_session(user_id: int):
    """
    Completely clear all session states across all wizard containers for a user.
    """
    temp.WIZARD_SESSIONS.pop(user_id, None)
    if hasattr(temp, "AUTO_MOVIE") and isinstance(temp.AUTO_MOVIE, dict):
        temp.AUTO_MOVIE.pop(user_id, None)
        # Purge any session_id keys owned by this user
        keys_to_del = [
            k for k, v in list(temp.AUTO_MOVIE.items())
            if isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id)
        ]
        for k in keys_to_del:
            temp.AUTO_MOVIE.pop(k, None)
    if hasattr(temp, "AUTO_SERIES") and isinstance(temp.AUTO_SERIES, dict):
        temp.AUTO_SERIES.pop(user_id, None)
        keys_to_del = [
            k for k, v in list(temp.AUTO_SERIES.items())
            if isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id)
        ]
        for k in keys_to_del:
            temp.AUTO_SERIES.pop(k, None)
    if hasattr(temp, "AUTO_MOVIE_BATCH") and isinstance(temp.AUTO_MOVIE_BATCH, dict):
        temp.AUTO_MOVIE_BATCH.pop(user_id, None)
        keys_to_del = [
            k for k, v in list(temp.AUTO_MOVIE_BATCH.items())
            if isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id)
        ]
        for k in keys_to_del:
            temp.AUTO_MOVIE_BATCH.pop(k, None)
    if hasattr(temp, "SERIES_WIZARD") and isinstance(temp.SERIES_WIZARD, dict):
        temp.SERIES_WIZARD.pop(user_id, None)
    if hasattr(temp, "MOVIE_WIZARD") and isinstance(temp.MOVIE_WIZARD, dict):
        temp.MOVIE_WIZARD.pop(user_id, None)
    if hasattr(temp, "SETTING_SERIES_THUMB") and isinstance(temp.SETTING_SERIES_THUMB, dict):
        temp.SETTING_SERIES_THUMB.pop(user_id, None)
    logger.info(f"[SESSION CLEARED] user_id={user_id}")


def cancel_wizard_session(user_id: int) -> str | None:
    """
    Cancel active session and return the cancelled workflow type name.
    """
    sess = get_wizard_session(user_id)
    workflow = None
    if sess:
        workflow = sess.get("workflow")
    elif hasattr(temp, "SETTING_SERIES_THUMB") and temp.SETTING_SERIES_THUMB.get(user_id):
        workflow = "THUMBNAIL"
    elif hasattr(temp, "AUTO_MOVIE_BATCH") and (user_id in temp.AUTO_MOVIE_BATCH or any(isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id) for v in temp.AUTO_MOVIE_BATCH.values())):
        workflow = "SUPER_MOVIE_BATCH"
    elif hasattr(temp, "AUTO_MOVIE") and (user_id in temp.AUTO_MOVIE or any(isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id) for v in temp.AUTO_MOVIE.values())):
        workflow = "AUTO_MOVIE"
    elif hasattr(temp, "AUTO_SERIES") and (user_id in temp.AUTO_SERIES or any(isinstance(v, dict) and (v.get("user_id") == user_id or v.get("admin_id") == user_id) for v in temp.AUTO_SERIES.values())):
        workflow = "AUTO_SERIES"
    elif hasattr(temp, "SERIES_WIZARD") and temp.SERIES_WIZARD.get(user_id):
        workflow = "SERIES_WIZARD"

    clear_wizard_session(user_id)
    if workflow:
        logger.info(f"[CANCEL WIZARD] user_id={user_id} workflow={workflow}")
    return workflow


_RE_RES = re.compile(r'(?i)\b(2160|1440|1080|720|576|480|360|240)p?\b')
_RE_CODEC = re.compile(r'(?i)\b(x264|x265|h264|h265|hevc|avc|10bit|8bit|ddp?5\.1|dd5\.1|7\.1|2\.0)\b')
_RE_AUDIO_CH = re.compile(r'(?i)\b(5\.1|7\.1|2\.0)\b')
_RE_YEAR = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')
_RE_EXT = re.compile(r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|zip|rar)$", flags=re.I)
_RE_URL = re.compile(r"(?i)https?://\S+|www\.\S+|@\w+|t\.me/\S+")
_RE_DELIMS = re.compile(r"[\._\-\+\[\]\(\)\{\}:;!?,/\\~|#*\"\'`]")
_RE_TECH_PATTERNS = [
    re.compile(r"\b(2160p|1440p|1080p|720p|576p|480p|360p|240p|4k|2k|uhd|fhd|hd|sd)\b", re.I),
    re.compile(r"\b(bluray|bdrip|brrip|web-dl|webdl|web-rip|webrip|hdrip|hdtv|dvdrip|dvd|vcd|vcdr|camrip|hdcam|web\s*dl|web\s*rip|hd\s*rip|bd\s*rip|br\s*rip|dvd\s*rip|cam\s*rip)\b", re.I),
    re.compile(r"\b(hevc|x264|x265|h264|h265|avc|10bit|8bit|hdr|hdr10|hdr10plus|hdr10\+|dv|dolby\s*vision|sdr)\b", re.I),
    re.compile(r"\b(aac|aac2\.0|aac\s*2\s*0|ac3|eac3|ddp|ddp5\.1|ddp\s*5\s*1|dd5\.1|dd\s*5\s*1|dts|dts-hd|dts\s*hd|truehd|atmos|mp3|flac|5\s*1|7\s*1|2\s*0)\b", re.I),
    re.compile(r"\b(esub|esubs|sub|subs|subtitles|english\s*subtitle|english\s*subtitles|multi\s*sub)\b", re.I),
    re.compile(r"\b(nf|amzn|dsnp|hotstar|zee5|sonyliv|aha|sunnxt|mx|voot|prime|hulu|max|apple|atvp|lionsgate)\b", re.I),
    re.compile(r"\b(proper|repack|unrated|directors\s*cut|extended|remastered|imax)\b", re.I),
    re.compile(r"\b(malayalam|tamil|telugu|hindi|kannada|english|bengali|marathi|punjabi|gujarati)\b", re.I),
    re.compile(r"\b(dual\s*audio|multi\s*audio|org\s*audio|clean\s*audio|line\s*audio|hq\s*audio|dual|multi|org|clean|hq|line)\b", re.I),
]
_RE_SERIES_TOKENS = re.compile(r"(?i)\b(?:s\d{1,2}[\s\.\-_]?e\d{1,4}|\d{1,2}x\d{1,4}|(?:season|series)\s*\d{1,2}|ep(?:isode)?\s*\d{1,4})\b")
_ROMAN_MAP = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def extract_release_year(filename: str, caption: str = None) -> str | None:
    """
    Extracts a 4-digit release year (1900-2099) from a filename or caption.
    Avoids mistaking resolutions (1080, 720, 2160, 480), codecs (x264, x265),
    or audio channel configurations (5.1, 7.1) for release years.
    """
    fn_clean = strip_file_prefix_markers(filename or "")
    cap_clean = strip_file_prefix_markers(caption or "")
    text = f"{fn_clean} {cap_clean}"
    if not text.strip():
        return None

    cleaned = _RE_RES.sub(' ', text)
    cleaned = _RE_CODEC.sub(' ', cleaned)
    cleaned = _RE_AUDIO_CH.sub(' ', cleaned)

    matches = _RE_YEAR.findall(cleaned)
    if matches:
        return matches[-1]
    return None


def normalize_title_for_matching(text: str) -> str:
    """
    Normalizes a movie or series title or filename for strict identity matching.
    Strips technical tokens, resolutions, codecs, sources, extensions, bracket tags, and years,
    while PRESERVING meaningful sequel/chapter/part/season numbers (e.g. '2', '3', 'ii', 'iii', 'chapter 2', 'part 2').
    """
    if not text:
        return ""
    
    t = str(text).strip()
    # 1. Remove file extensions
    t = _RE_EXT.sub("", t)
    # 2. Remove URLs, handles, invites
    t = _RE_URL.sub(" ", t)
    # 3. Remove bracketed noise like [430.34 MB], [mwkOTT], [TG], [VJ], @name
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"\{[^\}]*\}", " ", t)
    t = re.sub(r"@\w+", " ", t)
    t = re.sub(r"(?i)\b\d+(?:\.\d+)?\s*(?:gb|mb|kb)\b", " ", t)

    # 4. Replace delimiters with spaces
    t = _RE_DELIMS.sub(" ", t)

    # 5. Remove technical patterns (resolutions, codecs, sources, audios, languages)
    for pat in _RE_TECH_PATTERNS:
        t = pat.sub(" ", t)

    # 6. Remove 4-digit years
    t = _RE_YEAR.sub(" ", t)

    words = t.lower().split()
    norm_words = [_ROMAN_MAP.get(w, w) for w in words]
    return " ".join(norm_words).strip()


TMDB_LANGUAGE_CODE_MAP = {
    "en": "English", "eng": "English", "english": "English",
    "ml": "Malayalam", "mal": "Malayalam", "malayalam": "Malayalam", "malayala": "Malayalam",
    "hi": "Hindi", "hin": "Hindi", "hindi": "Hindi",
    "ta": "Tamil", "tam": "Tamil", "tamil": "Tamil",
    "te": "Telugu", "tel": "Telugu", "telugu": "Telugu",
    "kn": "Kannada", "kan": "Kannada", "kannada": "Kannada",
    "bn": "Bengali", "ben": "Bengali", "bengali": "Bengali",
    "mr": "Marathi", "mar": "Marathi", "marathi": "Marathi",
    "pa": "Punjabi", "pun": "Punjabi", "punjabi": "Punjabi",
    "gu": "Gujarati", "guj": "Gujarati", "gujarati": "Gujarati",
    "ur": "Urdu", "urd": "Urdu", "urdu": "Urdu",
    "or": "Odia", "ori": "Odia", "oriya": "Odia", "odia": "Odia",
    "de": "German", "ger": "German", "german": "German",
    "ko": "Korean", "kor": "Korean", "korean": "Korean",
    "ja": "Japanese", "jap": "Japanese", "jpn": "Japanese", "japanese": "Japanese",
    "es": "Spanish", "spa": "Spanish", "spanish": "Spanish",
    "fr": "French", "fre": "French", "fra": "French", "french": "French",
    "ar": "Arabic", "ara": "Arabic", "arabic": "Arabic",
    "ru": "Russian", "rus": "Russian", "russian": "Russian",
    "zh": "Chinese", "chi": "Chinese", "zho": "Chinese", "chinese": "Chinese", "cn": "Chinese",
    "it": "Italian", "ita": "Italian", "italian": "Italian",
    "pt": "Portuguese", "por": "Portuguese", "portuguese": "Portuguese",
    "tr": "Turkish", "tur": "Turkish", "turkish": "Turkish",
    "th": "Thai", "thai": "Thai",
    "id": "Indonesian", "ind": "Indonesian", "indonesian": "Indonesian",
    "ms": "Malay", "may": "Malay", "msa": "Malay", "malay": "Malay",
    "vi": "Vietnamese", "vie": "Vietnamese", "vietnamese": "Vietnamese",
    "fa": "Persian", "fas": "Persian", "per": "Persian", "persian": "Persian",
    "pl": "Polish", "pol": "Polish", "polish": "Polish",
    "nl": "Dutch", "dut": "Dutch", "nld": "Dutch", "dutch": "Dutch",
    "sv": "Swedish", "swe": "Swedish", "swedish": "Swedish",
    "no": "Norwegian", "nor": "Norwegian", "norwegian": "Norwegian",
    "da": "Danish", "dan": "Danish", "danish": "Danish",
    "fi": "Finnish", "fin": "Finnish", "finnish": "Finnish",
    "he": "Hebrew", "heb": "Hebrew", "hebrew": "Hebrew",
    "el": "Greek", "gre": "Greek", "ell": "Greek", "greek": "Greek",
    "cs": "Czech", "cze": "Czech", "ces": "Czech", "czech": "Czech",
    "hu": "Hungarian", "hun": "Hungarian", "hungarian": "Hungarian",
    "ro": "Romanian", "rum": "Romanian", "ron": "Romanian", "romanian": "Romanian",
    "uk": "Ukrainian", "ukr": "Ukrainian", "ukrainian": "Ukrainian",
    "tl": "Tagalog", "tgl": "Tagalog", "tagalog": "Tagalog",
}

def normalize_language_name(lang_val: str | None) -> str | None:
    """
    Normalizes any language string or ISO code (e.g. 'en', 'ml', 'Korean', 'hi')
    into its standardized full English language name (e.g. 'English', 'Malayalam', 'Korean', 'Hindi').
    """
    if not lang_val:
        return None
    cleaned = str(lang_val).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
    if not cleaned:
        return None
    if cleaned in TMDB_LANGUAGE_CODE_MAP:
        return TMDB_LANGUAGE_CODE_MAP[cleaned]
    return str(lang_val).strip().title()


def extract_tmdb_posters_from_html(html_content: str, primary_poster: str = None) -> list[str]:
    """
    Extracts all unique, valid TMDB poster image URLs (w500) from TMDB HTML webpage.
    Preserves primary_poster as the first element if provided.
    """
    posters = []
    seen_filenames = set()

    if primary_poster and str(primary_poster).strip() and str(primary_poster).strip().upper() != "N/A":
        clean_p = str(primary_poster).strip()
        if clean_p.startswith("//"):
            clean_p = "https:" + clean_p
        posters.append(clean_p)
        m_fn = re.search(r'([a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp))', clean_p, re.I)
        if m_fn:
            seen_filenames.add(m_fn.group(1).lower())

    if not html_content:
        return posters

    # Pattern 1: Fully qualified or protocol-relative TMDB image paths
    pattern1 = r'(?:https?:)?//(?:image|media)\.themoviedb\.org/t/p/[^"\'\s<>]+/([a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp))'
    matches = list(re.findall(pattern1, html_content, re.IGNORECASE))
    
    # Pattern 2: Relative paths /t/p/...
    pattern2 = r'/t/p/(?:w\d+|original|w\d+_and_h\d+[^/]*)/([a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp))'
    matches.extend(re.findall(pattern2, html_content, re.IGNORECASE))

    for img_fn in matches:
        fn_clean = img_fn.strip()
        fn_lower = fn_clean.lower()
        if any(skip in fn_lower for skip in ("avatar", "gravatar", "logo", "icon", "blank", "default", "backdrop")):
            continue
        if fn_lower in seen_filenames:
            continue
        seen_filenames.add(fn_lower)
        poster_url = f"https://image.themoviedb.org/t/p/w500/{fn_clean}"
        posters.append(poster_url)
        if len(posters) >= 12:
            break

    return posters


def get_random_filter_poster(filter_data: dict | None) -> str | None:
    """
    Randomly selects ONE valid poster from a Movie or Series filter document.
    Priority:
    1. If 'posters' array exists and contains non-empty valid poster entries, randomly pick one.
    2. Fallback to single 'poster' field if present and valid.
    3. Return None if no valid poster is available.
    """
    if not filter_data or not isinstance(filter_data, dict):
        return None

    posters = filter_data.get("posters")
    if isinstance(posters, list) and posters:
        valid_posters = []
        for p in posters:
            if isinstance(p, dict):
                p_val = str(p.get("file_id") or p.get("url") or "").strip()
            else:
                p_val = str(p).strip()
            if p_val and p_val.upper() != "N/A":
                valid_posters.append(p_val)
        if valid_posters:
            import random
            return random.choice(valid_posters)

    single_poster = str(filter_data.get("poster") or "").strip()
    if single_poster and single_poster.upper() != "N/A":
        return single_poster

    return None


def strip_file_prefix_markers(text: str) -> str:
    """
    Strips recognized leading prefix markers from the beginning of a filename or caption.
    Recognized leading markers:
      - @username / @channel (e.g. @Rocky_links, @movie_channel)
      - (MM) or [MM] or {MM} (case-insensitive)
      - (MS) or [MS] or {MS} (case-insensitive)
    
    Rules:
      - Removes ONLY leading markers from the beginning of the string.
      - Can remove multiple leading markers in sequence (e.g. '@Rocky_links (MM) Love 2026.mkv').
      - Preserves everything else in the filename/caption exactly.
      - Never removes markers that appear in the middle of the string (e.g. 'Love (MM) 2026.mkv').
    """
    if not text:
        return ""
    
    cleaned = str(text).strip()
    prefix_pattern = re.compile(
        r"^(?:"
        r"@[a-zA-Z0-9_]+"                          # @username
        r"|[\(\[\{]\s*M[MS]\s*[\)\]\}]"            # (MM), [MM], {MM}, (MS), [MS], {MS}
        r")[\s\._\-\+]*",
        flags=re.IGNORECASE
    )
    
    while True:
        m = prefix_pattern.match(cleaned)
        if not m:
            break
        cleaned = cleaned[m.end():].lstrip(" ._+-")
    
    return cleaned.strip()


def get_filter_button_filename_text(file_name: str) -> str:
    """
    Returns a clean shortened display filename for normal movie/series filter buttons.
    Priority:
    1. If a valid standalone year (1900-2099) exists: show everything from the start up to and including the year.
    2. If NO year but a recognized quality marker exists: show everything before the quality marker.
    3. If NEITHER year nor quality: show everything before the file extension.
    """
    if not file_name:
        return ""
    
    raw = str(file_name).strip()
    
    # 1. Strip leading prefix markers (@username, (MM), [MM], (MS), [MS])
    raw = strip_file_prefix_markers(raw)
    
    # 2. Strip only the final actual file extension
    raw = re.sub(
        r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|3gp|mpeg|mpg|vob|ogv|divx|m2ts|m2v|f4v|srt|sub|zip|rar)$",
        "",
        raw,
        flags=re.IGNORECASE
    ).strip()
    
    if not raw:
        return str(file_name).strip()

    # Priority 1: Standalone year 1900-2099
    year_iter = list(re.finditer(r"(?<![0-9a-zA-Z])(19\d{2}|20\d{2})(?![0-9a-zA-Z])", raw))
    if year_iter:
        for ym in year_iter:
            y_start = ym.start()
            y_end = ym.end()
            # Avoid matching if followed by 'p' or 'i' (e.g. 1080p, 2160p)
            if y_end < len(raw) and raw[y_end].lower() in ('p', 'i', 'k'):
                continue
            # Avoid matching if preceded by 'x' (e.g. 1920x1080)
            if y_start > 0 and raw[y_start - 1].lower() == 'x':
                continue
            
            prefix_part = raw[:y_end]
            cleaned = re.sub(r'[\._]', ' ', prefix_part)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            cleaned = re.sub(r'[\-\:\+]+$', '', cleaned).strip()
            if cleaned:
                return cleaned

    # Priority 2: Recognized quality marker (when no year is present)
    qual_pattern = re.compile(
        r"(?i)(?:^|[\s\._\-\(\[\{])("
        r"2160p|4k|uhd|1440p|2k|1080p|1080i|fhd|720p|576p|576i|480p|480i|360p|240p|hd|"
        r"web[\s\._\-]?dl|web[\s\._\-]?rip|web[\s\._\-]?hd|bluray|bdrip|brrip|hdrip|hdtv|dvdrip|dvd|camrip|hdcam|cam|"
        r"hevc|x264|x265|h264|h265|avc|10bit|8bit"
        r")(?:[\s\._\-\)\]\}]|$)"
    )
    qm = qual_pattern.search(raw)
    if qm:
        prefix_part = raw[:qm.start(1)].strip()
        cleaned = re.sub(r'[\._]', ' ', prefix_part)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'[\-\:\+]+$', '', cleaned).strip()
        if cleaned:
            return cleaned

    # Priority 3: Neither year nor quality
    cleaned = re.sub(r'[\._]', ' ', raw)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'[\-\:\+]+$', '', cleaned).strip()
    return cleaned or raw


def get_series_filter_button_text(file_name: str, file_size=None) -> str:
    """
    Returns formatted button label for normal series filter file buttons:
    Format: (FILE SIZE) [SxxEyy] SERIES/EPISODE NAME
    Example: (300 MB) [S01E03] Killadi

    If SxxEyy cannot be detected, falls back to: [FILE SIZE] CLEAN_FILENAME
    """
    if not file_name:
        return ""

    raw = str(file_name).strip()
    # 1. Format size string
    if file_size is not None:
        if isinstance(file_size, (int, float)):
            sz_str = get_size(file_size)
        else:
            sz_str = str(file_size).strip()
    else:
        sz_str = ""

    # 2. Strip leading prefix markers (@username, (MM), [MM], (MS), [MS])
    clean_unprefixed = strip_file_prefix_markers(raw)

    # 3. Strip file extensions
    name_no_ext = re.sub(
        r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|3gp|mpeg|mpg|vob|ogv|divx|m2ts|m2v|f4v|srt|sub|zip|rar)$",
        "",
        clean_unprefixed,
        flags=re.IGNORECASE
    ).strip()

    # 4. Extract Season & Episode (SxxEyy)
    patterns = [
        re.compile(r"(?i)(?:^|[\s._\-\(\[\{])S(\d{1,2})\s*[\.\-_ ]?\s*E(\d{1,4})(?:[\s._\-\)\]\}]|$)"),
        re.compile(r"(?i)(?:^|[\s._\-\(\[\{])(\d{1,2})\s*x\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)"),
        re.compile(r"(?i)(?:^|[\s._\-\(\[\{])(?:Season|S)\s*(\d{1,2})\s*[\.\-_ ]?\s*(?:Episode|Ep|E)\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)"),
    ]

    m_se = None
    s_val = None
    ep_val = None
    for p in patterns:
        m = p.search(name_no_ext)
        if m:
            try:
                s_val = int(m.group(1))
                ep_val = int(m.group(2))
                m_se = m
                break
            except Exception:
                pass

    # Fallback if no valid SxxEyy found
    if not m_se or s_val is None or ep_val is None or s_val <= 0 or ep_val <= 0:
        short_fn = get_filter_button_filename_text(file_name)
        if sz_str:
            return f"[{sz_str}] {short_fn}"
        return short_fn

    s_tag = f"S{s_val:02d}E{ep_val:02d}"

    # 5. Extract series display name before SxxEyy
    cand_prefix = name_no_ext[:m_se.start()].strip(" ._+-")
    if cand_prefix:
        cleaned_title = get_filter_button_filename_text(cand_prefix)
    else:
        # If filename started with SxxEyy, check remaining part
        cand_suffix = name_no_ext[m_se.end():].strip(" ._+-")
        cleaned_title = get_filter_button_filename_text(cand_suffix)

    if not cleaned_title:
        cleaned_title = "Series"

    if sz_str:
        return f"({sz_str}) [{s_tag}] {cleaned_title}"
    return f"[{s_tag}] {cleaned_title}"


def normalize_series_identity_title(text: str) -> str:
    """
    Normalizes a series title for strict identity comparison.
    Lowercases, unifies unicode, replaces punctuation (. _ - [ ] etc.) with spaces,
    and collapses whitespace.
    DOES NOT strip meaningful words like 'The', 'Real', 'Love', 'Ishq', 'Starts', 'Today', etc.
    """
    if not text:
        return ""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(text))
    t = t.lower()
    t = re.sub(r"[\._\-\+\[\]\(\)\{\}:;!?,/\\~|#*\"\'`]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def match_automatic_series_file(
    target_series_name: str,
    target_year: str | int = None,
    filename: str = "",
    caption: str = "",
    target_season: int = None,
    original_language: str = None,
    target_aliases: list = None
) -> dict:
    """
    Strict authoritative Automatic Series file matcher.
    Rule:
      Filename structure: {EXACT SERIES NAME} [YEAR] {SxxEyy} [YEAR] {METADATA}
      - ONLY the text BEFORE the SxxEyy boundary represents the candidate series name.
      - A standalone 4-digit release year (1900-2099) may appear EITHER BEFORE OR AFTER
        the SxxEyy marker and MUST NOT become part of the series name.
      - If a year is detected in filename and target_year is specified, they must match.
      - If no year in filename, exact normalized title + SxxEyy is accepted.
    """
    # Handle flexible positional argument calling: match_automatic_series_file(target, filename, ...)
    if isinstance(target_year, str) and (
        any(target_year.lower().endswith(ext) for ext in [".mkv", ".mp4", ".avi", ".mov", ".webm", ".ts", ".flv", ".m4v", ".3gp"])
        or (not filename and ("." in target_year or " " in target_year or "s0" in target_year.lower()))
    ):
        filename = target_year
        target_year = None

    if not filename:
        return {"matched": False, "status": "invalid", "reason": "empty_filename"}

    from utils import is_video_file, is_subtitle_file
    if not is_video_file(filename) or is_subtitle_file(filename):
        return {"matched": False, "status": "invalid", "reason": "not_a_video_file"}

    raw_name = str(filename).strip()
    # Strip file extensions
    name_no_ext = re.sub(
        r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|3gp|mpeg|mpg|vob|ogv|divx|m2ts|m2v|f4v)$",
        "",
        raw_name,
        flags=re.IGNORECASE
    ).strip()

    # Strip recognized leading prefix markers (@username, (MM), [MM], (MS), [MS], etc.)
    unprefixed_name = strip_file_prefix_markers(name_no_ext)

    # Remove remaining standalone usernames / URL links
    cleaned_name = ' '.join(
        filter(
            lambda x: not x.startswith('@') and not x.startswith('http://') and not x.startswith('https://') and not x.startswith('www.') and not x.startswith('t.me/'),
            unprefixed_name.split()
        )
    )

    # Search for Season/Episode marker boundary
    # Pattern 1: Standard S01E01 / S1E1 / S01.E01 / S01-E01 / S01_E01 / S01 E01 / S1 E1
    m1 = re.search(r"(?i)(?:^|[\s._\-\(\[\{])S(\d{1,3})\s*[\.\-_ ]?\s*E(\d{1,4})(?:[\s._\-\)\]\}]|$)", cleaned_name)
    # Pattern 2: Cross notation 01x01 / 1x01
    m2 = re.search(r"(?i)(?:^|[\s._\-\(\[\{])(\d{1,3})\s*x\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)", cleaned_name)
    # Pattern 3: Season 1 Episode 1 / Season 01 Ep 01 / Season 1 - 01
    m3 = re.search(r"(?i)(?:^|[\s._\-\(\[\{])(?:Season|S)\s*(\d{1,3})\s*[\.\-_ ]?\s*(?:Episode|Ep|E)\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)", cleaned_name)
    # Pattern 4: Separate Season ... Episode
    m4 = re.search(r"(?i)(?:^|[\s._\-\(\[\{])(?:Season|S)\s*(\d{1,3})\b.*?\b(?:Episode|Ep|E)\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)", cleaned_name)
    # Pattern 5: Standalone Episode: Ep 01 / Episode 01 / E01
    m5 = re.search(r"(?i)(?:^|[\s._\-\(\[\{])(?:Episode|Ep|E)\s*(\d{1,4})(?:[\s._\-\)\]\}]|$)", cleaned_name)

    boundary_start = -1
    boundary_end = -1
    season_val = 1
    episode_val = None

    if m1:
        boundary_start = m1.start()
        boundary_end = m1.end()
        season_val = int(m1.group(1))
        episode_val = int(m1.group(2))
    elif m2:
        boundary_start = m2.start()
        boundary_end = m2.end()
        season_val = int(m2.group(1))
        episode_val = int(m2.group(2))
    elif m3:
        boundary_start = m3.start()
        boundary_end = m3.end()
        season_val = int(m3.group(1))
        episode_val = int(m3.group(2))
    elif m4:
        boundary_start = m4.start()
        boundary_end = m4.end()
        season_val = int(m4.group(1))
        episode_val = int(m4.group(2))
    elif m5:
        boundary_start = m5.start()
        boundary_end = m5.end()
        season_val = target_season if target_season is not None else 1
        episode_val = int(m5.group(1))

    if episode_val is None or episode_val <= 0 or boundary_start < 0:
        return {
            "matched": False,
            "status": "invalid",
            "series": target_series_name,
            "reason": "missing_season_or_episode"
        }

    # Extract text strictly BEFORE SxxEyy marker
    candidate_raw = cleaned_name[:boundary_start].strip()
    remaining_text = cleaned_name[boundary_end:].strip()

    # Standalone 4-digit year detector (1900-2099)
    YEAR_REGEX = re.compile(r"(?i)(?<![0-9a-zA-Z])(19\d{2}|20\d{2})(?![0-9a-zA-Z])")

    detected_year = None
    candidate_series_name = candidate_raw

    # Check if a standalone year is present before the SxxEyy marker
    cand_year_matches = list(YEAR_REGEX.finditer(candidate_raw))
    norm_target = normalize_series_identity_title(target_series_name)

    valid_targets = {norm_target}
    if target_aliases and isinstance(target_aliases, (list, set, tuple)):
        for a in target_aliases:
            na = normalize_series_identity_title(a)
            if na:
                valid_targets.add(na)

    # Check if stripping year from candidate_raw matches target title
    title_matched = False
    if cand_year_matches:
        # Check from last found year match before marker
        for ym in reversed(cand_year_matches):
            y_val = int(ym.group(1))
            cand_without_year = (candidate_raw[:ym.start()] + " " + candidate_raw[ym.end():]).strip()
            norm_without_year = normalize_series_identity_title(cand_without_year)
            if norm_without_year in valid_targets:
                candidate_series_name = cand_without_year
                detected_year = y_val
                title_matched = True
                break

    if not title_matched:
        # Check direct candidate_raw without year stripping
        norm_candidate = normalize_series_identity_title(candidate_raw)
        if norm_candidate in valid_targets:
            candidate_series_name = candidate_raw
            title_matched = True

    # If year wasn't found before SxxEyy marker, check remaining_text / filename
    if detected_year is None:
        rem_year_matches = list(YEAR_REGEX.finditer(remaining_text))
        if rem_year_matches:
            detected_year = int(rem_year_matches[0].group(1))

    # Parse target year requirement if provided
    req_year = None
    if target_year and str(target_year).strip() not in ["N/A", "None", "0", ""]:
        try:
            req_year = int(str(target_year).strip())
        except (ValueError, TypeError):
            req_year = None

    if not title_matched or not normalize_series_identity_title(candidate_series_name):
        reason = f"series_name_mismatch: '{candidate_raw}' != '{target_series_name}'"
        logger.debug(
            f"[AUTO SERIES MATCH REJECT] "
            f"target_series={target_series_name!r} "
            f"candidate_series={candidate_series_name!r} "
            f"target_year={req_year!r} "
            f"detected_year={detected_year!r} "
            f"season={season_val!r} "
            f"episode={episode_val!r} "
            f"filename={filename!r} "
            f"reason={reason}"
        )
        return {
            "matched": False,
            "status": "invalid",
            "series": target_series_name,
            "series_name": candidate_series_name,
            "year": detected_year,
            "season": season_val,
            "episode": episode_val,
            "reason": reason
        }

    # Year validation if both target_year and detected_year exist
    if req_year is not None and detected_year is not None and detected_year != req_year:
        reason = f"year_mismatch: file year {detected_year} != target year {req_year}"
        logger.debug(
            f"[AUTO SERIES MATCH REJECT] "
            f"target_series={target_series_name!r} "
            f"candidate_series={candidate_series_name!r} "
            f"target_year={req_year!r} "
            f"detected_year={detected_year!r} "
            f"season={season_val!r} "
            f"episode={episode_val!r} "
            f"filename={filename!r} "
            f"reason={reason}"
        )
        return {
            "matched": False,
            "status": "invalid",
            "series": target_series_name,
            "series_name": candidate_series_name,
            "year": detected_year,
            "season": season_val,
            "episode": episode_val,
            "reason": reason
        }

    # Target season filter check if specified
    if target_season is not None and int(season_val) != int(target_season):
        reason = f"season_{season_val}_not_target_{target_season}"
        logger.debug(
            f"[AUTO SERIES MATCH REJECT] "
            f"target_series={target_series_name!r} "
            f"candidate_series={candidate_series_name!r} "
            f"target_year={req_year!r} "
            f"detected_year={detected_year!r} "
            f"season={season_val!r} "
            f"episode={episode_val!r} "
            f"filename={filename!r} "
            f"reason={reason}"
        )
        return {
            "matched": False,
            "status": "other_season",
            "series": target_series_name,
            "series_name": candidate_series_name,
            "year": detected_year,
            "season": season_val,
            "episode": episode_val,
            "remaining_text": remaining_text,
            "reason": reason
        }

    # Metadata extraction strictly from remaining_text / filename
    from utils import extract_quality_from_filename
    from plugins.pm_filter import resolve_file_language

    detected_quality = extract_quality_from_filename(remaining_text or raw_name)
    detected_lang = resolve_file_language(
        remaining_text or raw_name,
        caption=caption,
        metadata={"original_language": original_language},
        default_fallback="English"
    )

    return {
        "matched": True,
        "status": "matched",
        "series": target_series_name,
        "series_name": candidate_series_name,
        "year": detected_year,
        "season": season_val,
        "episode": episode_val,
        "quality": detected_quality,
        "language": detected_lang,
        "remaining_text": remaining_text,
        "reason": "exact_identity_match"
    }


def extract_quality_from_filename(filename: str) -> str:
    """Extract resolution / quality tag from media filename."""
    if not filename:
        return "Unknown"
    from plugins.series import extract_quality_from_filename as _eq
    try:
        return _eq(filename)
    except Exception:
        m = re.search(r"(?i)\b(2160p|4k|1440p|2k|1080p|720p|480p|360p|240p|hdrip|bluray|web-dl|webdl|webrip|dvdrip|hevc)\b", filename)
        return m.group(1).upper() if m else "Unknown"


VIDEO_EXTENSIONS = (
    ".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv", ".wmv",
    ".m4v", ".ts", ".3gp", ".mpeg", ".mpg", ".vob", ".ogv",
    ".divx", ".m2ts", ".m2v", ".f4v"
)
SUBTITLE_EXTENSIONS = (
    ".srt", ".vtt", ".sub", ".ass", ".ssa", ".idx", ".sup", ".smi"
)
RAW_VIDEO_EXTS = {ext.lstrip(".") for ext in VIDEO_EXTENSIONS}
RAW_SUBTITLE_EXTS = {ext.lstrip(".") for ext in SUBTITLE_EXTENSIONS}
NON_VIDEO_EXTS = {
    "mp3", "flac", "wav", "m4a", "aac", "ogg", "wma", "opus",
    "pdf", "apk", "zip", "rar", "7z", "tar", "gz", "iso",
    "txt", "docx", "doc", "epub", "srt", "vtt", "sub", "ass", "ssa", "idx", "sup", "smi",
    "jpg", "jpeg", "png", "webp", "gif", "exe"
}

def is_subtitle_file(file_obj_or_name) -> bool:
    """Returns True if the given file object or name is a subtitle file."""
    if not file_obj_or_name:
        return False
    if hasattr(file_obj_or_name, "document"):
        doc = getattr(file_obj_or_name, "document", None)
        if doc:
            mime = str(getattr(doc, "mime_type", "")).lower()
            if mime == "application/x-subrip" or "subtitle" in mime:
                return True
            fname = str(getattr(doc, "file_name", "") or getattr(file_obj_or_name, "caption", "") or "")
        else:
            fname = str(getattr(file_obj_or_name, "caption", "") or "")
    elif isinstance(file_obj_or_name, dict):
        mime = str(file_obj_or_name.get("mime_type", "")).lower()
        if mime == "application/x-subrip" or "subtitle" in mime:
            return True
        fname = file_obj_or_name.get("file_name", "") or file_obj_or_name.get("caption", "") or ""
    else:
        fname = str(file_obj_or_name)

    fname_lower = fname.strip().lower()
    if not fname_lower:
        return False
    if any(fname_lower.endswith(ext) for ext in SUBTITLE_EXTENSIONS):
        return True
    tokens = fname_lower.replace(".", " ").split()
    if tokens and tokens[-1] in RAW_SUBTITLE_EXTS:
        return True
    return False

def is_video_file(file_obj_or_name) -> bool:
    """Returns True if the file is a recognized video file (.mkv, .mp4, .avi, etc. or video object/mime/name)."""
    if not file_obj_or_name:
        return False
    if is_subtitle_file(file_obj_or_name):
        return False
    if hasattr(file_obj_or_name, "video") and getattr(file_obj_or_name, "video", None):
        return True
    if hasattr(file_obj_or_name, "document"):
        doc = getattr(file_obj_or_name, "document", None)
        if doc:
            mime = str(getattr(doc, "mime_type", "")).lower()
            if mime.startswith("video/"):
                return True
            fname = str(getattr(doc, "file_name", "") or getattr(file_obj_or_name, "caption", "") or "")
        else:
            fname = str(getattr(file_obj_or_name, "caption", "") or "")
    elif isinstance(file_obj_or_name, dict):
        mime = str(file_obj_or_name.get("mime_type", "")).lower()
        ftype = str(file_obj_or_name.get("file_type", "")).lower()
        if ftype == "video" or mime.startswith("video/"):
            return True
        fname = file_obj_or_name.get("file_name", "") or file_obj_or_name.get("caption", "") or ""
    else:
        fname = str(file_obj_or_name)

    fname_lower = fname.strip().lower()
    if not fname_lower:
        return False

    # Check extension with dot (e.g. .mkv, .mp4)
    if any(fname_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return True

    # Check space-separated tokens or cleaned extensions (e.g. "Interstellar 2014 1080p mkv")
    tokens = fname_lower.replace(".", " ").split()
    if tokens:
        if tokens[-1] in RAW_VIDEO_EXTS:
            return True
        if tokens[-1] in NON_VIDEO_EXTS:
            return False

    # If the file has video tags / resolution indicators and is not non-video
    if re.search(r"(?i)\b(s\d{1,2}[\s\.\-_]?e\d{1,4}|\d{1,2}x\d{1,4}|ep\d+|2160p|4k|1440p|2k|1080p|720p|480p|360p|240p|bluray|web-dl|webdl|webrip|dvdrip|hevc|x264|x265|h264|h265)\b", fname_lower):
        return True

    # Fallback: Check if any token is a known video extension
    if any(tok in RAW_VIDEO_EXTS for tok in tokens):
        return True

    return True


def normalize_movie_identity_title(text: str) -> str:
    """
    Normalizes a movie title for strict identity comparison.
    Lowercases, unifies unicode, replaces punctuation (. _ - [ ] etc.) with spaces,
    and collapses whitespace.
    DOES NOT strip meaningful words like 'The', 'Real', 'Love', 'Ishq', 'Starts', 'Today', etc.
    """
    return normalize_series_identity_title(text)


def match_automatic_movie_file(
    target_movie_name: str,
    target_year: str | int = None,
    filename: str = "",
    caption: str = "",
    original_language: str = None,
    target_aliases: list = None,
    imdb_id: str = None,
    tmdb_id: str = None
) -> dict:
    """
    Strict authoritative Automatic Movie file matcher.
    Rule:
      Filename structure is strictly: {EXACT MOVIE NAME} {YEAR} {OTHER FILE DETAILS}
      ONLY the text BEFORE the 4-digit release year represents candidate movie name.
      Everything AFTER the year is file metadata (quality, language, etc.)
      and MUST NOT be included in movie-name comparison.
      
      Matches iff:
        normalized_candidate_title == normalized_target_title (or exact alias)
        AND
        candidate_year == target_year (if target_year is provided)
    """
    if not filename:
        return {"matched": False, "status": "invalid", "reason": "empty_filename"}

    from utils import is_video_file, is_subtitle_file
    if not is_video_file(filename) or is_subtitle_file(filename):
        return {"matched": False, "status": "invalid", "reason": "not_a_video_file"}

    raw_name = str(filename).strip()
    cap_text = str(caption or "").strip()
    combined_text = f"{raw_name} {cap_text}"

    # 1. Exact IMDb ID match if present in file or caption
    if imdb_id and str(imdb_id).startswith("tt"):
        file_imdb = re.search(r"\b(tt\d{7,10})\b", combined_text, re.I)
        if file_imdb and file_imdb.group(1).lower() != imdb_id.lower():
            return {"matched": False, "status": "invalid", "reason": "imdb_id_mismatch"}

    # 2. Reject series files
    token_text = " " + re.sub(r"[\._\-\+\[\]\(\)\{\}]", " ", raw_name) + " "
    if re.search(r"(?i)\b(?:s\d{1,2}[\s\.\-_]?e\d{1,4}|\d{1,2}x\d{1,4}|(?:season|series)\s*\d{1,2}|ep(?:isode)?\s*\d{1,4})\b", token_text):
        return {"matched": False, "status": "invalid", "reason": "is_series"}

    # 3. Strip file extension
    name_no_ext = re.sub(
        r"\.(mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|3gp|mpeg|mpg|vob|ogv|divx|m2ts|m2v|f4v)$",
        "",
        raw_name,
        flags=re.IGNORECASE
    ).strip()

    # 3.5 Strip recognized leading prefix markers (@username, (MM), [MM], (MS), [MS], etc.)
    unprefixed_name = strip_file_prefix_markers(name_no_ext)

    # 4. Clean remaining usernames / URLs
    cleaned_name = ' '.join(
        filter(
            lambda x: not x.startswith('@') and not x.startswith('http://') and not x.startswith('https://') and not x.startswith('www.') and not x.startswith('t.me/'),
            unprefixed_name.split()
        )
    )

    # 5. Parse target requirements
    norm_target = normalize_movie_identity_title(target_movie_name)
    if not norm_target:
        return {"matched": False, "status": "invalid", "reason": "empty_target_title"}

    valid_targets = {norm_target}
    if target_aliases and isinstance(target_aliases, (list, set, tuple)):
        for a in target_aliases:
            na = normalize_movie_identity_title(a)
            if na:
                valid_targets.add(na)

    req_year = None
    if target_year and str(target_year).strip() not in ["N/A", "None", "0", ""]:
        try:
            req_year = int(str(target_year).strip())
        except (ValueError, TypeError):
            req_year = None

    # 6. Locate standalone 4-digit years (1900-2099) using zero-width lookaround
    year_iter = list(re.finditer(r"(?i)(?<![0-9a-zA-Z])(19\d{2}|20\d{2})(?![0-9a-zA-Z])", cleaned_name))
    if not year_iter:
        return {"matched": False, "status": "invalid", "reason": "year_not_found_in_filename"}

    # Find the matching year boundary
    matched_candidate = None
    first_candidate = None

    for m in year_iter:
        year_start = m.start()
        year_end = m.end()
        digits_str = m.group(1)

        cand_raw = cleaned_name[:year_start].strip()
        rem_text = cleaned_name[year_end:].strip()
        c_year = int(digits_str)

        norm_cand = normalize_movie_identity_title(cand_raw)

        info = {
            "candidate_raw": cand_raw,
            "norm_candidate": norm_cand,
            "candidate_year": c_year,
            "remaining_text": rem_text,
        }

        if first_candidate is None:
            first_candidate = info

        # Check title match & year match
        title_matches = (norm_cand in valid_targets)
        year_matches = (req_year is None or c_year == req_year)

        if title_matches and year_matches:
            matched_candidate = info
            break

    if not matched_candidate:
        eval_cand = first_candidate or {}
        c_raw = eval_cand.get("candidate_raw", "")
        n_cand = eval_cand.get("norm_candidate", "")
        c_yr = eval_cand.get("candidate_year")

        if n_cand not in valid_targets:
            reason = f"movie_name_mismatch: '{c_raw}' != '{target_movie_name}'"
        elif req_year is not None and c_yr != req_year:
            reason = f"year_mismatch: file year {c_yr} != target year {req_year}"
        else:
            reason = "movie_identity_mismatch"

        return {
            "matched": False,
            "status": "invalid",
            "movie_name": c_raw,
            "year": c_yr,
            "reason": reason
        }

    # 7. Metadata extraction from remaining_text / filename
    from utils import extract_quality_from_filename
    from plugins.pm_filter import resolve_file_language, detect_file_languages
    from utils import normalize_language_name

    rem_text = matched_candidate["remaining_text"]
    c_year = matched_candidate["candidate_year"]
    cand_raw = matched_candidate["candidate_raw"]

    detected_quality = extract_quality_from_filename(rem_text or raw_name)
    detected_lang = resolve_file_language(
        rem_text or raw_name,
        caption=caption,
        metadata={"original_language": original_language},
        default_fallback=None
    )
    detected_langs = detect_file_languages(rem_text or raw_name, caption=caption, default=None)
    if not detected_langs and original_language:
        norm_orig = normalize_language_name(original_language) or original_language
        detected_langs = [norm_orig]
        if not detected_lang:
            detected_lang = norm_orig

    if not detected_lang:
        detected_lang = "English"

    return {
        "matched": True,
        "status": "matched",
        "movie_name": target_movie_name,
        "title": target_movie_name,
        "candidate_movie_name": cand_raw,
        "year": c_year,
        "quality": detected_quality,
        "language": detected_lang,
        "languages": detected_langs or [detected_lang],
        "remaining_text": rem_text,
        "reason": "exact_identity_match"
    }


def match_movie_identity(file_doc: dict, requested_title: str, requested_year: str | int = None, imdb_id: str = None, tmdb_id: str = None, known_conflicts: set = None) -> tuple[bool, str]:
    """
    Strict identity matcher for Auto Movie Add / Super Movie Filter synchronization.
    Enforces BOTH Title and Release Year matching to prevent cross-contamination across sequels/different years.
    Returns: (is_match: bool, reason: str)
    """
    if not isinstance(file_doc, dict):
        return False, "INVALID_FILE_DOC"

    file_name = file_doc.get("file_name", "") or ""
    caption = file_doc.get("caption", "") or ""

    res = match_automatic_movie_file(
        target_movie_name=requested_title,
        target_year=requested_year,
        filename=file_name,
        caption=caption,
        imdb_id=imdb_id,
        tmdb_id=tmdb_id
    )

    if res.get("matched"):
        return True, "EXACT_TITLE_AND_YEAR_MATCH"
    else:
        reason = res.get("reason", "MISMATCH")
        if "year_mismatch" in reason.lower():
            return False, "YEAR_MISMATCH"
        elif "year_not_found" in reason.lower():
            return False, "YEAR_NOT_FOUND_IN_FILENAME"
        elif "is_series" in reason.lower():
            return False, "IS_SERIES"
        elif "empty_filename" in reason.lower() or "not_a_video" in reason.lower():
            return False, "IS_SUBTITLE_OR_NON_VIDEO"
        else:
            return False, "TITLE_MISMATCH"


async def pub_is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append(
                [InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)]
            )
        except Exception as e:
            pass
    return btn

async def get_fsub_invite_link(bot, auth_channel, creates_join_request=True) -> str | None:
    """
    Generates an invite link for force subscribe channel.
    Attempts join-request invite link first if creates_join_request=True,
    falling back to standard invite link or chat invite link.
    """
    if not auth_channel:
        return None
    try:
        ch_id = int(auth_channel) if str(auth_channel).lstrip("-").isdigit() else auth_channel
        if creates_join_request:
            try:
                link_obj = await bot.create_chat_invite_link(ch_id, creates_join_request=True)
                if link_obj and hasattr(link_obj, "invite_link") and link_obj.invite_link:
                    return link_obj.invite_link
                if isinstance(link_obj, str) and link_obj.startswith("http"):
                    return link_obj
            except Exception as e:
                logger.warning(f"[FSUB LINK] creates_join_request failed: {e}, falling back to standard link")
        try:
            link_obj = await bot.create_chat_invite_link(ch_id)
            if link_obj and hasattr(link_obj, "invite_link") and link_obj.invite_link:
                return link_obj.invite_link
            if isinstance(link_obj, str) and link_obj.startswith("http"):
                return link_obj
        except Exception as e:
            logger.warning(f"[FSUB LINK] standard create_chat_invite_link failed: {e}")
        try:
            chat = await bot.get_chat(ch_id)
            if getattr(chat, "invite_link", None):
                return chat.invite_link
            if getattr(chat, "username", None):
                return f"https://t.me/{chat.username}"
        except Exception as e:
            logger.error(f"[FSUB LINK] get_chat failed: {e}")
    except Exception as ex:
        logger.error(f"[FSUB LINK ERROR] {ex}")
    return None

async def is_subscribed(bot, query):
    if not AUTH_CHANNEL:
        return True

    if isinstance(query, int):
        user_id = query
    elif isinstance(query, str) and query.lstrip("-").isdigit():
        user_id = int(query)
    elif hasattr(query, "from_user") and query.from_user:
        user_id = query.from_user.id
    elif hasattr(query, "chat") and query.chat:
        user_id = query.chat.id
    else:
        user_id = getattr(query, "id", None)

    if not user_id:
        return False

    if user_id in ADMINS:
        return True

    try:
        user = await join_db().get_user(user_id)
        if user and int(user.get("user_id", 0)) == int(user_id):
            return True
    except Exception as e:
        logger.warning(f"[IS_SUBSCRIBED] join_db lookup error: {e}")

    try:
        auth_ch = int(AUTH_CHANNEL) if str(AUTH_CHANNEL).lstrip("-").isdigit() else AUTH_CHANNEL
        user_data = await bot.get_chat_member(auth_ch, user_id)
        if user_data:
            st = user_data.status
            if st in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.RESTRICTED]:
                try:
                    u_obj = getattr(user_data, "user", None)
                    fn = getattr(u_obj, "first_name", "") if u_obj else ""
                    un = getattr(u_obj, "username", "") if u_obj else ""
                    await join_db().add_user(user_id=user_id, first_name=fn, username=un, date=datetime.now())
                except Exception:
                    pass
                return True
    except UserNotParticipant:
        pass
    except Exception as e:
        logger.warning(f"[IS_SUBSCRIBED] get_chat_member exception: {e}")
    return False

def _fetch_url_sync(url):
    import ssl
    import urllib.request
    import urllib.error
    crawlers = [
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Twitterbot/1.0",
        "TelegramBot (like TwitterBot)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for ua in crawlers:
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'close',
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            continue
    return None

async def get_public_tmdb_poster(query, bulk=False, id=False, file=None):
    """
    Fetches public TMDB movie/series metadata without any API key.
    Extracts poster (w500), title, year, rating, genres, and overview.
    """
    try:
        query_str = str(query).strip()
        year = None

        y_match = re.search(r'\b(19\d\d|20\d\d)\b', query_str)
        if y_match:
            year = y_match.group(1)
            clean_title = (query_str.replace(year, "")).strip()
        elif file is not None:
            fy_match = re.search(r'\b(19\d\d|20\d\d)\b', str(file))
            if fy_match:
                year = fy_match.group(1)
            clean_title = query_str
        else:
            clean_title = query_str

        clean_title = re.sub(r'[\._\-]', ' ', clean_title).strip()
        if not clean_title:
            return None

        import urllib.parse
        import html as _html
        url = f"https://www.themoviedb.org/search?query={urllib.parse.quote(clean_title)}"

        html_text = await asyncio.to_thread(_fetch_url_sync, url)
        candidates = []
        if html_text:
            cards = re.findall(r'<div[^>]+class="[^"]*(?:comp:media-card|card v4)[^"]*"[^>]*>(.*?)(?=<div[^>]+class="[^"]*(?:comp:media-card|card v4)[^"]*"|<div class="pagination"|<footer>|$)', html_text, re.DOTALL)
            for card in cards:
                title_match = re.search(r'<h2[^>]*>(?:<span[^>]*>)?([^<]+)', card)
                title = _html.unescape(title_match.group(1).strip()) if title_match else None

                href_match = re.search(r'href="(/[^"]+)"', card)
                rel_url = href_match.group(1) if href_match else ""

                kind = "movie"
                if "/tv/" in rel_url or 'data-media-type="tv"' in card:
                    kind = "tv series"
                elif "/movie/" in rel_url or 'data-media-type="movie"' in card:
                    kind = "movie"

                date_match = re.search(r'<span class="release_date[^"]*">([^<]+)</span>', card)
                release_date = date_match.group(1).strip() if date_match else None
                card_year = None
                if release_date:
                    cy_match = re.search(r'\b(19\d\d|20\d\d)\b', release_date)
                    if cy_match:
                        card_year = cy_match.group(1)

                poster_match = re.search(r'(?:src|data-src)="([^"]+/(?:image|media)\.themoviedb\.org/t/p/[^"]+)"', card)
                poster = None
                if poster_match:
                    raw_poster = poster_match.group(1)
                    poster = re.sub(r'/w\d+(_and_h\d+[^/]*)?/', '/w500/', raw_poster)
                    if poster.startswith('//'):
                        poster = 'https:' + poster

                overview_match = re.search(r'<p>([^<]+)</p>', card)
                overview = _html.unescape(overview_match.group(1).strip()) if overview_match else ""

                if title:
                    item = {
                        'title': title,
                        'year': card_year or year,
                        'release_date': release_date or str(card_year or "N/A"),
                        'poster': poster,
                        'overview': overview,
                        'kind': kind,
                        'rel_url': rel_url,
                        'tmdb_id': None,
                    }
                    candidates.append(item)

        if not candidates:
            return None

        if bulk:
            class MockTMDBMovie(dict):
                def __init__(self, d):
                    super().__init__(d)
                    self.movieID = d.get('rel_url', '')
                    self.data = d
                def __getitem__(self, k):
                    return self.get(k)
            return [MockTMDBMovie(c) for c in candidates]

        best = candidates[0]
        if year:
            for c in candidates:
                if str(c.get('year')) == str(year):
                    best = c
                    break

        rating = None
        genres = []
        orig_lang = normalize_language_name(best.get('original_language')) if best.get('original_language') else None
        posters = [best.get('poster')] if best.get('poster') else []

        if best.get('rel_url'):
            try:
                detail_url = f"https://www.themoviedb.org{best['rel_url']}"
                page = await asyncio.to_thread(_fetch_url_sync, detail_url)
                if page:
                    rate_match = re.search(r'data-percent="([0-9.]+)"', page)
                    if rate_match:
                        rating = str(round(float(rate_match.group(1)) / 10.0, 1))
                    genres_match = re.search(r'<span class="genres">([^<]+(?:<a[^>]*>[^<]+</a>[^<]*)+)</span>', page)
                    if genres_match:
                        genres = [_html.unescape(g.strip()) for g in re.findall(r'<a[^>]*>([^<]+)</a>', genres_match.group(1))]
                    lang_match = re.search(r'(?:<bdi>Original Language</bdi>|Original Language)[^<]*</(?:bdi|strong|span|p)>[\s:]*([A-Za-z]+)', page, re.I)
                    if not lang_match:
                        lang_match = re.search(r'<strong>\s*Original Language\s*</strong>[\s:]*([A-Za-z]+)', page, re.I)
                    if not lang_match:
                        lang_match = re.search(r'"original_language"\s*:\s*"([^"]+)"', page, re.I)
                    if lang_match:
                        orig_lang = normalize_language_name(lang_match.group(1).strip())
                    posters = extract_tmdb_posters_from_html(page, primary_poster=best.get('poster'))
            except Exception:
                pass

        return {
            'title': best['title'],
            'votes': None,
            'aka': None,
            'seasons': None,
            'box_office': None,
            'localized_title': best['title'],
            'kind': best['kind'],
            'imdb_id': None,
            'cast': None,
            'runtime': None,
            'countries': None,
            'certificates': None,
            'languages': None,
            'original_language': orig_lang,
            'director': None,
            'writer': None,
            'producer': None,
            'composer': None,
            'cinematographer': None,
            'music_team': None,
            'distributors': None,
            'release_date': str(best.get('release_date') or best.get('year') or 'N/A'),
            'year': best.get('year'),
            'genres': ", ".join(genres) if genres else "Drama",
            'poster': best.get('poster'),
            'posters': posters,
            'plot': best.get('overview') or "",
            'rating': rating or "7.5",
            'url': f"https://www.themoviedb.org{best.get('rel_url')}" if best.get('rel_url') else "https://www.themoviedb.org"
        }
    except Exception as e:
        logger.warning(f"Public TMDB scraper error for '{query}': {e}")
        return None

async def get_imdb_public_metadata(url_or_id: str) -> dict | None:
    """
    Public IMDb metadata scraper without API keys.
    Extracts structured JSON-LD and OpenGraph metadata from public IMDb webpage.
    """
    import html as _html
    import json as _json

    m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", str(url_or_id), re.IGNORECASE)
    if not m_imdb:
        logger.warning(f"[PUBLIC IMDb] Invalid IMDb URL or ID: {url_or_id}")
        return None

    clean_tt = m_imdb.group(1).lower()
    page_url = f"https://www.imdb.com/title/{clean_tt}/"
    logger.info(f"[PUBLIC IMDb] START id={clean_tt} url={page_url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    timeout = aiohttp.ClientTimeout(total=10, connect=4, sock_read=6)

    html_content = ""
    status = 0

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(page_url) as resp:
                status = resp.status
                logger.info(f"[PUBLIC IMDb] HTTP status={status}")
                if status == 200:
                    html_content = await resp.text()
    except asyncio.TimeoutError:
        logger.error(f"[PUBLIC IMDb] FAILED reason=TIMEOUT id={clean_tt}")
    except Exception as e:
        logger.warning(f"[PUBLIC IMDb] HTML fetch failed: {e}")

    # Fallback to direct Suggestion API if HTML is blocked, empty, or challenges
    if not html_content or status != 200:
        logger.info(f"[PUBLIC IMDb] Falling back to Suggestion API id={clean_tt}")
        direct_meta = await get_imdb_metadata_direct(clean_tt)
        if direct_meta:
            direct_meta["source"] = "imdb_public"
            return direct_meta
        return None

    soup = BeautifulSoup(html_content, "html.parser") if BeautifulSoup else None
    json_ld_obj = None

    # 1. Parse JSON-LD scripts
    json_ld_raw_list = []
    if soup:
        for script_tag in soup.find_all("script", type="application/ld+json"):
            if script_tag.string:
                json_ld_raw_list.append(script_tag.string)
    else:
        for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_content, re.DOTALL | re.I):
            json_ld_raw_list.append(m.group(1))

    for raw_json in json_ld_raw_list:
        try:
            parsed = _json.loads(raw_json)
            candidates = []
            if isinstance(parsed, dict):
                if "@graph" in parsed and isinstance(parsed["@graph"], list):
                    candidates.extend(parsed["@graph"])
                else:
                    candidates.append(parsed)
            elif isinstance(parsed, list):
                candidates.extend(parsed)

            for cand in candidates:
                if not isinstance(cand, dict):
                    continue
                c_type = str(cand.get("@type", "")).lower()
                if any(t in c_type for t in ("movie", "tvseries", "tvepisode", "creativework", "videoobject")):
                    json_ld_obj = cand
                    break
                if "name" in cand and ("datePublished" in cand or "genre" in cand):
                    json_ld_obj = cand
                    break
            if json_ld_obj:
                break
        except Exception:
            continue

    logger.info(f"[PUBLIC IMDb] JSON-LD FOUND={bool(json_ld_obj)}")

    title = None
    year = None
    kind = "movie"
    poster = None
    rating = ""
    genres = ""
    plot = ""
    orig_lang = None

    if json_ld_obj:
        title = json_ld_obj.get("name")
        date_pub = json_ld_obj.get("datePublished")
        if date_pub:
            y_match = re.search(r"\b(19|20)\d{2}\b", str(date_pub))
            if y_match:
                year = y_match.group(0)

        ld_type = str(json_ld_obj.get("@type", "")).lower()
        if "tvseries" in ld_type or "tv_series" in ld_type:
            kind = "tv series"
        elif "tvepisode" in ld_type:
            kind = "tv episode"
        elif "movie" in ld_type:
            kind = "movie"

        img = json_ld_obj.get("image")
        if isinstance(img, str):
            poster = img
        elif isinstance(img, dict):
            poster = img.get("url") or img.get("contentUrl")

        agg_rating = json_ld_obj.get("aggregateRating")
        if isinstance(agg_rating, dict):
            rating = str(agg_rating.get("ratingValue") or "").strip()

        if not rating or rating in ("0", "0.0", "0/10"):
            im_r = re.search(r'data-testid=["\']hero-rating-bar__aggregate-rating__score["\'][^>]*>(?:<[^>]+>)*\s*([0-9.]+)', html_content) or re.search(r'["\']ratingValue["\']\s*:\s*["\']?([0-9.]+)["\']?', html_content)
            if im_r and float(im_r.group(1)) > 0:
                rating = str(round(float(im_r.group(1)), 1))

        genre_val = json_ld_obj.get("genre")
        if isinstance(genre_val, list):
            genres = ", ".join(str(g).strip() for g in genre_val if str(g).strip())
        elif isinstance(genre_val, str):
            genres = genre_val.strip()

        plot = json_ld_obj.get("description") or ""

        in_lang = json_ld_obj.get("inLanguage")
        if isinstance(in_lang, str):
            orig_lang = normalize_language_name(in_lang)
        elif isinstance(in_lang, dict):
            orig_lang = normalize_language_name(in_lang.get("name") or in_lang.get("alternateName") or in_lang.get("identifier"))
        elif isinstance(in_lang, list) and in_lang:
            first_l = in_lang[0]
            if isinstance(first_l, str):
                orig_lang = normalize_language_name(first_l)
            elif isinstance(first_l, dict):
                orig_lang = normalize_language_name(first_l.get("name") or first_l.get("alternateName"))

    # OpenGraph / Meta Tag fallbacks
    if not title:
        og_t_m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']', html_content, re.I)
        if og_t_m:
            raw_og_title = _html.unescape(og_t_m.group(1).strip())
            title = re.sub(r"\s*-\s*IMDb.*$", "", raw_og_title, flags=re.I).strip()

    if not year:
        page_t_m = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.I)
        if page_t_m:
            y_m = re.search(r"\(.*?((?:19|20)\d{2}).*?\)", page_t_m.group(1))
            if y_m:
                year = y_m.group(1)

    if not orig_lang:
        lang_m = re.search(r'data-testid=["\']title-details-languages["\'][^>]*>(?:<[^>]+>)*\s*<a[^>]*>([^<]+)</a>', html_content, re.I)
        if not lang_m:
            lang_m = re.search(r'href=["\']/search/title/\?primary_language=([^"&]+)', html_content, re.I)
        if lang_m:
            orig_lang = normalize_language_name(lang_m.group(1).strip())

    if not poster:
        og_img_m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_content, re.I)
        if og_img_m:
            poster = og_img_m.group(1).strip()

    if not plot:
        og_desc_m = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']', html_content, re.I)
        if og_desc_m:
            plot = _html.unescape(og_desc_m.group(1).strip())

    og_type_m = re.search(r'<meta[^>]*property=["\']og:type["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I)
    if og_type_m:
        if "tv_series" in og_type_m.group(1).lower() or "video.tv_show" in og_type_m.group(1).lower():
            kind = "tv series"

    if poster and poster.startswith("//"):
        poster = "https:" + poster

    if not title or not year:
        logger.info(f"[PUBLIC IMDb] Supplementary Suggestion API lookup id={clean_tt}")
        sugg = await get_imdb_metadata_direct(clean_tt)
        if sugg:
            title = title or sugg.get("title")
            year = year or str(sugg.get("year") or "")
            kind = sugg.get("kind") or kind
            poster = poster or sugg.get("poster")
            orig_lang = orig_lang or sugg.get("original_language")

    if not title:
        logger.warning(f"[PUBLIC IMDb] FAILED reason=NO_TITLE id={clean_tt}")
        return None

    clean_year = str(year).strip() if year else None

    logger.info(
        f"[PUBLIC IMDb] COMPLETE\n"
        f"title={title}\n"
        f"year={clean_year}\n"
        f"kind={kind}\n"
        f"original_language={orig_lang}\n"
        f"poster={bool(poster)}"
    )

    return {
        "title": _html.unescape(title.strip()),
        "year": clean_year,
        "kind": kind,
        "imdb_id": clean_tt,
        "tmdb_id": None,
        "original_language": orig_lang,
        "poster": poster,
        "posters": [poster] if poster else [],
        "rating": rating,
        "genres": genres,
        "plot": _html.unescape(plot.strip()) if plot else "",
        "source": "imdb_public",
    }


async def get_tmdb_public_metadata(url: str) -> dict | None:
    """
    Public TMDB metadata scraper without API keys.
    Extracts structured JSON-LD and OpenGraph metadata from public TMDB webpage.
    """
    import html as _html
    import json as _json

    m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)(?:-([a-zA-Z0-9_-]+))?', str(url), re.IGNORECASE)
    if not m_tmdb:
        logger.warning(f"[PUBLIC TMDB] Invalid TMDB URL: {url}")
        return None

    media_type = m_tmdb.group(1).lower()
    tmdb_id = m_tmdb.group(2)
    raw_slug = m_tmdb.group(3) or ""
    clean_url = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"
    logger.info(f"[PUBLIC TMDB] START id={tmdb_id} type={media_type} url={clean_url}")

    # 1. Fetch public HTML webpage directly using crawler user-agents
    html_content = await asyncio.to_thread(_fetch_url_sync, clean_url)
    if not html_content:
        try:
            crawlers_ua = "Googlebot/2.1 (+http://www.google.com/bot.html)"
            headers = {
                "User-Agent": crawlers_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            timeout = aiohttp.ClientTimeout(total=10, connect=4, sock_read=6)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(clean_url) as resp:
                    if resp.status == 200:
                        html_content = await resp.text()
        except Exception:
            pass

    # 2. If public HTML could not be fetched, log warning and fallback to slug
    if not html_content:
        logger.warning(f"[PUBLIC TMDB] Failed to fetch public webpage for id={tmdb_id}")
        if raw_slug:
            slug_clean = re.sub(r"-\b((?:19|20)\d{2})\b", "", raw_slug).replace("-", " ").strip().title()
            if slug_clean:
                sugg = await get_imdb_metadata_direct(slug_clean)
                if sugg and sugg.get("title"):
                    sugg["tmdb_id"] = str(tmdb_id)
                    return sugg
        return None

    soup = BeautifulSoup(html_content, "html.parser") if BeautifulSoup else None

    # 1. Parse and flatten all JSON-LD objects recursively
    json_ld_raw_list = []
    if soup:
        for script_tag in soup.find_all("script", type="application/ld+json"):
            if script_tag.string:
                json_ld_raw_list.append(script_tag.string)
    else:
        for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_content, re.DOTALL | re.I):
            json_ld_raw_list.append(m.group(1))

    candidates = []
    def _flatten_json_ld(obj):
        if isinstance(obj, dict):
            if "@graph" in obj and isinstance(obj["@graph"], list):
                for item in obj["@graph"]:
                    _flatten_json_ld(item)
            else:
                candidates.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                _flatten_json_ld(item)

    for raw_json in json_ld_raw_list:
        try:
            parsed = _json.loads(raw_json)
            _flatten_json_ld(parsed)
        except Exception:
            continue

    logger.info(f"[PUBLIC TMDB] JSON-LD OBJECTS={len(candidates)}")

    selected_obj = None
    REJECT_NAMES = {"the movie database", "tmdb", "themoviedb", "the movie database (tmdb)"}
    REJECT_TYPES = {"website", "organization", "webpage", "webapplication"}

    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        c_type = str(cand.get("@type", "")).strip()
        c_name = str(cand.get("name", "")).strip()
        logger.info(f"[PUBLIC TMDB] JSON-LD CANDIDATE type={c_type} name={c_name}")

        if c_type.lower() in REJECT_TYPES:
            continue
        if c_name.lower() in REJECT_NAMES or c_name.lower().startswith("the movie database"):
            continue

        c_type_lower = c_type.lower()
        if any(t in c_type_lower for t in ("movie", "tvseries", "tv_series", "tvepisode", "creativework", "videoobject")):
            if c_name:
                selected_obj = cand
                break
        elif "datePublished" in cand or "releasedEvent" in cand or "genre" in cand or "aggregateRating" in cand:
            if c_name:
                selected_obj = cand
                break

    title = None
    year = None
    kind = "tv series" if media_type == "tv" else "movie"
    poster = None
    rating = ""
    genres = ""
    plot = ""
    orig_lang = None

    if selected_obj:
        c_name = str(selected_obj.get("name", "")).strip()
        if c_name and c_name.lower() not in REJECT_NAMES and not c_name.lower().startswith("the movie database"):
            title = c_name
            logger.info(f"[PUBLIC TMDB] SELECTED MOVIE OBJECT title={title}")

        date_pub = selected_obj.get("datePublished") or selected_obj.get("releasedEvent")
        if date_pub:
            y_match = re.search(r"\b(19|20)\d{2}\b", str(date_pub))
            if y_match:
                year = y_match.group(0)

        img = selected_obj.get("image")
        if isinstance(img, str):
            poster = img
        elif isinstance(img, dict):
            poster = img.get("url") or img.get("contentUrl")

        agg = selected_obj.get("aggregateRating")
        if isinstance(agg, dict):
            rating = str(agg.get("ratingValue") or "").strip()

        if not rating or rating in ("0", "0.0", "0/10"):
            pct_m = re.search(r'data-percent=["\']([0-9.]+)["\']', html_content)
            if pct_m and float(pct_m.group(1)) > 0:
                rating = str(round(float(pct_m.group(1)) / 10.0, 1))
            else:
                va_m = re.search(r'["\']vote_average["\']\s*:\s*([0-9.]+)', html_content) or re.search(r'["\']ratingValue["\']\s*:\s*["\']?([0-9.]+)["\']?', html_content)
                if va_m and float(va_m.group(1)) > 0:
                    rating = str(round(float(va_m.group(1)), 1))

        genre_val = selected_obj.get("genre")
        if isinstance(genre_val, list):
            genres = ", ".join(str(g).strip() for g in genre_val if str(g).strip())
        elif isinstance(genre_val, str):
            genres = genre_val.strip()

        plot = selected_obj.get("description") or ""

        in_lang = selected_obj.get("inLanguage")
        if isinstance(in_lang, str):
            orig_lang = normalize_language_name(in_lang)
        elif isinstance(in_lang, dict):
            orig_lang = normalize_language_name(in_lang.get("name") or in_lang.get("alternateName") or in_lang.get("identifier"))
        elif isinstance(in_lang, list) and in_lang:
            first_l = in_lang[0]
            if isinstance(first_l, str):
                orig_lang = normalize_language_name(first_l)
            elif isinstance(first_l, dict):
                orig_lang = normalize_language_name(first_l.get("name") or first_l.get("alternateName"))

    # OpenGraph / Meta title fallback
    if not title or title.lower() in REJECT_NAMES or title.lower().startswith("the movie database"):
        title = None
        og_t_m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']', html_content, re.I)
        if og_t_m:
            raw_t = _html.unescape(og_t_m.group(1).strip())
            cleaned_og_title = re.sub(r"\s*([—\-\|]\s*(?:The Movie Database|TMDB).*)$", "", raw_t, flags=re.I).strip()
            y_m = re.search(r"\(((?:19|20)\d{2})\)", cleaned_og_title)
            if y_m:
                if not year:
                    year = y_m.group(1)
                cleaned_og_title = re.sub(r"\s*\(((?:19|20)\d{2})\)", "", cleaned_og_title).strip()
            if cleaned_og_title and cleaned_og_title.lower() not in REJECT_NAMES and not cleaned_og_title.lower().startswith("the movie database"):
                title = cleaned_og_title

    # Page <title> tag fallback
    if not title or title.lower() in REJECT_NAMES or title.lower().startswith("the movie database"):
        page_t_m = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.I)
        if page_t_m:
            raw_page_t = _html.unescape(page_t_m.group(1).strip())
            cleaned_page_title = re.sub(r"\s*([—\-\|]\s*(?:The Movie Database|TMDB).*)$", "", raw_page_t, flags=re.I).strip()
            y_m = re.search(r"\(((?:19|20)\d{2})\)", cleaned_page_title)
            if y_m:
                if not year:
                    year = y_m.group(1)
                cleaned_page_title = re.sub(r"\s*\(((?:19|20)\d{2})\)", "", cleaned_page_title).strip()
            if cleaned_page_title and cleaned_page_title.lower() not in REJECT_NAMES and not cleaned_page_title.lower().startswith("the movie database"):
                title = cleaned_page_title

    # URL slug fallback
    if not title or title.lower() in REJECT_NAMES or title.lower().startswith("the movie database"):
        if raw_slug:
            slug_clean = re.sub(r"-\b((?:19|20)\d{2})\b", "", raw_slug)
            y_m = re.search(r"\b((?:19|20)\d{2})\b", raw_slug)
            if y_m and not year:
                year = y_m.group(1)
            title = slug_clean.replace("-", " ").strip().title()

    # Year fallback from HTML
    if not year:
        rel_m = re.search(r'class=["\'][^"\']*release_date[^"\']*["\'][^>]*>([^<]+)', html_content, re.I)
        if rel_m:
            y_m = re.search(r"\b((?:19|20)\d{2})\b", rel_m.group(1))
            if y_m:
                year = y_m.group(1)

    # HTML original language fallback
    if not orig_lang:
        lang_m = re.search(r'(?:<bdi>Original Language</bdi>|Original Language)[^<]*</(?:bdi|strong|span|p)>[\s:]*([A-Za-z]+)', html_content, re.I)
        if not lang_m:
            lang_m = re.search(r'<strong>\s*Original Language\s*</strong>[\s:]*([A-Za-z]+)', html_content, re.I)
        if not lang_m:
            lang_m = re.search(r'"original_language"\s*:\s*"([^"]+)"', html_content, re.I)
        if lang_m:
            orig_lang = normalize_language_name(lang_m.group(1).strip())

    if not poster:
        og_img_m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_content, re.I)
        if og_img_m:
            poster = og_img_m.group(1).strip()

    if not plot:
        og_desc_m = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I) or re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']', html_content, re.I)
        if og_desc_m:
            plot = _html.unescape(og_desc_m.group(1).strip())

    if not genres:
        genres_m = re.search(r'<span[^>]*class=["\']genres["\'][^>]*>(.*?)</span>', html_content, re.DOTALL | re.I)
        if genres_m:
            genres_list = [_html.unescape(g.strip()) for g in re.findall(r'<a[^>]*>([^<]+)</a>', genres_m.group(1)) if g.strip()]
            if genres_list:
                genres = ", ".join(genres_list)

    if poster:
        if poster.startswith("//"):
            poster = "https:" + poster
        poster = re.sub(r'/w\d+(_and_h\d+[^/]*)?/', '/w500/', poster)

    posters = extract_tmdb_posters_from_html(html_content, primary_poster=poster)
    if len(posters) < 3 and media_type and tmdb_id:
        try:
            gallery_url = f"https://www.themoviedb.org/{media_type}/{tmdb_id}/images/posters"
            gallery_html = await asyncio.to_thread(_fetch_url_sync, gallery_url)
            if gallery_html:
                gallery_posters = extract_tmdb_posters_from_html(gallery_html)
                for gp in gallery_posters:
                    if gp not in posters:
                        posters.append(gp)
                    if len(posters) >= 12:
                        break
        except Exception as ge:
            logger.debug(f"[PUBLIC TMDB] Gallery fetch error: {ge}")

    if not poster and posters:
        poster = posters[0]

    # Strict Validation
    if not title or title.strip().lower() in REJECT_NAMES or title.strip().lower().startswith("the movie database"):
        logger.warning(f"[PUBLIC TMDB] FAILED reason=INVALID_TITLE title={title} id={tmdb_id}")
        return None

    clean_year = str(year).strip() if year else None

    logger.info(
        f"[PUBLIC TMDB] COMPLETE\n"
        f"title={title}\n"
        f"year={clean_year}\n"
        f"kind={kind}\n"
        f"original_language={orig_lang}\n"
        f"poster={bool(poster)}\n"
        f"posters_count={len(posters)}"
    )

    return {
        "title": _html.unescape(title.strip()),
        "year": clean_year,
        "kind": kind,
        "imdb_id": None,
        "tmdb_id": str(tmdb_id),
        "original_language": orig_lang,
        "poster": poster,
        "posters": posters,
        "rating": rating,
        "genres": genres,
        "plot": _html.unescape(plot.strip()) if plot else "",
        "source": "tmdb_public",
    }


async def get_public_movie_metadata(text: str) -> dict | None:
    """
    Unified public metadata dispatcher for IMDb / TMDB URLs or IDs.
    Does NOT require API keys. Returns standardized movie/series metadata.
    """
    text_str = str(text).strip()
    m_tmdb = re.search(r'(?:https?://)?(?:www\.)?themoviedb\.org/(movie|tv)/(\d+)', text_str, re.IGNORECASE)
    m_imdb = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", text_str, re.IGNORECASE)

    if m_tmdb:
        return await get_tmdb_public_metadata(text_str)
    elif m_imdb:
        return await get_imdb_public_metadata(text_str)
    else:
        logger.warning(f"[PUBLIC METADATA] Unrecognized URL or ID query={text_str}")
        return None


def extract_single_episode_title_from_tmdb_html(html_content: str) -> str | None:
    """
    Extracts episode title from TMDB single episode HTML page.
    """
    if not html_content:
        return None
    import html as _html
    import json as _json

    # 1. JSON-LD
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_content, re.DOTALL | re.I):
        try:
            data = _json.loads(m.group(1))
            if isinstance(data, dict):
                if data.get("@type") in ("TVEpisode", "Episode") and data.get("name"):
                    return _html.unescape(str(data["name"])).strip()
        except Exception:
            continue

    # 2. OpenGraph og:title
    og_m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.I)
    if og_m:
        raw_og = _html.unescape(og_m.group(1)).strip()
        clean = re.sub(r"\s*\(S\d+E\d+\).*$", "", raw_og, flags=re.I)
        clean = re.sub(r"\s*[—–-]\s*The Movie Database.*$", "", clean, flags=re.I)
        clean = re.sub(r"\s*[—–-]\s*TMDB.*$", "", clean, flags=re.I)
        if clean.strip():
            return clean.strip()

    # 3. <title> tag
    title_m = re.search(r'<title>(.*?)</title>', html_content, re.I | re.DOTALL)
    if title_m:
        raw_t = _html.unescape(title_m.group(1)).strip()
        clean = re.sub(r"\s*\(S\d+E\d+\).*$", "", raw_t, flags=re.I)
        clean = re.sub(r"\s*[—–-]\s*The Movie Database.*$", "", clean, flags=re.I)
        clean = re.sub(r"\s*[—–-]\s*TMDB.*$", "", clean, flags=re.I)
        if clean.strip():
            return clean.strip()

    return None


async def get_tmdb_public_season_episodes(tv_id: str | int, season_number: int) -> dict[int, str]:
    """
    Publicly fetches all episode titles for a specific season from TMDB TV webpage.
    Returns: {episode_number (int): episode_title (str)}
    """
    if not tv_id or str(tv_id).strip() in ("0", "None", "N/A", ""):
        return {}
    
    clean_tv_id = str(tv_id).strip()
    try:
        s_num = int(season_number)
    except (ValueError, TypeError):
        s_num = 1

    season_url = f"https://www.themoviedb.org/tv/{clean_tv_id}/season/{s_num}"
    logger.info(f"[EPISODE TITLE] REQUEST TMDB SEASON tv_id={clean_tv_id} season={s_num} url={season_url}")

    html_content = await asyncio.to_thread(_fetch_url_sync, season_url)
    if not html_content:
        try:
            crawlers_ua = "Googlebot/2.1 (+http://www.google.com/bot.html)"
            headers = {
                "User-Agent": crawlers_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            timeout = aiohttp.ClientTimeout(total=8, connect=3, sock_read=5)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(season_url) as resp:
                    if resp.status == 200:
                        html_content = await resp.text()
        except Exception:
            pass

    if not html_content:
        logger.warning(f"[EPISODE TITLE] FETCH FAILED tv_id={clean_tv_id} season={s_num} source=TMDB")
        return {}

    episodes = {}
    import html as _html
    import json as _json

    # 1. Parse JSON-LD
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_content, re.DOTALL | re.I):
        try:
            data = _json.loads(m.group(1))
            items = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            for item in items:
                if isinstance(item, dict):
                    if item.get("@type") in ("TVEpisode", "Episode") or "episodeNumber" in item:
                        ep_num = item.get("episodeNumber")
                        name = item.get("name")
                        if ep_num is not None and name:
                            try:
                                episodes[int(ep_num)] = _html.unescape(str(name)).strip()
                            except ValueError:
                                pass
        except Exception:
            continue

    # 2. Extract from Episode link anchors
    ep_pattern = re.compile(
        rf'/tv/{clean_tv_id}/season/{s_num}/episode/(\d+)[^>]*>(?:<[^>]+>)*\s*([^<]+?)\s*<',
        re.IGNORECASE
    )
    for m in ep_pattern.finditer(html_content):
        ep_num_str = m.group(1)
        title_str = _html.unescape(m.group(2)).strip()
        if ep_num_str.isdigit() and title_str and not title_str.lower().startswith("episode") and int(ep_num_str) not in episodes:
            episodes[int(ep_num_str)] = title_str

    # 3. Check card headers / h3 / h4: <h3><a href=".../episode/1">Winter Is Coming</a></h3>
    ep_h_pattern = re.compile(
        rf'<h[2345][^>]*>\s*<a[^>]*href=["\'][^"\']*/episode/(\d+)["\'][^>]*>\s*([^<]+?)\s*</a>',
        re.IGNORECASE
    )
    for m in ep_h_pattern.finditer(html_content):
        ep_num_str = m.group(1)
        title_str = _html.unescape(m.group(2)).strip()
        if ep_num_str.isdigit() and title_str and int(ep_num_str) not in episodes:
            episodes[int(ep_num_str)] = title_str

    if not hasattr(temp, "EPISODE_TITLES_CACHE"):
        temp.EPISODE_TITLES_CACHE = {}

    for ep_n, ep_t in episodes.items():
        cache_k = f"tmdb:{clean_tv_id}:{s_num}:{ep_n}"
        temp.EPISODE_TITLES_CACHE[cache_k] = ep_t
        logger.info(f"[EPISODE TITLE] SUCCESS source=TMDB season={s_num} episode={ep_n} title={ep_t}")

    return episodes


async def get_tmdb_public_episode_metadata(tv_id: str | int, season_number: int, episode_number: int) -> dict:
    """
    Publicly fetches metadata for a specific episode from TMDB TV webpage.
    Returns: {"episode_title": str, "season": int, "episode": int}
    """
    clean_tv_id = str(tv_id).strip()
    try:
        s_num = int(season_number)
    except (ValueError, TypeError):
        s_num = 1
    try:
        ep_num = int(episode_number)
    except (ValueError, TypeError):
        ep_num = 1

    cache_k = f"tmdb:{clean_tv_id}:{s_num}:{ep_num}"
    cached = getattr(temp, "EPISODE_TITLES_CACHE", {}).get(cache_k)
    if cached:
        return {"episode_title": cached, "season": s_num, "episode": ep_num}

    # Fetch season episodes first (efficiently fills entire season cache in one go)
    season_eps = await get_tmdb_public_season_episodes(clean_tv_id, s_num)
    if ep_num in season_eps:
        return {"episode_title": season_eps[ep_num], "season": s_num, "episode": ep_num}

    # If season page didn't have it, try direct episode page
    ep_url = f"https://www.themoviedb.org/tv/{clean_tv_id}/season/{s_num}/episode/{ep_num}"
    logger.info(f"[EPISODE TITLE] REQUEST TMDB SINGLE EPISODE url={ep_url}")
    html_content = await asyncio.to_thread(_fetch_url_sync, ep_url)
    if html_content:
        ep_title = extract_single_episode_title_from_tmdb_html(html_content)
        if ep_title:
            if not hasattr(temp, "EPISODE_TITLES_CACHE"):
                temp.EPISODE_TITLES_CACHE = {}
            temp.EPISODE_TITLES_CACHE[cache_k] = ep_title
            logger.info(f"[EPISODE TITLE] SUCCESS source=TMDB season={s_num} episode={ep_num} title={ep_title}")
            return {"episode_title": ep_title, "season": s_num, "episode": ep_num}

    return {"episode_title": f"Episode {ep_num:02d}", "season": s_num, "episode": ep_num}


async def get_imdb_public_episode_metadata(imdb_id: str, season_number: int, episode_number: int) -> dict | None:
    """
    Public fallback to retrieve episode title from IMDb.
    """
    if not imdb_id or not str(imdb_id).startswith("tt"):
        return None
    try:
        s_num = int(season_number)
        ep_num = int(episode_number)
    except (ValueError, TypeError):
        return None

    cache_k = f"imdb:{imdb_id}:{s_num}:{ep_num}"
    cached = getattr(temp, "EPISODE_TITLES_CACHE", {}).get(cache_k)
    if cached:
        return {"episode_title": cached, "season": s_num, "episode": ep_num}

    imdb_url = f"https://www.imdb.com/title/{imdb_id}/episodes/?season={s_num}"
    logger.info(f"[EPISODE TITLE] REQUEST IMDB SEASON url={imdb_url}")
    html_content = await asyncio.to_thread(_fetch_url_sync, imdb_url)
    if not html_content:
        return None

    import html as _html
    title_m = re.search(
        rf'S{s_num},\s*Ep{ep_num}.*?<a[^>]*href=["\']/title/[^"\']+["\'][^>]*>(.*?)</a>',
        html_content,
        re.DOTALL | re.IGNORECASE
    )
    if title_m:
        ep_t = _html.unescape(title_m.group(1)).strip()
        if ep_t and not ep_t.lower().startswith("episode"):
            if not hasattr(temp, "EPISODE_TITLES_CACHE"):
                temp.EPISODE_TITLES_CACHE = {}
            temp.EPISODE_TITLES_CACHE[cache_k] = ep_t
            logger.info(f"[EPISODE TITLE] SUCCESS source=IMDb season={s_num} episode={ep_num} title={ep_t}")
            return {"episode_title": ep_t, "season": s_num, "episode": ep_num}

    return None


async def get_public_episode_title(series_name: str = "", tmdb_id: str = None, imdb_id: str = None, season: int = 1, episode: int = 1) -> str:
    """
    Resolves authoritative episode title using priority:
    1. TMDB public webpage data
    2. IMDb public data
    3. Fallback: 'Episode 01'
    """
    try:
        s_num = int(season)
    except Exception:
        s_num = 1
    try:
        ep_num = int(episode)
    except Exception:
        ep_num = 1

    default_fallback = f"Episode {ep_num:02d}"

    # Check cache first
    if tmdb_id:
        cache_k = f"tmdb:{tmdb_id}:{s_num}:{ep_num}"
        if cache_k in getattr(temp, "EPISODE_TITLES_CACHE", {}):
            return temp.EPISODE_TITLES_CACHE[cache_k]
    if imdb_id:
        cache_k = f"imdb:{imdb_id}:{s_num}:{ep_num}"
        if cache_k in getattr(temp, "EPISODE_TITLES_CACHE", {}):
            return temp.EPISODE_TITLES_CACHE[cache_k]

    # 1. Primary: TMDB
    if tmdb_id and str(tmdb_id).strip() not in ("0", "None", "N/A", ""):
        try:
            res = await get_tmdb_public_episode_metadata(tmdb_id, s_num, ep_num)
            if res and res.get("episode_title") and not res["episode_title"].startswith("Episode "):
                return res["episode_title"]
        except Exception as e:
            logger.warning(f"[EPISODE TITLE] TMDB error: {e}")

    # 2. Fallback: IMDb
    if imdb_id and str(imdb_id).startswith("tt"):
        try:
            logger.info(f"[EPISODE TITLE] FALLBACK source=IMDb season={s_num} episode={ep_num}")
            res = await get_imdb_public_episode_metadata(imdb_id, s_num, ep_num)
            if res and res.get("episode_title") and not res["episode_title"].startswith("Episode "):
                return res["episode_title"]
        except Exception as e:
            logger.warning(f"[EPISODE TITLE] IMDb error: {e}")

    logger.info(f"[EPISODE TITLE] DEFAULT season={s_num} episode={ep_num}")
    return default_fallback


async def prefetch_series_episode_titles(series_name: str = "", tmdb_id: str = None, imdb_id: str = None, pairs: list = None) -> dict[tuple[int, int], str]:
    """
    Prefetches all unique (season, episode) titles concurrently/in-batch before sending files.
    Returns: {(season, episode): "Episode Title"}
    """
    if not pairs:
        return {}

    unique_pairs = list(dict.fromkeys(pairs))
    seasons_needed = list(set(s for s, ep in unique_pairs))

    # Fetch seasons from TMDB concurrently
    if tmdb_id and str(tmdb_id).strip() not in ("0", "None", "N/A", ""):
        tasks = [get_tmdb_public_season_episodes(tmdb_id, s) for s in seasons_needed]
        await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for s, ep in unique_pairs:
        t = await get_public_episode_title(series_name, tmdb_id=tmdb_id, imdb_id=imdb_id, season=s, episode=ep)
        results[(s, ep)] = t

    return results


async def get_tmdb_by_url(url_or_path):
    """
    Public TMDB metadata resolver for backward compatibility.
    """
    return await get_tmdb_public_metadata(url_or_path)


async def get_imdb_metadata_direct(imdb_id: str):
    """
    Fast direct IMDb metadata resolver using IMDb Suggestion API.
    Bypasses Cinemagoer and does not block the Pyrogram event loop.
    """
    imdb_id = str(imdb_id).strip().lower()
    if not imdb_id.startswith("tt"):
        imdb_id = f"tt{imdb_id}"

    logger.info(f"[DIRECT IMDb] START id={imdb_id}")

    url = f"https://v3.sg.media-imdb.com/suggestion/titles/t/{imdb_id}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    timeout = aiohttp.ClientTimeout(total=8, connect=4, sock_read=6)

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                logger.info(f"[DIRECT IMDb] HTTP status={resp.status}")
                if resp.status != 200:
                    logger.warning(f"[DIRECT IMDb] FAILED reason=HTTP_{resp.status} id={imdb_id}")
                    return None
                data = await resp.json(content_type=None)

        items = data.get("d") or []
        exact = None
        for item in items:
            if str(item.get("id", "")).lower() == imdb_id:
                exact = item
                break

        if not exact:
            logger.warning(f"[DIRECT IMDb] FAILED reason=NOT_FOUND id={imdb_id}")
            return None

        qid = str(exact.get("qid") or exact.get("q") or "").lower()
        is_series = any(x in qid for x in ("tv", "series", "tvseries", "tv-mini-series"))
        kind = "tv series" if is_series else "movie"

        image = exact.get("i")
        poster = None
        if isinstance(image, dict):
            poster = image.get("imageUrl") or image.get("url")

        title = exact.get("l")
        year = exact.get("y")

        logger.info(
            f"[DIRECT IMDb] FOUND\n"
            f"title={title}\n"
            f"year={year}\n"
            f"kind={kind}"
        )

        return {
            "title": title,
            "year": str(year) if year else None,
            "kind": kind,
            "imdb_id": exact.get("id", imdb_id),
            "tmdb_id": None,
            "original_language": None,
            "poster": poster,
            "posters": [poster] if poster else [],
            "rating": "",
            "genres": "",
            "plot": "",
            "seasons": None,
            "source": "imdb_direct",
        }

    except asyncio.TimeoutError:
        logger.error(f"[DIRECT IMDb] FAILED reason=TIMEOUT id={imdb_id}")
        return None
    except Exception as e:
        logger.exception(f"[DIRECT IMDb] FAILED reason=ERROR id={imdb_id}: {e}")
        return None


async def get_poster(query, bulk=False, id=False, file=None):
    try:
        query_str = str(query).strip()

        # ── 0. Direct TMDB URL Resolution ──────────────────────────────────────────
        if "themoviedb.org" in query_str:
            tmdb_direct = await get_tmdb_by_url(query_str)
            if tmdb_direct:
                return tmdb_direct

        imdb_url_match = re.search(r"(?:imdb\.com/title/)?(tt\d{5,12})", query_str, re.IGNORECASE)

        # ── 1. Fast Public TMDB lookup (if enabled and not explicit tt ID) ───────────
        if TMDB_DATA and not id and not imdb_url_match:
            try:
                tmdb_res = await get_public_tmdb_poster(query, bulk=bulk, id=id, file=file)
                if tmdb_res:
                    return tmdb_res
            except Exception as te:
                logger.warning(f"Public TMDB lookup error: {te}")

        if id or (imdb_url_match and not bulk):
            if imdb_url_match:
                movieid = re.sub(r"^tt", "", imdb_url_match.group(1).strip(), flags=re.IGNORECASE)
            else:
                movieid = re.sub(r"^tt", "", query_str, flags=re.IGNORECASE)

            clean_tt = f"tt{movieid}"

            # ── 1. Fast IMDb Suggestion API by ID (Primary - ~100ms) ───────────
            try:
                s_url = f"https://v3.sg.media-imdb.com/suggestion/titles/t/{clean_tt}.json"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                page_data = await asyncio.to_thread(_fetch_url_sync, s_url)
                if page_data:
                    import json as _json
                    s_data = _json.loads(page_data)
                    if "d" in s_data and s_data["d"]:
                        item = s_data["d"][0]
                        q_type = str(item.get("qid") or item.get("q") or "").lower()
                        is_tv = any(k in q_type for k in ["tv", "series"])
                        kind = "tv series" if is_tv else "movie"
                        poster_url = item.get("i", {}).get("imageUrl") if isinstance(item.get("i"), dict) else None
                        return {
                            'title': item.get("l"),
                            'votes': None,
                            'aka': None,
                            'seasons': None,
                            'box_office': None,
                            'localized_title': item.get("l"),
                            'kind': kind,
                            'imdb_id': item.get("id", clean_tt),
                            'cast': item.get("s"),
                            'runtime': None,
                            'countries': None,
                            'certificates': None,
                            'languages': None,
                            'director': None,
                            'writer': None,
                            'producer': None,
                            'composer': None,
                            'cinematographer': None,
                            'music_team': None,
                            'distributors': None,
                            'release_date': str(item.get("y", "N/A")),
                            'year': item.get("y"),
                            'genres': "Drama",
                            'poster': poster_url,
                            'plot': item.get("s", ""),
                            'rating': "7.5",
                            'url': f'https://www.imdb.com/title/{clean_tt}'
                        }
            except Exception as se:
                logger.warning(f"Fast IMDb suggestion API lookup failed for {clean_tt}: {se}")

            # ── 2. Direct IMDb HTML Scraper by ID (~200ms) ────────────────────
            try:
                imdb_web_url = f"https://www.imdb.com/title/{clean_tt}/"
                page_html = await asyncio.to_thread(_fetch_url_sync, imdb_web_url)
                if page_html:
                    import html as _html
                    t_m = re.search(r'<meta property="og:title" content="([^"]+)"', page_html)
                    if t_m:
                        raw_title = _html.unescape(t_m.group(1))
                        c_title = re.sub(r'\s*-\s*IMDb.*$', '', raw_title).strip()
                        y_m = re.search(r'\((\d{4})\)', c_title)
                        y_val = y_m.group(1) if y_m else None
                        c_title = re.sub(r'\s*\(\d{4}\)\s*$', '', c_title).strip()

                        img_m = re.search(r'<meta property="og:image" content="([^"]+)"', page_html)
                        p_val = img_m.group(1) if img_m else None

                        desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', page_html)
                        plot_val = _html.unescape(desc_m.group(1)) if desc_m else ""

                        is_tv = any(k in page_html.lower() for k in ['"type":"tvseries"', '"type":"tvepisode"', 'tv series'])
                        kind = "tv series" if is_tv else "movie"

                        return {
                            'title': c_title,
                            'votes': None,
                            'aka': None,
                            'seasons': None,
                            'box_office': None,
                            'localized_title': c_title,
                            'kind': kind,
                            'imdb_id': clean_tt,
                            'cast': None,
                            'runtime': None,
                            'countries': None,
                            'certificates': None,
                            'languages': None,
                            'director': None,
                            'writer': None,
                            'producer': None,
                            'composer': None,
                            'cinematographer': None,
                            'music_team': None,
                            'distributors': None,
                            'release_date': str(y_val or "N/A"),
                            'year': y_val,
                            'genres': "Drama",
                            'poster': p_val,
                            'plot': plot_val,
                            'rating': "7.5",
                            'url': imdb_web_url
                        }
            except Exception as he:
                logger.warning(f"Direct IMDb HTML scraper lookup failed for {clean_tt}: {he}")

        else:
            query = query_str.lower()
            title = query
            year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1])
                title = (query.replace(year, "")).strip()
            elif file is not None:
                year = re.findall(r'[1-2]\d{3}', str(file), re.IGNORECASE)
                if year:
                    year = list_to_str(year[:1]) 
            else:
                year = None

            movieid = None
            try:
                clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", title).strip()
                if clean_q:
                    first_ch = clean_q[0].lower()
                    import urllib.parse
                    enc_q = urllib.parse.quote(clean_q.lower())
                    s_url = f"https://v3.sg.media-imdb.com/suggestion/titles/{first_ch}/{enc_q}.json"
                    page_data = await asyncio.to_thread(_fetch_url_sync, s_url)
                    if page_data:
                        import json as _json
                        s_data = _json.loads(page_data)
                        if "d" in s_data and s_data["d"]:
                            first_match = s_data["d"][0]
                            if bulk:
                                class MockMovie(dict):
                                    def __init__(self, d):
                                        super().__init__(d)
                                        self.movieID = re.sub(r"^tt", "", d.get("id", ""))
                                        self.data = d
                                    def __getitem__(self, k):
                                        return self.get(k)
                                return [MockMovie({'title': item.get('l'), 'year': item.get('y'), 'kind': 'movie', 'id': item.get('id')}) for item in s_data["d"] if item.get('id')]
                            movieid = re.sub(r"^tt", "", str(first_match.get("id", "")))
            except Exception as fe:
                logger.warning(f"IMDb suggestion search failed for '{title}': {fe}")

            if not movieid:
                try:
                    search_results = await asyncio.wait_for(
                        asyncio.to_thread(imdb.search_movie, title.lower(), results=10),
                        timeout=5.0
                    )
                    if search_results:
                        if year:
                            filtered = list(filter(lambda k: str(k.get('year')) == str(year), search_results))
                            if not filtered:
                                filtered = search_results
                        else:
                            filtered = search_results
                        candidates = list(filter(lambda k: k.get('kind') in ['movie', 'tv series', 'episode'], filtered))
                        if not candidates:
                            candidates = filtered
                        if bulk:
                            return candidates
                        if candidates:
                            movieid = getattr(candidates[0], "movieID", None) or candidates[0].get("imdbID")
                except Exception as se:
                    logger.warning(f"Cinemagoer search_movie error for '{title}': {se}")

            if not movieid:
                return None

        movie = None
        try:
            movie = await asyncio.wait_for(
                asyncio.to_thread(imdb.get_movie, movieid),
                timeout=8.0
            )
        except Exception as e:
            logger.warning(f"Cinemagoer get_movie error for {movieid}: {e}")

        if movie and movie.get("title"):
            if movie.get("original air date"):
                date = movie["original air date"]
            elif movie.get("year"):
                date = movie.get("year")
            else:
                date = "N/A"
            plot = ""
            if not LONG_IMDB_DESCRIPTION:
                plot = movie.get('plot')
                if plot and len(plot) > 0:
                    plot = plot[0]
            else:
                plot = movie.get('plot outline')
            if plot and len(plot) > 800:
                plot = plot[0:800] + "..."

            return {
                'title': movie.get('title'),
                'votes': movie.get('votes'),
                "aka": list_to_str(movie.get("akas")),
                "seasons": movie.get("number of seasons"),
                "box_office": movie.get('box office'),
                'localized_title': movie.get('localized title'),
                'kind': movie.get("kind"),
                "imdb_id": f"tt{movie.get('imdbID') or movieid}",
                "cast": list_to_str(movie.get("cast")),
                "runtime": list_to_str(movie.get("runtimes")),
                "countries": list_to_str(movie.get("countries")),
                "certificates": list_to_str(movie.get("certificates")),
                "languages": list_to_str(movie.get("languages")),
                "director": list_to_str(movie.get("director")),
                "writer": list_to_str(movie.get("writer")),
                "producer": list_to_str(movie.get("producer")),
                "composer": list_to_str(movie.get("composer")),
                "cinematographer": list_to_str(movie.get("cinematographer")),
                "music_team": list_to_str(movie.get("music department")),
                "distributors": list_to_str(movie.get("distributors")),
                'release_date': str(date),
                'year': movie.get('year'),
                'genres': list_to_str(movie.get("genres")),
                'poster': movie.get('full-size cover url') or movie.get('cover url'),
                'plot': plot or "",
                'rating': str(movie.get("rating") or ""),
                'url': f'https://www.imdb.com/title/tt{movieid}'
            }

        # ── Fallback: IMDb Suggestion API by ID ─────────────────────────────────────
        try:
            clean_tt = f"tt{movieid}"
            url = f"https://v3.sg.media-imdb.com/suggestion/titles/t/{clean_tt}.json"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "d" in data and len(data["d"]) > 0:
                            item = data["d"][0]
                            q_type = str(item.get("qid") or item.get("q") or "").lower()
                            is_tv = any(k in q_type for k in ["tv", "series"])
                            kind = "tv series" if is_tv else "movie"
                            poster_url = item.get("i", {}).get("imageUrl") if isinstance(item.get("i"), dict) else None
                            return {
                                'title': item.get("l"),
                                'votes': None,
                                'aka': None,
                                'seasons': None,
                                'box_office': None,
                                'localized_title': item.get("l"),
                                'kind': kind,
                                'imdb_id': item.get("id", clean_tt),
                                'cast': item.get("s"),
                                'runtime': None,
                                'countries': None,
                                'certificates': None,
                                'languages': None,
                                'director': None,
                                'writer': None,
                                'producer': None,
                                'composer': None,
                                'cinematographer': None,
                                'music_team': None,
                                'distributors': None,
                                'release_date': str(item.get("y", "N/A")),
                                'year': item.get("y"),
                                'genres': "Drama",
                                'poster': poster_url,
                                'plot': item.get("s", ""),
                                'rating': "7.5",
                                'url': f'https://www.imdb.com/title/{clean_tt}'
                            }
        except Exception as e:
            logger.warning(f"IMDb suggestion API fallback failed for {movieid}: {e}")

        # ── Fallback: Direct IMDb HTML Meta-Tag Scraper ───────────────────────────
        try:
            clean_tt = f"tt{movieid}"
            imdb_web_url = f"https://www.imdb.com/title/{clean_tt}/"
            page_html = await asyncio.to_thread(_fetch_url_sync, imdb_web_url)
            if page_html:
                import html as _html
                # Title
                t_m = re.search(r'<meta property="og:title" content="([^"]+)"', page_html)
                if t_m:
                    raw_title = _html.unescape(t_m.group(1))
                    # Remove " - IMDb" and trailing year/parentheses
                    c_title = re.sub(r'\s*-\s*IMDb.*$', '', raw_title).strip()
                    y_m = re.search(r'\((\d{4})\)', c_title)
                    y_val = y_m.group(1) if y_m else None
                    c_title = re.sub(r'\s*\(\d{4}\)\s*$', '', c_title).strip()

                    # Poster
                    img_m = re.search(r'<meta property="og:image" content="([^"]+)"', page_html)
                    p_val = img_m.group(1) if img_m else None

                    # Description / Plot
                    desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', page_html)
                    plot_val = _html.unescape(desc_m.group(1)) if desc_m else ""

                    is_tv = any(k in page_html.lower() for k in ['"type":"tvseries"', '"type":"tvepisode"', 'tv series'])
                    kind = "tv series" if is_tv else "movie"

                    return {
                        'title': c_title,
                        'votes': None,
                        'aka': None,
                        'seasons': None,
                        'box_office': None,
                        'localized_title': c_title,
                        'kind': kind,
                        'imdb_id': clean_tt,
                        'cast': None,
                        'runtime': None,
                        'countries': None,
                        'certificates': None,
                        'languages': None,
                        'director': None,
                        'writer': None,
                        'producer': None,
                        'composer': None,
                        'cinematographer': None,
                        'music_team': None,
                        'distributors': None,
                        'release_date': str(y_val or "N/A"),
                        'year': y_val,
                        'genres': "Drama",
                        'poster': p_val,
                        'plot': plot_val,
                        'rating': "7.5",
                        'url': imdb_web_url
                    }
        except Exception as he:
            logger.warning(f"Direct IMDb HTML scraper fallback failed for {movieid}: {he}")

        return None
    except Exception as e:
        logger.error(f"get_poster unexpected error for query='{query}': {e}")
        return None

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def broadcast_messages_group(chat_id, message):
    try:
        kd = await message.copy(chat_id=chat_id)
        try:
            await kd.pin()
        except:
            pass
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages_group(chat_id, message)
    except Exception as e:
        return False, "Error"
    
async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
    }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=usr_agent, timeout=aiohttp.ClientTimeout(total=6)) as response:
                if response.status == 200:
                    text_content = await response.text()
                    if BeautifulSoup:
                        soup = BeautifulSoup(text_content, 'html.parser')
                        titles = soup.find_all('h3')
                        return [title.getText() for title in titles]
    except Exception as e:
        logger.warning(f"[SEARCH GAGALA ERROR] {e}")
    return []

async def get_settings(group_id):
    settings = await db.get_settings(group_id)
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    await db.update_settings(group_id, current)
    
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]  

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
           
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time

def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def gfilterparser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'



async def get_clone_shortlink(link, url, api):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link
                           
async def get_shortlink(chat_id, link):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'shortlink' in settings.keys():
        URL = settings['shortlink']
        API = settings['shortlink_api']
    else:
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL.startswith("shorturllink") or URL.startswith("terabox.in") or URL.startswith("urlshorten.in"):
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
    
async def get_tutorial(chat_id):
    settings = await get_settings(chat_id) #fetching settings for group
    return settings['tutorial']
        
async def get_verify_shorted_link(link, url, api):
    API = api
    URL = url
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
        
async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    if user.id in TOKENS.keys():
        TKN = TOKENS[user.id]
        if token in TKN.keys():
            is_used = TKN[token]
            if is_used == True:
                return False
            else:
                return True
    else:
        return False

async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    link = f"{link}verify-{user.id}-{token}"
    shortened_verify_url = await get_verify_shorted_link(link, VERIFY_SHORTLINK_URL, VERIFY_SHORTLINK_API)
    if VERIFY_SECOND_SHORTNER == True:
        snd_link = await get_verify_shorted_link(shortened_verify_url, VERIFY_SND_SHORTLINK_URL, VERIFY_SND_SHORTLINK_API)
        return str(snd_link)
    else:
        return str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    TOKENS[user.id] = {token: True}
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    VERIFIED[user.id] = str(today)

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    if user.id in VERIFIED.keys():
        EXP = VERIFIED[user.id]
        years, month, day = EXP.split('-')
        comp = date(int(years), int(month), int(day))
        if comp<today:
            return False
        else:
            return True
    else:
        return False  
    
async def send_all(bot, userid, files, ident, chat_id, user_name, query):
    settings = await get_settings(chat_id)
    if 'is_shortlink' in settings.keys():
        ENABLE_SHORTLINK = settings['is_shortlink']
    else:
        await save_group_settings(chat_id, 'is_shortlink', False)
        ENABLE_SHORTLINK = False
    try:
        if ENABLE_SHORTLINK:
            for file in files:
                title = file["file_name"]
                size = get_size(file["file_size"])
                if not await db.has_premium_access(userid) and SHORTLINK_MODE == True:
                    await bot.send_message(chat_id=userid, text=f"<b>Hᴇʏ ᴛʜᴇʀᴇ {user_name} 👋🏽 \n\n✅ Sᴇᴄᴜʀᴇ ʟɪɴᴋ ᴛᴏ ʏᴏᴜʀ ғɪʟᴇ ʜᴀs sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴇᴇɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ\n\n🗃️ Fɪʟᴇ Nᴀᴍᴇ : {title}\n🔖 Fɪʟᴇ Sɪᴢᴇ : {size}</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Dᴏᴡɴʟᴏᴀᴅ 📥", url=await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}"))]]))
        else:
            for file in files:
                f_caption = file["caption"]
                title = file["file_name"]
                size = get_size(file["file_size"])
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption = CUSTOM_FILE_CAPTION.format(
                            file_name='' if title is None else title,
                            file_size='' if size is None else size,
                            file_caption='' if f_caption is None else f_caption
                        )
                    except Exception as e:
                        print(e)
                        f_caption = f_caption
                if f_caption is None:
                    f_caption = f"{title}"
                await bot.send_cached_media(
                    chat_id=userid,
                    file_id=file["file_id"],
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False,
                    reply_markup=InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
                            InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                        ],[
                            InlineKeyboardButton("Bᴏᴛ Oᴡɴᴇʀ", url=OWNER_LNK)
                        ]]
                    )
                )
    except UserIsBlocked:
        await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
    except PeerIdInvalid:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
    except Exception as e:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
        
async def get_cap(settings, remaining_seconds, files, query, total_results, search):
    if settings["imdb"]:
        IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
        if IMDB_CAP:
            cap = IMDB_CAP
            cap+="<b>\n\n<u>🍿 Your Movie Files 👇</u></b>\n\n"
            for file in files:
                cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {get_filter_button_filename_text(file['file_name'])}\n\n</a></b>"
        else:
            imdb = await get_poster(search, file=(files[0])["file_name"]) if settings["imdb"] else None
            if imdb:
                TEMPLATE = script.IMDB_TEMPLATE_TXT
                cap = TEMPLATE.format(
                    qurey=search,
                    title=imdb['title'],
                    votes=imdb['votes'],
                    aka=imdb["aka"],
                    seasons=imdb["seasons"],
                    box_office=imdb['box_office'],
                    localized_title=imdb['localized_title'],
                    kind=imdb['kind'],
                    imdb_id=imdb["imdb_id"],
                    cast=imdb["cast"],
                    runtime=imdb["runtime"],
                    countries=imdb["countries"],
                    certificates=imdb["certificates"],
                    languages=imdb["languages"],
                    director=imdb["director"],
                    writer=imdb["writer"],
                    producer=imdb["producer"],
                    composer=imdb["composer"],
                    cinematographer=imdb["cinematographer"],
                    music_team=imdb["music_team"],
                    distributors=imdb["distributors"],
                    release_date=imdb['release_date'],
                    year=imdb['year'],
                    genres=imdb['genres'],
                    poster=imdb['poster'],
                    plot=imdb['plot'],
                    rating=imdb['rating'],
                    url=imdb['url'],
                    **locals()
                )
                cap+="<b>\n\n<u>🍿 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {get_filter_button_filename_text(file['file_name'])}\n\n</a></b>"
            else:
                cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title}\n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
                cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {get_filter_button_filename_text(file['file_name'])}\n\n</a></b>"
    else:
        cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title} \n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
        cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
        for file in files:
            cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {get_filter_button_filename_text(file['file_name'])}\n\n</a></b>"
    return cap


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:]
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


# ─── Robust Safe Message Deletion & Cleanup System ───────────────────────────
DELETE_IN_PROGRESS = set()
_DELETE_SEMAPHORE = asyncio.Semaphore(5)
_FILTER_DELETE_TASKS = {}

async def safe_delete_message(client, chat_id: int, message_id: int, retries: int = 2) -> bool:
    """
    Safely deletes a message with duplicate prevention, concurrency limiting, 
    and connection error handling to prevent Pyrogram hanging or crashing.
    """
    if not client or not chat_id or not message_id:
        return False

    delete_key = f"{chat_id}:{message_id}"
    if delete_key in DELETE_IN_PROGRESS:
        logger.info(f"[CLEANUP DELETE SKIPPED] chat={chat_id} message={message_id}")
        return False

    DELETE_IN_PROGRESS.add(delete_key)
    try:
        logger.info(f"[CLEANUP DELETE START] chat={chat_id} message={message_id}")
        async with _DELETE_SEMAPHORE:
            for attempt in range(max(1, retries)):
                try:
                    await asyncio.wait_for(
                        client.delete_messages(chat_id, message_id),
                        timeout=10.0
                    )
                    logger.info(f"[CLEANUP DELETE SUCCESS] chat={chat_id} message={message_id}")
                    return True
                except asyncio.CancelledError:
                    raise
                except asyncio.TimeoutError:
                    logger.warning(f"[CLEANUP TELEGRAM CONNECTION ERROR] Timeout on chat={chat_id} message={message_id} attempt={attempt+1}/{retries}")
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                except Exception as e:
                    err_str = str(e).lower()
                    if "connection lost" in err_str or "timeout" in err_str or "rpc" in err_str or "network" in err_str or "socket" in err_str:
                        logger.warning(f"[CLEANUP TELEGRAM CONNECTION ERROR] chat={chat_id} message={message_id} error={e}")
                    else:
                        logger.warning(f"[CLEANUP DELETE FAILED] chat={chat_id} message={message_id} error={e}")
                    
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    else:
                        return False
            return False
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"[CLEANUP DELETE FAILED] chat={chat_id} message={message_id} error={e}")
        return False
    finally:
        DELETE_IN_PROGRESS.discard(delete_key)

async def safe_delete_messages(client, chat_id: int, message_ids: list[int] | set[int], retries: int = 2) -> bool:
    """Safely deletes multiple messages without throwing unhandled exceptions."""
    if not client or not chat_id or not message_ids:
        return False
    all_ok = True
    for msg_id in list(message_ids):
        try:
            res = await safe_delete_message(client, chat_id, msg_id, retries=retries)
            if not res:
                all_ok = False
        except Exception as e:
            logger.warning(f"[CLEANUP] delete skipped: {e}")
            all_ok = False
            continue
    return all_ok

async def delete_message_after(client, chat_id: int, message_id: int, delay: int = 600):
    try:
        await asyncio.sleep(delay)
        await safe_delete_message(client, chat_id, message_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"[CLEANUP] Telegram delete failed: {e}")
    finally:
        _FILTER_DELETE_TASKS.pop((int(chat_id), int(message_id)), None)

def schedule_filter_message_delete(client, chat_id: int, message_id: int, delay: int = 600):
    """
    Schedules auto-deletion of a temporary bot filter/result message after `delay` seconds.
    For group chats (chat_id < 0), default delay is 18,000s (5 hours).
    For private messages (chat_id > 0), default delay is 600s (10 mins).
    If the message is refreshed/edited, cancels any pending task and resets the TTL.
    """
    if not client or not chat_id or not message_id:
        return None

    c_id = int(chat_id)
    # If in group chat and default 600 was passed, use 5 hours (18,000s)
    if c_id < 0 and delay == 600:
        delay = 18000

    key = (c_id, int(message_id))
    old_task = _FILTER_DELETE_TASKS.get(key)
    if old_task and not old_task.done():
        try:
            old_task.cancel()
        except Exception:
            pass

    logger.info(f"[AUTO DELETE SCHEDULED]\nchat_id={chat_id}\nmessage_id={message_id}\ndelay={delay}")
    task = asyncio.create_task(delete_message_after(client, chat_id, message_id, delay))
    _FILTER_DELETE_TASKS[key] = task
    return task

_SET_FILTER_DELETE_TASKS = {}
SET_FILTER_AUTO_DELETE_DELAY = 18000  # 5 hours = 18,000 seconds

async def delete_set_filter_reply(message_or_client, chat_id: int = None, message_id: int = None, delay: int = 18000):
    """
    Dedicated safe deletion worker ONLY for Set Filters replies.
    Waits 5 hours (18000s) and deletes the message safely with structured logging.
    """
    client = None
    target_msg = None
    if hasattr(message_or_client, "delete") and hasattr(message_or_client, "chat"):
        target_msg = message_or_client
        c_id = getattr(getattr(target_msg, "chat", None), "id", None) or chat_id
        m_id = getattr(target_msg, "id", None) or message_id
    else:
        client = message_or_client
        c_id = chat_id
        m_id = message_id

    key = (int(c_id), int(m_id)) if (c_id and m_id) else None

    try:
        await asyncio.sleep(delay)
        logger.info(
            f"[SET FILTER AUTO DELETE]\n"
            f"action=DELETE\n"
            f"chat_id={c_id}\n"
            f"message_id={m_id}"
        )
        if target_msg is not None:
            await target_msg.delete()
        elif client is not None and c_id and m_id:
            await safe_delete_message(client, c_id, m_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(
            f"[SET FILTER AUTO DELETE]\n"
            f"action=FAILED\n"
            f"error={e}"
        )
    finally:
        if key:
            _SET_FILTER_DELETE_TASKS.pop(key, None)

def schedule_set_filter_reply_delete(message_or_client, chat_id: int = None, message_id: int = None, delay: int = 18000):
    """
    Schedules background auto-deletion ONLY for Set Filters replies after 5 hours (18,000s).
    Non-blocking, retains chat_id/message_id, cancels existing task to avoid duplicate tasks.
    """
    if hasattr(message_or_client, "chat") and hasattr(message_or_client, "id"):
        target_msg = message_or_client
        c_id = getattr(target_msg.chat, "id", None)
        m_id = getattr(target_msg, "id", None)
        client = None
    else:
        target_msg = None
        client = message_or_client
        c_id = chat_id
        m_id = message_id

    if not c_id or not m_id:
        return None

    key = (int(c_id), int(m_id))
    old_task = _SET_FILTER_DELETE_TASKS.get(key)
    if old_task and not old_task.done():
        try:
            old_task.cancel()
        except Exception:
            pass

    logger.info(
        f"[SET FILTER AUTO DELETE]\n"
        f"chat_id={c_id}\n"
        f"message_id={m_id}\n"
        f"delete_after={delay}"
    )

    if target_msg is not None:
        task = asyncio.create_task(delete_set_filter_reply(target_msg, delay=delay))
    else:
        task = asyncio.create_task(delete_set_filter_reply(client, chat_id=c_id, message_id=m_id, delay=delay))

    _SET_FILTER_DELETE_TASKS[key] = task
    return task

async def cleanup_expired_messages():
    """Periodic cleanup worker for expired state entries."""
    pass

async def _cleanup_scheduler_loop():
    while True:
        try:
            await cleanup_expired_messages()
        except Exception as e:
            logger.exception(f"[CLEANUP SCHEDULER ERROR] {e}")
        await asyncio.sleep(60)

def start_cleanup_schedulers(client=None):
    """Starts background cleanup scheduler safely."""
    return asyncio.create_task(_cleanup_scheduler_loop())


# ─── Resilient Telegram Message Senders with Exponential Backoff ─────────────

_TRANSIENT_EXCEPTIONS = (
    OSError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)

async def safe_reply_text(message, text: str, max_retries: int = 3, **kwargs):
    """
    Safely reply to a message with conservative exponential backoff on transient network/connection drops.
    Catches OSError: Connection lost and prevents handler failure.
    """
    if not message:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            return await message.reply_text(text, **kwargs)
        except _TRANSIENT_EXCEPTIONS as e:
            logger.warning(
                f"[TELEGRAM SEND RETRY]\n"
                f"error={e}\n"
                f"type=reply_text\n"
                f"attempt={attempt}/{max_retries}"
            )
            if attempt < max_retries:
                await asyncio.sleep(attempt * 1.0)
            else:
                logger.error(
                    f"[AUTO FILTER SEND ERROR]\n"
                    f"error={e}\n"
                    f"status=failed_after_retries\n"
                    f"action=reply_text"
                )
                return None
        except Exception as e:
            err_msg = str(e).lower()
            if "connection lost" in err_msg or "network" in err_msg or "timeout" in err_msg:
                logger.warning(f"[TELEGRAM SEND CONNECTION ERROR] attempt={attempt}/{max_retries} error={e}")
                if attempt < max_retries:
                    await asyncio.sleep(attempt * 1.0)
                    continue
            logger.warning(f"[TELEGRAM REPLY TEXT ERROR] {e}")
            return None


async def safe_reply_photo(message, photo, max_retries: int = 3, **kwargs):
    """
    Safely reply with photo with conservative exponential backoff on transient network/connection drops.
    """
    if not message:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            return await message.reply_photo(photo=photo, **kwargs)
        except _TRANSIENT_EXCEPTIONS as e:
            logger.warning(
                f"[TELEGRAM SEND RETRY]\n"
                f"error={e}\n"
                f"type=reply_photo\n"
                f"attempt={attempt}/{max_retries}"
            )
            if attempt < max_retries:
                await asyncio.sleep(attempt * 1.0)
            else:
                logger.error(
                    f"[AUTO FILTER SEND ERROR]\n"
                    f"error={e}\n"
                    f"status=failed_after_retries\n"
                    f"action=reply_photo"
                )
                return None
        except Exception as e:
            err_msg = str(e).lower()
            if "connection lost" in err_msg or "network" in err_msg or "timeout" in err_msg:
                logger.warning(f"[TELEGRAM SEND CONNECTION ERROR] attempt={attempt}/{max_retries} error={e}")
                if attempt < max_retries:
                    await asyncio.sleep(attempt * 1.0)
                    continue
            # Non-transient errors (e.g. MediaEmpty) re-raised for caller fallback
            raise e


async def safe_send_message(client, chat_id, text: str, max_retries: int = 3, **kwargs):
    """
    Safely send message with conservative exponential backoff on transient network/connection drops.
    """
    if not client or not chat_id:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            return await client.send_message(chat_id, text, **kwargs)
        except _TRANSIENT_EXCEPTIONS as e:
            logger.warning(
                f"[TELEGRAM SEND RETRY]\n"
                f"error={e}\n"
                f"type=send_message\n"
                f"attempt={attempt}/{max_retries}"
            )
            if attempt < max_retries:
                await asyncio.sleep(attempt * 1.0)
            else:
                logger.error(
                    f"[AUTO FILTER SEND ERROR]\n"
                    f"error={e}\n"
                    f"status=failed_after_retries\n"
                    f"action=send_message"
                )
                return None
        except Exception as e:
            err_msg = str(e).lower()
            if "connection lost" in err_msg or "network" in err_msg or "timeout" in err_msg:
                logger.warning(f"[TELEGRAM SEND CONNECTION ERROR] attempt={attempt}/{max_retries} error={e}")
                if attempt < max_retries:
                    await asyncio.sleep(attempt * 1.0)
                    continue
            logger.warning(f"[TELEGRAM SEND MESSAGE ERROR] {e}")
            return None


async def safe_edit_text(message_or_query, text: str, max_retries: int = 3, **kwargs):
    """
    Safely edit text message with conservative exponential backoff.
    """
    if not message_or_query:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            return await message_or_query.edit_text(text, **kwargs)
        except _TRANSIENT_EXCEPTIONS as e:
            logger.warning(f"[TELEGRAM EDIT RETRY] error={e} attempt={attempt}/{max_retries}")
            if attempt < max_retries:
                await asyncio.sleep(attempt * 1.0)
            else:
                logger.error(f"[AUTO FILTER SEND ERROR] error={e} status=failed_after_retries action=edit_text")
                return None
        except Exception as e:
            err_msg = str(e).lower()
            if "message is not modified" in err_msg:
                return message_or_query
            if "connection lost" in err_msg or "network" in err_msg or "timeout" in err_msg:
                if attempt < max_retries:
                    await asyncio.sleep(attempt * 1.0)
                    continue
            logger.warning(f"[TELEGRAM EDIT TEXT ERROR] {e}")
            return None


# ─── Telegram Connection Watchdog ─────────────────────────────────────────────
_WATCHDOG_TASK = None

async def _telegram_watchdog_loop(client, check_interval: int = 30):
    """
    Single-instance connection health watchdog.
    Monitors Telegram connectivity and triggers safe reconnection upon connection loss.
    """
    logger.info("[TELEGRAM WATCHDOG] Connection health monitor active.")
    consecutive_fails = 0

    while True:
        try:
            await asyncio.sleep(check_interval)

            is_connected = getattr(client, "is_connected", True)
            if not is_connected:
                consecutive_fails += 1
                logger.warning(
                    f"[TELEGRAM CONNECTION]\n"
                    f"status=DISCONNECTED\n"
                    f"reason=is_connected is False\n"
                    f"attempt={consecutive_fails}"
                )
                logger.info(
                    f"[TELEGRAM CONNECTION]\n"
                    f"action=RECONNECT\n"
                    f"attempt={consecutive_fails}"
                )
                try:
                    if hasattr(client, "connect"):
                        await client.connect()
                    consecutive_fails = 0
                    logger.info(
                        f"[TELEGRAM CONNECTION]\n"
                        f"action=RECONNECTED"
                    )
                except Exception as rec_err:
                    logger.warning(f"[TELEGRAM RECONNECT FAILED] {rec_err}")
            else:
                # Test connectivity with a fast timeout
                try:
                    await asyncio.wait_for(client.get_me(), timeout=6.0)
                    consecutive_fails = 0
                except (asyncio.TimeoutError, OSError, Exception) as ping_err:
                    err_s = str(ping_err).lower()
                    if "connection lost" in err_s or isinstance(ping_err, (OSError, asyncio.TimeoutError)):
                        consecutive_fails += 1
                        logger.warning(
                            f"[TELEGRAM CONNECTION]\n"
                            f"status=DISCONNECTED\n"
                            f"reason={ping_err}"
                        )
                        logger.info(
                            f"[TELEGRAM CONNECTION]\n"
                            f"action=RECONNECT\n"
                            f"attempt={consecutive_fails}"
                        )
                        try:
                            if hasattr(client, "reconnect"):
                                await client.reconnect()
                            elif hasattr(client, "connect"):
                                await client.connect()
                            consecutive_fails = 0
                            logger.info(
                                f"[TELEGRAM CONNECTION]\n"
                                f"action=RECONNECTED"
                            )
                        except Exception as r_err:
                            logger.warning(f"[TELEGRAM RECONNECT ATTEMPT FAILED] {r_err}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"[TELEGRAM WATCHDOG ERROR] {e}")


def start_telegram_watchdog(client, check_interval: int = 30):
    """Guarantees a single watchdog instance is started."""
    global _WATCHDOG_TASK
    if _WATCHDOG_TASK is not None and not _WATCHDOG_TASK.done():
        return _WATCHDOG_TASK
    _WATCHDOG_TASK = asyncio.create_task(_telegram_watchdog_loop(client, check_interval))
    return _WATCHDOG_TASK


def parse_srt_timestamp(ts: str) -> float:
    """Parses HH:MM:SS,mmm or HH:MM:SS.mmm into float seconds."""
    ts = ts.strip().replace('.', ',')
    parts = ts.split(':')
    if len(parts) == 3:
        h = int(parts[0])
        m = int(parts[1])
        s_parts = parts[2].split(',')
        s = int(s_parts[0])
        ms = int(s_parts[1]) if len(s_parts) > 1 else 0
        return h * 3600 + m * 60 + s + ms / 1000.0
    return 0.0


def format_srt_timestamp(seconds: float) -> str:
    """Formats float seconds into HH:MM:SS,mmm format."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s_float = seconds % 60
    s = int(s_float)
    ms = int(round((s_float - s) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    if s >= 60:
        m += 1
        s -= 60
    if m >= 60:
        h += 1
        m -= 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"



def adjust_srt_timing(srt_text: str, offset_seconds: float = 0.0, drift_scale: float = 1.0) -> str:
    """
    Adjusts SRT timestamps using linear correction: corrected_time = drift_scale * original_time + offset_seconds.
    Leaves non-timestamp lines unchanged.
    """
    if offset_seconds == 0.0 and drift_scale == 1.0:
        return srt_text

    time_pat = re.compile(r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})')
    lines = srt_text.splitlines()
    new_lines = []
    for line in lines:
        m = time_pat.search(line)
        if m:
            start_ts = parse_srt_timestamp(m.group(1))
            end_ts = parse_srt_timestamp(m.group(2))
            new_start = drift_scale * start_ts + offset_seconds
            new_end = drift_scale * end_ts + offset_seconds
            new_lines.append(f"{format_srt_timestamp(new_start)} --> {format_srt_timestamp(new_end)}")
        else:
            new_lines.append(line)
    return "\n".join(new_lines)


def extract_poster_file_id(message, workflow: str = "UNKNOWN", state: str = "UNKNOWN") -> str | None:
    """
    Safely extracts a poster file_id, image document, or image URL from an incoming message.
    Returns:
      - str file_id or URL for valid image input
      - "" (empty string) for Skip command/text
      - None for invalid input
    """
    uid = message.from_user.id if message.from_user else 0
    has_photo = bool(message.photo)
    has_doc = bool(message.document)
    doc_mime = getattr(message.document, "mime_type", "") or "" if has_doc else ""
    doc_name = getattr(message.document, "file_name", "") or "" if has_doc else ""
    text_content = (message.text or message.caption or "").strip()

    photo_type = type(message.photo).__name__ if has_photo else "None"
    logger.info(
        f"[MANUAL POSTER INPUT]\n"
        f"user_id={uid}\n"
        f"workflow={workflow}\n"
        f"state={state}\n"
        f"message_id={message.id}\n"
        f"chat_id={message.chat.id if message.chat else 0}\n"
        f"has_photo={has_photo}\n"
        f"photo_type={photo_type}\n"
        f"has_document={has_doc}\n"
        f"document_mime={doc_mime}\n"
        f"document_file_name={doc_name}\n"
        f"text={text_content[:50]}"
    )

    # 1. Telegram Photo
    if message.photo:
        try:
            if isinstance(message.photo, (list, tuple)) and len(message.photo) > 0:
                return message.photo[-1].file_id
            return getattr(message.photo, "file_id", None) or message.photo[-1].file_id
        except Exception as e:
            logger.warning(f"[POSTER ERROR] stage=EXTRACT_PHOTO err={e}")
            return getattr(message.photo, "file_id", None)

    # 2. Telegram Image Document
    if message.document:
        mime = doc_mime.lower()
        fname = doc_name.lower()
        if mime in ("image/jpeg", "image/png", "image/webp", "image/jpg") or fname.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return message.document.file_id
        else:
            logger.info(f"[POSTER REJECTED] Document not an image: mime={mime}, file_name={fname}")
            return None

    # 3. Skip command / text
    if text_content.lower() in ("skip", "/skip", "⏭ skip"):
        return ""

    # 4. URL or File-ID string
    if (
        text_content.startswith("http://")
        or text_content.startswith("https://")
        or text_content.startswith("AgAC")
        or text_content.startswith("BAAC")
    ):
        return text_content

    return None



