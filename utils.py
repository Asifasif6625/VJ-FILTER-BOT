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
from bs4 import BeautifulSoup
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
    text = f"{filename or ''} {caption or ''}"
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


def match_movie_identity(file_doc: dict, requested_title: str, requested_year: str | int = None, imdb_id: str = None, tmdb_id: str = None, known_conflicts: set = None) -> tuple[bool, str]:
    """
    Strict identity matcher for Auto Movie Add / Super Movie Filter synchronization.
    Enforces BOTH Title and Release Year matching to prevent cross-contamination across sequels/different years.
    Returns: (is_match: bool, reason: str)
    """
    file_name = file_doc.get("file_name", "") or ""
    caption = file_doc.get("caption", "") or ""
    combined_text = f"{file_name} {caption}"

    # 1. Exact IMDb ID match if present
    if imdb_id and str(imdb_id).startswith("tt"):
        file_imdb = re.search(r"\b(tt\d{7,10})\b", combined_text, re.I)
        if file_imdb:
            if file_imdb.group(1).lower() == imdb_id.lower():
                return True, "IMDB_ID_MATCH"
            else:
                return False, "IMDB_ID_MISMATCH"

    # 2. Reject series files
    token_text = " " + re.sub(r"[\._\-\+\[\]\(\)\{\}]", " ", file_name) + " "
    if re.search(r"(?i)\b(?:s\d{1,2}[\s\.\-_]?e\d{1,4}|\d{1,2}x\d{1,4}|(?:season|series)\s*\d{1,2}|ep(?:isode)?\s*\d{1,4})\b", token_text):
        return False, "IS_SERIES"

    # 3. Extract Titles and Years
    file_year = extract_release_year(file_name, caption)
    req_year_str = str(requested_year).strip() if (requested_year and str(requested_year).strip() not in ["N/A", "None", "0", ""]) else None

    # Strict Year validation check
    if req_year_str and file_year:
        if file_year != req_year_str:
            return False, "YEAR_MISMATCH"

    norm_req_title = normalize_title_for_matching(requested_title)
    r_tokens = norm_req_title.split()
    if not r_tokens:
        return False, "EMPTY_TITLE"

    # Strategy A: Check title extracted before release year in filename
    # E.g. for "I.Nobody.2026.1080p.mkv", before "2026" is "I.Nobody"
    title_match = False
    if file_year and file_year in file_name:
        idx = file_name.find(file_year)
        before_year = file_name[:idx]
        norm_before_year = normalize_title_for_matching(before_year)
        if norm_before_year.split() == r_tokens:
            title_match = True

    # Strategy B: Full normalized filename comparison
    if not title_match:
        norm_file_title = normalize_title_for_matching(file_name)
        f_tokens = norm_file_title.split()
        if f_tokens == r_tokens:
            title_match = True
        elif len(f_tokens) >= len(r_tokens) and f_tokens[:len(r_tokens)] == r_tokens:
            trailing = f_tokens[len(r_tokens):]
            sequel_indicators = {"2", "3", "4", "5", "6", "7", "8", "9", "ii", "iii", "iv", "v", "vi", "part", "chapter", "reloaded", "returns"}
            if not any(t in sequel_indicators for t in trailing):
                title_match = True

    # Strategy C: Check caption if filename alone was ambiguous/incomplete
    if not title_match and caption:
        norm_cap = normalize_title_for_matching(caption)
        cap_tokens = norm_cap.split()
        if cap_tokens == r_tokens:
            title_match = True
        elif len(cap_tokens) >= len(r_tokens) and cap_tokens[:len(r_tokens)] == r_tokens:
            trailing = cap_tokens[len(r_tokens):]
            sequel_indicators = {"2", "3", "4", "5", "6", "7", "8", "9", "ii", "iii", "iv", "v", "vi", "part", "chapter"}
            if not any(t in sequel_indicators for t in trailing):
                title_match = True

    if not title_match:
        return False, "TITLE_MISMATCH"

    # Year Comparison completion
    if req_year_str and file_year:
        if file_year == req_year_str:
            return True, "TITLE_AND_YEAR_MATCH"
        else:
            return False, "YEAR_MISMATCH"

    if req_year_str and not file_year:
        if known_conflicts and len(known_conflicts) > 1:
            return False, "YEAR_NOT_FOUND_IN_FILENAME"
        return True, "TITLE_MATCH_UNAMBIGUOUS"

    return True, "TITLE_MATCH"


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

    auth_ch = int(AUTH_CHANNEL)
    try:
        user = await join_db().get_user(user_id)
        if user and int(user.get("user_id", 0)) == int(user_id):
            return True
    except Exception as e:
        logger.warning(f"[IS_SUBSCRIBED] join_db lookup error: {e}")

    try:
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"_fetch_url_sync error for {url}: {e}")
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
        if not html_text:
            return None

        cards = re.findall(r'<div[^>]+class="[^"]*(?:comp:media-card|card v4)[^"]*"[^>]*>(.*?)(?=<div[^>]+class="[^"]*(?:comp:media-card|card v4)[^"]*"|<div class="pagination"|<footer>|$)', html_text, re.DOTALL)
        if not cards:
            return None

        candidates = []
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
                    'rel_url': rel_url
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
            'plot': best.get('overview') or "",
            'rating': rating or "7.5",
            'url': f"https://www.themoviedb.org{best.get('rel_url')}" if best.get('rel_url') else "https://www.themoviedb.org"
        }
    except Exception as e:
        logger.warning(f"Public TMDB scraper error for '{query}': {e}")
        return None

