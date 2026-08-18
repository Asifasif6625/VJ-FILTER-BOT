# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import logging
from datetime import datetime
from difflib import SequenceMatcher
from bson import ObjectId
import motor.motor_asyncio
from pymongo.errors import DuplicateKeyError

from info import OTHER_DB_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

# ─── Motor async client ────────────────────────────────────────────────────────
_client = motor.motor_asyncio.AsyncIOMotorClient(OTHER_DB_URI)
_db = _client[DATABASE_NAME]

series_col   = _db["series"]
sfiles_col   = _db["series_files"]
sbatch_col   = _db["series_batches"]
temp_reqs_col = _db["temp_requests"]
settings_col = _db["settings"]
announcements_col = _db["announcements"]


# ─── Helpers ──────────────────────────────────────────────────────────────────
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u200d\ufe0f\ufe0e\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u2934\u2935\u3030\u303d\u3297\u3299]+",
    flags=re.UNICODE
)

def clean_series_title(title: str) -> str:
    """
    Cleans markdown formatting, decorative symbols, and punctuation
    from a Series title while preserving the alphanumeric title words.
    """
    if not title:
        return ""
    # Remove HTML tags if present (e.g. <b>title</b>)
    cleaned = re.sub(r"<[^>]+>", " ", title)
    # Remove markdown formatting characters: *, _, `, ~, |, #
    cleaned = re.sub(r"[\*\_`~|#]", " ", cleaned)
    # Remove punctuation & decorative symbols: !, ?, :, ;, ,, ", ', (, ), [, ], {, }, <, >, /, \, @, $, %, ^, &, +, =, ~
    cleaned = re.sub(r"[!?:;,\"'\(\)\[\]\{\}<>/\\@$%^&+=~]", " ", cleaned)
    # Remove emojis & non-printable symbols
    cleaned = EMOJI_PATTERN.sub(" ", cleaned)
    # Collapse multiple spaces and strip
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize(name: str) -> str:
    """Lowercase, clean title symbols and extra spaces — used for search."""
    cleaned = clean_series_title(name)
    return cleaned.lower()


def make_series_key(title: str) -> str:
    """
    Generate a URL-safe normalized key from series title for /start deep link.
    e.g., "Stranger Things" -> "stranger_things"
    "Money Heist: Korea" -> "money_heist_korea"
    """
    if not title:
        return ""
    cleaned = clean_series_title(title)
    key = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
    return key or "series"


_indexes_ensured = False