async def get_tmdb_by_url(url_or_path):
    """
    Directly resolves a TMDB URL (e.g. https://www.themoviedb.org/movie/863530 or https://www.themoviedb.org/tv/1396)
    without any API key and returns structured movie/series metadata.
    """
    import html as _html
    try:
        m = re.search(r'(?:themoviedb\.org)?/(movie|tv)/(\d+)', str(url_or_path), re.I)
        if not m:
            return None
        media_type = m.group(1).lower()  # 'movie' or 'tv'
        tmdb_id = m.group(2)
        
        clean_url = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"
        page = await asyncio.to_thread(_fetch_url_sync, clean_url)
        if not page:
            return None

        # Title
        title_match = re.search(r'<h2[^>]*>\s*(?:<a[^>]*>)?([^<]+)', page) or re.search(r'<meta property="og:title" content="([^"]+)"', page)
        title = _html.unescape(title_match.group(1).strip()) if title_match else None
        if title:
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()

        # Year
        year = None
        date_match = re.search(r'<span class="tag release_date">\s*\(([0-9]{4})\)\s*</span>', page) or re.search(r'<span class="release_date[^"]*">([^<]+)</span>', page)
        if date_match:
            rel_text = date_match.group(1).strip()
            y_m = re.search(r'\b(19\d\d|20\d\d)\b', rel_text)
            if y_m:
                year = y_m.group(1)

        # Rating
        rating = None
        rate_match = re.search(r'data-percent="([0-9.]+)"', page)
        if rate_match:
            try:
                rating = str(round(float(rate_match.group(1)) / 10.0, 1))
            except:
                pass

        # Genres
        genres_match = re.search(r'<span class="genres">([^<]+(?:<a[^>]*>[^<]+</a>[^<]*)+)</span>', page)
        genres = []
        if genres_match:
            genres = [_html.unescape(g.strip()) for g in re.findall(r'<a[^>]*>([^<]+)</a>', genres_match.group(1))]

        # Seasons for TV Series
        seasons = None
        if media_type == "tv":
            season_match = re.search(r'(\d+)\s+Season', page, re.I)
            if season_match:
                seasons = int(season_match.group(1))
            else:
                seasons = 1

        # Poster
        poster_match = re.search(r'<meta property="og:image" content="([^"]+)"', page) or re.search(r'class="poster[^"]*"[^>]+(?:src|data-src)="([^"]+)"', page)
        poster = None
        if poster_match:
            raw_poster = poster_match.group(1)
            poster = re.sub(r'/w\d+(_and_h\d+[^/]*)?/', '/w500/', raw_poster)
            if poster.startswith('//'):
                poster = 'https:' + poster

        # Overview
        overview_match = re.search(r'<div class="overview"[^>]*>\s*<p>([^<]+)</p>', page) or re.search(r'<meta property="og:description" content="([^"]+)"', page)
        overview = _html.unescape(overview_match.group(1).strip()) if overview_match else ""

        kind = "tv series" if media_type == "tv" else "movie"

        return {
            'title': title,
            'votes': None,
            'aka': None,
            'seasons': seasons,
            'box_office': None,
            'localized_title': title,
            'kind': kind,
            'imdb_id': None,
            'tmdb_id': tmdb_id,
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
            'release_date': str(year or "N/A"),
            'year': year,
            'genres': ", ".join(genres) if genres else "Drama",
            'poster': poster,
            'plot': overview,
            'rating': rating or "7.5",
            'url': clean_url
        }
    except Exception as e:
        logger.warning(f"Error fetching TMDB URL '{url_or_path}': {e}")
        return None


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
            "year": year,
            "kind": kind,
            "imdb_id": exact.get("id", imdb_id),
            "poster": poster,
            "rating": "",
            "genres": "",
            "plot": "",
            "seasons": None,
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
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all( 'h3' )
    return [title.getText() for title in titles]

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
                cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
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
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
            else:
                cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title}\n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
                cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
    else:
        cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title} \n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
        cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
        for file in files:
            cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n\n</a></b>"
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


# ─── 10-Minute Centralized Auto Delete Helper ─────────────────────────────────
_FILTER_DELETE_TASKS = {}

async def delete_message_after(client, chat_id: int, message_id: int, delay: int = 600):
    try:
        await asyncio.sleep(delay)
        await client.delete_messages(chat_id, message_id)
        logger.info(f"[AUTO DELETE EXECUTED]\nchat_id={chat_id}\nmessage_id={message_id}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"[AUTO DELETE] chat={chat_id} message={message_id} error={e}")
    finally:
        _FILTER_DELETE_TASKS.pop((int(chat_id), int(message_id)), None)

def schedule_filter_message_delete(client, chat_id: int, message_id: int, delay: int = 600):
    """
    Schedules auto-deletion of a temporary bot filter/result message after `delay` seconds (default 600s = 10 mins).
    If the message is refreshed/edited, cancels any pending task and resets the TTL.
    """
    if not client or not chat_id or not message_id:
        return None

    key = (int(chat_id), int(message_id))
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