async def _ensure_indexes():
    """Create useful indexes once at startup."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    _indexes_ensured = True
    try:
        await series_col.create_index("normalized_name")
        await series_col.create_index("series_key")
        await announcements_col.create_index("series_id", unique=True)
        await sfiles_col.create_index(
            [("series_id", 1), ("language", 1), ("season", 1), ("episode", 1), ("quality", 1)]
        )
        await sbatch_col.create_index(
            [("series_id", 1), ("language", 1), ("season", 1), ("quality", 1)]
        )
        # TTL index for temporary requests (expires after 1 hour)
        await temp_reqs_col.create_index("created_at", expireAfterSeconds=3600)
    except Exception as e:
        logger.warning(f"Series DB index creation: {e}")


# ─── Series CRUD ──────────────────────────────────────────────────────────────

async def create_series(data: dict) -> str:
    """
    Insert a new series document with a cleaned canonical title.
    data keys: name, year, genre, description, poster,
                languages, seasons, qualities, created_by
    Returns the new _id string.
    """
    clean_name = clean_series_title(data.get("name", ""))
    doc = {
        "name": clean_name,
        "normalized_name": _normalize(clean_name),
        "series_key": make_series_key(clean_name),
        "year": data.get("year", "N/A"),
        "genre": data.get("genre", "N/A"),
        "rating": data.get("rating", ""),
        "description": data.get("description", ""),
        "poster": data.get("poster", ""),
        "languages": data.get("languages", []),
        "seasons": data.get("seasons", []),
        "qualities": data.get("qualities", []),
        "season_modes": data.get("season_modes", {}),
        "created_by": data.get("created_by"),
        "announcement_sent": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "active",
    }
    result = await series_col.insert_one(doc)
    return str(result.inserted_id)


async def get_series(series_id: str) -> dict | None:
    """Fetch a series by its string _id."""
    try:
        return await series_col.find_one({"_id": ObjectId(series_id)})
    except Exception:
        return None


async def get_series_by_name(normalized_name: str) -> dict | None:
    """Exact-match on normalized_name."""
    return await series_col.find_one({"normalized_name": normalized_name, "status": "active"})


async def get_series_by_key(series_key: str) -> dict | None:
    """
    Fetch a series by its URL-safe series_key, normalized_name, or string _id.
    """
    if not series_key:
        return None
    key = str(series_key).strip().lower()
    # 1. Direct series_key match
    doc = await series_col.find_one({"series_key": key, "status": "active"})
    if doc:
        return doc
    # 2. Check normalized name with spaces
    norm_name = key.replace("_", " ")
    doc = await series_col.find_one({"normalized_name": norm_name, "status": "active"})
    if doc:
        return doc
    # 3. Check ObjectId match if valid hex string
    if len(key) == 24:
        try:
            doc = await series_col.find_one({"_id": ObjectId(key), "status": "active"})
            if doc:
                return doc
        except Exception:
            pass
    # 4. Fallback search by fuzzy / regex
    matches = await search_series(norm_name)
    if matches:
        return matches[0]
    return None


def _token_similarity(q_token: str, t_token: str) -> float:
    """Calculates similarity between a query token and a title token."""
    if q_token == t_token:
        return 1.0
    
    # Prefix matching
    if t_token.startswith(q_token) and len(q_token) >= 3:
        prefix_ratio = len(q_token) / len(t_token)
        return max(0.80 + (0.20 * prefix_ratio), SequenceMatcher(None, q_token, t_token).ratio())
        
    if q_token.startswith(t_token) and len(t_token) >= 3:
        prefix_ratio = len(t_token) / len(q_token)
        return max(0.75 + (0.25 * prefix_ratio), SequenceMatcher(None, q_token, t_token).ratio())

    # Fuzzy edit similarity
    return SequenceMatcher(None, q_token, t_token).ratio()


def _score_series_candidate(q_norm: str, q_tokens: list[str], title_norm: str) -> tuple[bool, float]:
    """
    Evaluates whether title_norm matches q_tokens and calculates a relevance score (0.0 to 1.0).
    Returns (is_match, score).
    """
    if not title_norm:
        return False, 0.0
        
    # Exact full match
    if q_norm == title_norm:
        return True, 1.0
        
    title_tokens = [t for t in title_norm.split(" ") if t]
    if not title_tokens:
        return False, 0.0
        
    num_q = len(q_tokens)
    num_t = len(title_tokens)
    
    # ── Single Word Query ──
    if num_q == 1:
        q_tok = q_tokens[0]
        # Exact title starts with query (e.g. 'dark' matching 'Dark' and 'Dark Matter')
        if title_norm.startswith(q_tok):
            score = 0.85 + (0.15 * (len(q_tok) / len(title_norm)))
            return True, score
            
        best_token_sim = 0.0
        for t_tok in title_tokens:
            sim = _token_similarity(q_tok, t_tok)
            if sim > best_token_sim:
                best_token_sim = sim
                
        # Single word must have strong match with at least one title word
        if best_token_sim >= 0.70:
            score = best_token_sim * (0.80 + 0.20 * (1.0 / num_t))
            return True, score
            
        full_sim = SequenceMatcher(None, q_norm, title_norm).ratio()
        if full_sim >= 0.75:
            return True, full_sim
            
        return False, 0.0

    # ── Multi-Word Query ──
    token_scores = []
    matched_title_indices = set()
    
    for q_tok in q_tokens:
        best_sim = 0.0
        best_idx = -1
        for idx, t_tok in enumerate(title_tokens):
            sim = _token_similarity(q_tok, t_tok)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
                
        token_scores.append(best_sim)
        if best_sim >= 0.65 and best_idx != -1:
            matched_title_indices.add(best_idx)
            
    # For multi-word queries, all query tokens must match (or at least N-1 if query >= 4 words)
    min_required_matches = num_q if num_q <= 3 else (num_q - 1)
    matched_count = sum(1 for s in token_scores if s >= 0.65)
    
    if matched_count < min_required_matches:
        full_sim = SequenceMatcher(None, q_norm, title_norm).ratio()
        if full_sim >= 0.80:
            return True, full_sim
        return False, 0.0
        
    avg_token_score = sum(token_scores) / num_q
    
    # Check if words matched in the same relative order
    ordered_matches = sorted(list(matched_title_indices))
    order_bonus = 0.05 if list(matched_title_indices) == ordered_matches else 0.0
    
    title_coverage = min(1.0, len(matched_title_indices) / num_t)
    
    score = (avg_token_score * 0.70) + (title_coverage * 0.25) + order_bonus
    score = min(0.99, score)
    
    return True, score


async def search_series(query: str) -> list[dict]:
    """Multi-word & partial-word fuzzy search across series names, scored and deduplicated."""
    q = query.strip()
    if not q:
        return []
    
    q_norm = _normalize(q)
    if not q_norm:
        return []
        
    q_tokens = [w for w in q_norm.split(" ") if w]
    if not q_tokens:
        return []

    # 1. Retrieve candidates from MongoDB efficiently using regex
    token_patterns = []
    for tok in q_tokens:
        if len(tok) <= 2:
            token_patterns.append(re.escape(tok))
        elif len(tok) <= 4:
            token_patterns.append(re.escape(tok[:3]))
        else:
            token_patterns.append(re.escape(tok[:max(3, len(tok)-2)]))
            
    combined_pattern = "|".join(token_patterns)
    try:
        mongo_regex = re.compile(combined_pattern, re.IGNORECASE)
    except Exception:
        mongo_regex = re.compile(re.escape(q_norm), re.IGNORECASE)

    cursor = series_col.find(
        {"normalized_name": mongo_regex, "status": "active"}
    ).limit(60)

    candidates = [doc async for doc in cursor]
    
    # Fallback to active series scan if regex yielded no candidates
    if not candidates:
        cursor = series_col.find({"status": "active"}).limit(60)
        candidates = [doc async for doc in cursor]

    if not candidates:
        return []

    # 2. Score candidates using fuzzy & multi-word matching
    scored_results = []
    for doc in candidates:
        title_norm = doc.get("normalized_name", "")
        is_match, score = _score_series_candidate(q_norm, q_tokens, title_norm)
        if is_match and score > 0.0:
            scored_results.append((score, doc))

    if not scored_results:
        return []

    # 3. Sort by score descending, then length difference, then name
    scored_results.sort(key=lambda x: (-x[0], abs(len(x[1].get("normalized_name", "")) - len(q_norm)), x[1].get("name", "")))

    # 4. Deduplicate by unique series title
    seen = set()
    dedup = []
    for score, doc in scored_results:
        name_lower = doc.get("name", "").strip().lower()
        if name_lower not in seen:
            seen.add(name_lower)
            dedup.append(doc)
            if len(dedup) == 10:
                break
                
    return dedup

# ─── Settings / Global Thumbnail ─────────────────────────────────────────────

async def save_series_thumbnail(file_id: str):
    await settings_col.update_one(
        {"_id": "global_thumbnail"},
        {"$set": {"file_id": file_id}},
        upsert=True
    )

async def get_series_thumbnail() -> str | None:
    doc = await settings_col.find_one({"_id": "global_thumbnail"})
    return doc.get("file_id") if doc else None

async def delete_series_thumbnail():
    await settings_col.delete_one({"_id": "global_thumbnail"})


async def update_series(series_id: str, data: dict):
    """Partial update on a series document."""
    if "name" in data and data["name"]:
        clean_name = clean_series_title(data["name"])
        data["name"] = clean_name
        data["normalized_name"] = _normalize(clean_name)
        data["series_key"] = make_series_key(clean_name)
    data["updated_at"] = datetime.utcnow()
    await series_col.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": data}
    )


# ─── Announcement Channel & Tracking ──────────────────────────────────────────

async def set_announcement_channel(channel_id: int | str):
    """Save or update the configured announcement channel ID."""
    cid = int(channel_id) if str(channel_id).lstrip("-").isdigit() else str(channel_id)
    await settings_col.update_one(
        {"_id": "announcement_channel"},
        {"$set": {"channel_id": cid}},
        upsert=True
    )

async def get_announcement_channel() -> int | str | None:
    """Retrieve the configured announcement channel ID."""
    doc = await settings_col.find_one({"_id": "announcement_channel"})
    return doc.get("channel_id") if doc else None

async def delete_announcement_channel():
    """Delete the configured announcement channel setting."""
    await settings_col.delete_one({"_id": "announcement_channel"})

async def is_announcement_sent(series_id: str) -> bool:
    """Check if an announcement has already been sent for a series."""
    sid = str(series_id).strip()
    existing = await announcements_col.find_one({"series_id": sid})
    if existing:
        return True
    # Also check series document flag
    try:
        sdoc = await series_col.find_one({"_id": ObjectId(sid)})
        if sdoc and sdoc.get("announcement_sent"):
            return True
    except Exception:
        pass
    return False

async def get_announcement(series_id: str) -> dict | None:
    """Fetch the persistent announcement record for a series."""
    sid = str(series_id).strip()
    return await announcements_col.find_one({"series_id": sid})

async def save_announcement(series_id: str, channel_id: int | str, message_id: int, series_key: str = "") -> str:
    """Save an announcement tracking record."""
    sid = str(series_id).strip()
    doc = {
        "series_id": sid,
        "channel_id": channel_id,
        "message_id": message_id,
        "series_key": series_key,
        "sent_at": datetime.utcnow()
    }
    await announcements_col.update_one(
        {"series_id": sid},
        {"$set": doc},
        upsert=True
    )
    try:
        await series_col.update_one(
            {"_id": ObjectId(sid)},
            {"$set": {"announcement_sent": True, "announcement_message_id": message_id}}
        )
    except Exception:
        pass
    return sid

async def delete_announcement(series_id: str) -> dict | None:
    """
    Delete an announcement record for a series and clear its tracking flag.
    Returns the deleted announcement record if it existed.
    """
    sid = str(series_id).strip()
    doc = await announcements_col.find_one({"series_id": sid})
    if doc:
        await announcements_col.delete_one({"series_id": sid})
    try:
        await series_col.update_one(
            {"_id": ObjectId(sid)},
            {"$unset": {"announcement_sent": "", "announcement_message_id": ""}}
        )
    except Exception:
        pass
    return doc


async def set_sbatch_msgid(doc_id: str, message_id: int):
    """Set the forwarded batch message_id on an existing sbatch doc."""
    await sbatch_col.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"message_id": message_id}}
    )


# ─── Temp Requests (Group -> PM Flow) ─────────────────────────────────────────

async def save_temp_request(req_id: str, data: dict):
    """Save a temporary request (e.g. for series quality navigation)."""
    data["_id"] = req_id
    data["created_at"] = datetime.utcnow()
    try:
        await temp_reqs_col.insert_one(data)
    except DuplicateKeyError:
        pass
        
async def get_temp_request(req_id: str) -> dict:
    """Retrieve and delete a temporary request."""
    doc = await temp_reqs_col.find_one({"_id": req_id})
    return doc


async def delete_series(series_id: str):
    """Soft-delete: set status='deleted'."""
    await series_col.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": {"status": "deleted", "updated_at": datetime.utcnow()}}
    )


async def list_all_series() -> list[dict]:
    """Return all active series (for admin listing)."""
    cursor = series_col.find({"status": "active"}).sort("name", 1)
    return [doc async for doc in cursor]


# ─── Series Files ─────────────────────────────────────────────────────────────

async def add_series_file(data: dict) -> tuple[bool, str]:
    """
    Add one episode file.
    data keys: series_id, language, season (int), episode (int),
               quality, chat_id, message_id, file_id, file_name, file_size
    Returns (True, 'inserted') or (False, 'duplicate').
    """
    ep = int(data["episode"]) if data.get("episode") is not None else -1
    query = {
        "series_id": str(data["series_id"]),
        "language":  data["language"],
        "season":    int(data["season"]),
        "episode":   ep,
        "quality":   data["quality"],
    }
    if ep == -1 and data.get("message_id"):
        query["message_id"] = data["message_id"]

    existing = await sfiles_col.find_one(query)
    if existing:
        return False, "duplicate"

    doc = {
        "series_id":  str(data["series_id"]),
        "language":   data["language"],
        "season":     int(data["season"]),
        "episode":    ep,
        "quality":    data["quality"],
        "chat_id":    data.get("chat_id"),
        "message_id": data.get("message_id"),
        "file_id":    data.get("file_id", ""),
        "file_name":  data.get("file_name", ""),
        "file_size":  data.get("file_size", 0),
        "is_batch":   data.get("is_batch", False),
        "total_episodes": data.get("total_episodes", 1),
        "created_at": datetime.utcnow(),
    }
    try:
        await sfiles_col.insert_one(doc)
        return True, "inserted"
    except DuplicateKeyError:
        return False, "duplicate"
    except Exception as e:
        logger.error(f"add_series_file error: {e}")
        return False, "error"


def _sid_query(series_id: str):
    sid = str(series_id).strip()
    candidates = [sid]
    if len(sid) == 24:
        candidates.append(sid[-8:])
    return {"$in": candidates} if len(candidates) > 1 else sid


def _num_query(val):
    try:
        n = int(val)
        return {"$in": [n, str(n)]}
    except Exception:
        return val


async def check_episode_exists(
    series_id: str, language: str, season: int, episode: int, quality: str
) -> bool:
    """Check if a specific episode exists for given series context."""
    doc = await sfiles_col.find_one({
        "series_id": _sid_query(series_id),
        "language":  language,
        "season":    _num_query(season),
        "episode":   _num_query(episode),
        "quality":   quality,
    })
    return doc is not None


async def replace_series_file(data: dict):
    """Replace an existing episode file document."""
    ep = int(data["episode"]) if data.get("episode") is not None else -1
    del_query = {
        "series_id": _sid_query(data["series_id"]),
        "language":  data["language"],
        "season":    _num_query(data["season"]),
        "episode":   _num_query(ep),
        "quality":   data["quality"],
    }
    if ep == -1 and data.get("message_id"):
        del_query["message_id"] = data["message_id"]
    await sfiles_col.delete_many(del_query)
    await add_series_file(data)


async def get_series_files(
    series_id: str,
    language: str,
    season: int,
    episode: int,
    quality: str,
) -> list[dict]:
    """Fetch all files matching (series, lang, season, episode, quality)."""
    cursor = sfiles_col.find({
        "series_id": _sid_query(series_id),
        "language":  language,
        "season":    _num_query(season),
        "episode":   _num_query(episode),
        "quality":   quality,
    })
    return [doc async for doc in cursor]


async def find_saved_series_file(
    series_id: str,
    language: str,
    season: int,
    quality: str,
    file_id: str,
    episode: int | None = None
) -> dict | None:
    """Find an existing saved series file record in sfiles_col matching context and file_id."""
    query = {
        "series_id": _sid_query(series_id),
        "language":  language,
        "season":    _num_query(season),
        "quality":   quality,
        "file_id":   str(file_id),
        "is_batch":  {"$ne": True}
    }
    if episode is not None and (isinstance(episode, int) or (isinstance(episode, str) and str(episode).isdigit())) and int(episode) > 0:
        doc = await sfiles_col.find_one({**query, "episode": int(episode)})
        if doc:
            return doc
    return await sfiles_col.find_one(query)


async def list_series_languages(series_id: str) -> list[str]:
    """Distinct languages with at least one file saved."""
    vals = await sfiles_col.distinct("language", {"series_id": _sid_query(series_id)})
    return [v for v in vals if v]


async def list_series_seasons(series_id: str, language: str) -> list[int]:
    """Distinct season numbers for (series, language)."""
    vals = await sfiles_col.distinct(
        "season", {"series_id": _sid_query(series_id), "language": language}
    )
    result = []
    for v in vals:
        try:
            result.append(int(v))
        except (ValueError, TypeError):
            pass
    return sorted(list(set(result)))


async def list_season_qualities(series_id: str, language: str, season: int) -> list[str]:
    """Distinct qualities for (series, language, season)."""
    vals = await sfiles_col.distinct(
        "quality",
        {
            "series_id": _sid_query(series_id),
            "language":  language,
            "season":    _num_query(season),
        }
    )
    return [v for v in vals if v]


async def list_quality_episodes(
    series_id: str, language: str, season: int, quality: str
) -> list[int]:
    """Distinct episodes for (series, language, season, quality) sorted strictly numerically."""
    vals = await sfiles_col.distinct(
        "episode",
        {
            "series_id": _sid_query(series_id),
            "language":  language,
            "season":    int(season),
            "quality":   quality,
        }
    )
    pos_vals = sorted(list(set(
        int(v) for v in vals 
        if (isinstance(v, int) or (isinstance(v, str) and v.isdigit())) and int(v) > 0
    )))
    neg_vals = sorted(list(set(
        int(v) for v in vals 
        if (isinstance(v, int) or (isinstance(v, str) and v.lstrip("-").isdigit())) and int(v) <= 0
    )))
    return pos_vals + neg_vals


# ─── Batch Records ────────────────────────────────────────────────────────────

async def save_batch(data: dict) -> str:
    """
    Save a batch record.
    data keys: series_id, language, season, quality,
               chat_id, first_message_id, last_message_id, total_files
    Returns inserted _id string.
    """
    doc = {
        "series_id":       data["series_id"],
        "language":        data["language"],
        "season":          int(data["season"]),
        "quality":         data["quality"],
        "chat_id":         data.get("chat_id"),
        "first_message_id": data.get("first_message_id"),
        "last_message_id":  data.get("last_message_id"),
        "total_files":     data.get("total_files", 0),
        "created_at":      datetime.utcnow(),
    }
    result = await sbatch_col.insert_one(doc)
    return str(result.inserted_id)


async def get_batches(series_id: str, language: str, season: int, quality: str) -> list[dict]:
    cursor = sbatch_col.find({
        "series_id": series_id,
        "language":  language,
        "season":    int(season),
        "quality":   quality,
    })
    return [doc async for doc in cursor]
