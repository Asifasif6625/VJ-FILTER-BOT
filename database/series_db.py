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
super_movies_col = _db["super_movies"]


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
        {"normalized_name": mongo_regex, "status": {"$ne": "deleted"}}
    ).limit(60)

    candidates = [doc async for doc in cursor]
    
    # Fallback to active series scan if regex yielded no candidates
    if not candidates:
        cursor = series_col.find({"status": {"$ne": "deleted"}}).limit(60)
        candidates = [doc async for doc in cursor]

    if not candidates:
        logger.info(
            f"[SERIES SEARCH ROUTING]\n"
            f"query={query}\n"
            f"matched=False"
        )
        return []

    # 2. Score candidates using fuzzy & multi-word matching
    scored_results = []
    for doc in candidates:
        title_norm = doc.get("normalized_name", "")
        is_match, score = _score_series_candidate(q_norm, q_tokens, title_norm)
        if is_match and score > 0.0:
            scored_results.append((score, doc))

    if not scored_results:
        logger.info(
            f"[SERIES SEARCH ROUTING]\n"
            f"query={query}\n"
            f"matched=False"
        )
        return []

    # 3. Sort by score descending, then length difference, then name
    scored_results.sort(key=lambda x: (-x[0], abs(len(x[1].get("normalized_name", "")) - len(q_norm)), x[1].get("name", "")))

    # 4. Deduplicate by (title + year) — NOT just title alone.
    #    Series with the same name but different years must remain separate.
    seen = set()
    dedup = []
    for score, doc in scored_results:
        name_lower = doc.get("name", "").strip().lower()
        year       = str(doc.get("year", "")).strip()
        imdb_id    = str(doc.get("imdb_id", "")).strip()
        # Primary key: imdb_id when present; otherwise (name, year)
        if imdb_id:
            dedup_key = imdb_id
        else:
            dedup_key = f"{name_lower}||{year}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            dedup.append(doc)
            if len(dedup) == 10:
                break

    logger.info(
        f"[SERIES SEARCH ROUTING]\n"
        f"query={query}\n"
        f"matched={bool(dedup)}"
    )
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
    cid = doc.get("channel_id") if doc else None
    if not cid:
        try:
            from info import ANNOUNCEMENT_CHANNEL
            cid = ANNOUNCEMENT_CHANNEL
        except Exception:
            from os import environ
            cid = environ.get("ANNOUNCEMENT_CHANNEL") or environ.get("ANO_CHANNEL")
    return cid

async def delete_announcement_channel():
    """Delete the configured announcement channel setting."""
    await settings_col.delete_one({"_id": "announcement_channel"})

async def is_announcement_sent(announcement_key: str, filter_type: str = None, filter_id: str = None) -> bool:
    """Check if an announcement has already been sent for a series or movie."""
    key = str(announcement_key).strip()
    f_id = str(filter_id).strip() if filter_id else ""
    f_type = str(filter_type).strip().lower() if filter_type else ""

    if not f_type:
        if key.startswith("series:"):
            f_type = "series"
            f_id = key.split(":", 1)[1]
        elif key.startswith("movie:"):
            f_type = "movie"
            f_id = key.split(":", 1)[1]
        else:
            f_id = key

    # 1. Check announcements collection by announcement_key or legacy series_id
    query_conditions = [
        {"announcement_key": key, "sent": True},
        {"announcement_key": key}
    ]
    if f_id:
        query_conditions.extend([
            {"series_id": f_id, "sent": True},
            {"series_id": f_id},
            {"filter_id": f_id, "sent": True},
            {"filter_id": f_id}
        ])
    existing = await announcements_col.find_one({"$or": query_conditions})
    if existing:
        return True

    # 2. Check series_col or super_movies_col document flag
    if f_type in ("series", "") and f_id:
        try:
            sdoc = await series_col.find_one({"_id": ObjectId(f_id)})
            if sdoc and sdoc.get("announcement_sent"):
                return True
        except Exception:
            pass

    if f_type in ("movie", "") and f_id:
        try:
            mdoc = await super_movies_col.find_one({"_id": ObjectId(f_id)})
            if mdoc and mdoc.get("announcement_sent"):
                return True
        except Exception:
            pass

    return False

async def get_announcement(identifier: str, filter_type: str = None) -> dict | None:
    """Fetch the persistent announcement record for a series or movie."""
    raw = str(identifier).strip()
    return await announcements_col.find_one({
        "$or": [
            {"announcement_key": raw},
            {"series_id": raw},
            {"filter_id": raw}
        ]
    })

async def save_announcement(filter_id: str, channel_id: int | str, message_id: int, filter_type: str = "series", series_key: str = "") -> str:
    """Save an announcement tracking record."""
    fid = str(filter_id).strip()
    ftype = str(filter_type).strip().lower() if filter_type else ("movie" if fid.startswith("movie:") else "series")

    if fid.startswith(f"{ftype}:"):
        actual_id = fid.split(":", 1)[1]
        announcement_key = fid
    else:
        actual_id = fid
        announcement_key = f"{ftype}:{actual_id}"

    doc = {
        "announcement_key": announcement_key,
        "filter_type": ftype,
        "filter_id": actual_id,
        "series_id": actual_id,  # backward compatibility
        "channel_id": channel_id,
        "message_id": message_id,
        "series_key": series_key,
        "sent": True,
        "sent_at": datetime.utcnow()
    }
    await announcements_col.update_one(
        {"$or": [{"announcement_key": announcement_key}, {"series_id": actual_id}]},
        {"$set": doc},
        upsert=True
    )
    if ftype == "series":
        try:
            await series_col.update_one(
                {"_id": ObjectId(actual_id)},
                {"$set": {"announcement_sent": True, "announcement_message_id": message_id}}
            )
        except Exception:
            pass
    elif ftype == "movie":
        try:
            await super_movies_col.update_one(
                {"_id": ObjectId(actual_id)},
                {"$set": {"announcement_sent": True, "announcement_message_id": message_id}}
            )
        except Exception:
            pass
    return actual_id

async def delete_announcement(identifier: str, filter_type: str = None) -> dict | None:
    """
    Delete an announcement record for a series and clear its tracking flag.
    Returns the deleted announcement record if it existed.
    """
    raw = str(identifier).strip()
    doc = await announcements_col.find_one({
        "$or": [
            {"announcement_key": raw},
            {"series_id": raw},
            {"filter_id": raw}
        ]
    })
    if doc:
        await announcements_col.delete_many({
            "$or": [
                {"announcement_key": doc.get("announcement_key") or raw},
                {"series_id": doc.get("series_id") or raw},
                {"filter_id": doc.get("filter_id") or raw}
            ]
        })
        actual_id = doc.get("filter_id") or doc.get("series_id") or raw
        ftype = doc.get("filter_type") or ("movie" if "movie:" in raw else "series")
        if ftype == "series":
            try:
                await series_col.update_one(
                    {"_id": ObjectId(actual_id)},
                    {"$unset": {"announcement_sent": "", "announcement_message_id": ""}}
                )
            except Exception:
                pass
        elif ftype == "movie":
            try:
                await super_movies_col.update_one(
                    {"_id": ObjectId(actual_id)},
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


async def delete_series_filter(series_id: str):
    """
    Canonical helper: Soft-delete/disable ONLY the series filter metadata/index.
    Preserves series_files (sfiles_col) intact.
    """
    return await delete_series(series_id)



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


# ─── Super Movie CRUD ────────────────────────────────────────────────────────
async def create_super_movie(data: dict) -> str:
    clean_name = clean_series_title(data.get("title", ""))
    file_ids = [str(fid) for fid in data.get("file_ids", []) if fid]
    # Deduplicate file_ids preserving order
    unique_file_ids = list(dict.fromkeys(file_ids))
    
    doc = {
        "title": clean_name,
        "normalized_name": _normalize(clean_name),
        "year": str(data.get("year", "N/A")),
        "genre": data.get("genre", "N/A"),
        "rating": str(data.get("rating", "")),
        "poster": data.get("poster", ""),
        "imdb_id": data.get("imdb_id", ""),
        "languages": data.get("languages", []),
        "qualities": data.get("qualities", []),
        "file_ids": unique_file_ids,
        "created_by": data.get("created_by"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "active",
    }
    existing = None
    if doc.get("imdb_id"):
        existing = await super_movies_col.find_one({"imdb_id": doc["imdb_id"], "status": {"$ne": "deleted"}})
    if not existing:
        existing = await super_movies_col.find_one({"normalized_name": doc["normalized_name"], "year": doc["year"], "status": {"$ne": "deleted"}})
    if not existing and doc["year"] == "N/A":
        existing = await super_movies_col.find_one({"normalized_name": doc["normalized_name"], "status": {"$ne": "deleted"}})
    if existing:
        merged_file_ids = list(dict.fromkeys((existing.get("file_ids") or []) + unique_file_ids))
        merged_langs = list(dict.fromkeys((existing.get("languages") or []) + (doc.get("languages") or [])))
        merged_quals = list(dict.fromkeys((existing.get("qualities") or []) + (doc.get("qualities") or [])))
        update_fields = {
            "title": doc["title"] or existing.get("title"),
            "year": doc["year"] if doc["year"] != "N/A" else existing.get("year", "N/A"),
            "genre": doc["genre"] if doc["genre"] != "N/A" else existing.get("genre", "N/A"),
            "rating": doc["rating"] or existing.get("rating", ""),
            "poster": doc["poster"] or existing.get("poster", ""),
            "imdb_id": doc["imdb_id"] or existing.get("imdb_id", ""),
            "languages": merged_langs,
            "qualities": merged_quals,
            "file_ids": merged_file_ids,
            "updated_at": datetime.utcnow(),
            "status": "active",
        }
        await super_movies_col.update_one({"_id": existing["_id"]}, {"$set": update_fields})
        return str(existing["_id"])
    result = await super_movies_col.insert_one(doc)
    return str(result.inserted_id)


async def get_super_movie(movie_id: str) -> dict | None:
    try:
        return await super_movies_col.find_one({"_id": ObjectId(movie_id)})
    except Exception:
        return None


def normalize_movie_search_title(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[\._\-\+\[\]\(\)\{\}:;!?,/\\]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def search_super_movies(query: str) -> list[dict]:
    raw_query = str(query or "").strip()
    if not raw_query:
        return []

    norm_query = normalize_movie_search_title(raw_query)
    if not norm_query:
        return []

    # Optional year extraction from user query
    q_year_match = re.search(r"\b(19\d{2}|20\d{2})\b", raw_query)
    q_year = q_year_match.group(1) if q_year_match else None

    q_title_no_year = re.sub(r"\b(19\d{2}|20\d{2})\b", "", norm_query).strip()
    q_title_no_year = re.sub(r"\s+", " ", q_title_no_year).strip()
    target_query = q_title_no_year if q_title_no_year else norm_query
    q_tokens = [w for w in target_query.split() if w]

    # Fetch active candidates from MongoDB
    cursor = super_movies_col.find({"status": {"$ne": "deleted"}})
    candidates = [doc async for doc in cursor]

    scored_matches = []
    for cand in candidates:
        c_title = cand.get("title", "")
        c_norm = cand.get("normalized_name") or normalize_movie_search_title(c_title)
        c_year = str(cand.get("year", "")).strip()
        c_file_count = len(cand.get("file_ids") or [])
        c_tokens = [w for w in c_norm.split() if w]

        if not c_norm:
            continue

        score = 0.0
        # 1. Exact normalized title match
        if norm_query == c_norm or target_query == c_norm:
            score = 100.0
        elif q_tokens and c_tokens and q_tokens == c_tokens:
            score = 95.0
        elif q_tokens and c_tokens and all(qt in c_tokens for qt in q_tokens):
            # All query words are in movie title (e.g. "parakkum pappan" in "Parakkum Pappan")
            score = 80.0 + (len(q_tokens) / len(c_tokens)) * 10.0
        elif q_tokens and c_tokens and all(ct in q_tokens for ct in c_tokens):
            # All movie title words are in user query
            score = 75.0 + (len(c_tokens) / len(q_tokens)) * 10.0
        elif c_norm.startswith(target_query) or target_query.startswith(c_norm):
            score = 70.0
        elif len(q_tokens) >= 2 and sum(1 for qt in q_tokens if qt in c_tokens) >= len(q_tokens) - 1:
            score = 65.0

        if score >= 65.0:
            if q_year:
                if c_year == q_year:
                    score += 20.0
                elif c_year and c_year not in ("N/A", "None", "0", ""):
                    score -= 30.0

            scored_matches.append((score, c_file_count, cand))

    scored_matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
    matched = [cand for score, f_count, cand in scored_matches if score >= 60.0]

    logger.info(
        f"[SUPER MOVIE SEARCH DEBUG]\n"
        f"raw_query={raw_query}\n"
        f"normalized_query={norm_query}\n"
        f"candidate_count={len(candidates)}\n"
        f"matched_count={len(matched)}"
    )

    for m in matched:
        logger.info(
            f"[SUPER MOVIE MATCH]\n"
            f"title={m.get('title')}\n"
            f"year={m.get('year')}\n"
            f"movie_id={str(m.get('_id'))}\n"
            f"file_count={len(m.get('file_ids') or [])}"
        )

    return matched


async def list_all_super_movies() -> list[dict]:
    """List all active Super Movie records."""
    cursor = super_movies_col.find({"status": {"$ne": "deleted"}})
    return [doc async for doc in cursor]


async def delete_super_movie(movie_id: str) -> bool:
    """Soft-delete a Super Movie record."""
    try:
        res = await super_movies_col.update_one(
            {"_id": ObjectId(movie_id)},
            {"$set": {"status": "deleted", "updated_at": datetime.utcnow()}}
        )
        return res.modified_count > 0
    except Exception:
        return False


async def update_super_movie(movie_id: str, fields: dict) -> bool:
    """Update metadata of an existing Super Movie."""
    try:
        data = dict(fields)
        if "title" in data and data["title"]:
            clean_name = clean_series_title(data["title"])
            data["title"] = clean_name
            data["normalized_name"] = _normalize(clean_name)
        data["updated_at"] = datetime.utcnow()
        res = await super_movies_col.update_one(
            {"_id": ObjectId(movie_id)},
            {"$set": data}
        )
        return res.modified_count > 0 or res.matched_count > 0
    except Exception as e:
        logger.error(f"[UPDATE SUPER MOVIE ERROR] movie_id={movie_id}: {e}")
        return False


async def find_matching_super_movie(file_name: str, caption: str = "") -> dict | None:
    """
    Strict identity matcher for incoming movie file against existing Super Movie filters.
    Requires EXACT Title + Release Year match or exact IMDb ID match to prevent cross-contamination.
    """
    if not file_name:
        return None

    from utils import extract_release_year, normalize_title_for_matching, match_movie_identity

    # Reject series files immediately
    token_text = " " + re.sub(r"[\._\-\+\[\]\(\)\{\}]", " ", file_name) + " "
    if re.search(r"(?i)\b(?:s\d{1,2}[\s\.\-_]?e\d{1,4}|\d{1,2}x\d{1,4}|(?:season|series)\s*\d{1,2}|ep(?:isode)?\s*\d{1,4})\b", token_text):
        return None

    # 1. Check IMDb ID in caption or filename (e.g. tt1234567)
    imdb_match = re.search(r"\b(tt\d{7,10})\b", f"{file_name} {caption}", re.I)
    if imdb_match:
        imdb_id = imdb_match.group(1).lower()
        doc = await super_movies_col.find_one({"imdb_id": imdb_id, "status": {"$ne": "deleted"}})
        if doc:
            return doc

    # 2. Extract release year and normalized title
    file_year = extract_release_year(file_name, caption)
    norm_title = normalize_title_for_matching(file_name)

    if not norm_title:
        return None

    cursor = super_movies_col.find({"status": {"$ne": "deleted"}})
    candidates = [doc async for doc in cursor]

    if not candidates:
        return None

    known_years = set()
    for cand in candidates:
        c_yr = str(cand.get("year", "")).strip()
        if c_yr and c_yr not in ["N/A", "None", "0", ""]:
            known_years.add(c_yr)

    for cand in candidates:
        c_title = cand.get("title", "")
        c_year = cand.get("year")
        c_imdb = cand.get("imdb_id")
        c_tmdb = cand.get("tmdb_id")

        matched, reason = match_movie_identity(
            {"file_name": file_name, "caption": caption},
            requested_title=c_title,
            requested_year=c_year,
            imdb_id=c_imdb,
            tmdb_id=c_tmdb,
            known_conflicts=known_years
        )
        if matched:
            return cand
        else:
            if reason == "YEAR_MISMATCH":
                logger.info(f"[AUTO MOVIE FILTER SYNC SKIP]\nreason=YEAR_MISMATCH\nfilter_title={c_title}\nfilter_year={c_year}\nfile_year={file_year}\nfile_name={file_name}")

    return None


async def resync_super_movie_filter(movie_id: str) -> dict | None:
    """
    Repairs and re-synchronizes an existing Super Movie Filter by removing any wrong-year
    or mismatched files, retaining only strictly matching files.
    """
    from database.ia_filterdb import get_file_details
    from plugins.pm_filter import detect_file_languages
    from plugins.series import extract_quality_from_filename
    from utils import match_movie_identity

    movie = await get_super_movie(movie_id)
    if not movie:
        return None

    mid = str(movie["_id"])
    title = movie.get("title", "")
    year = movie.get("year")
    imdb_id = movie.get("imdb_id")
    tmdb_id = movie.get("tmdb_id")
    old_fids = movie.get("file_ids") or []

    valid_fids = []
    removed_fids = []
    new_langs = set()
    new_quals = set()

    for fid in old_fids:
        fdoc = await get_file_details(fid)
        if not fdoc:
            removed_fids.append(fid)
            continue
        
        is_match, reason = match_movie_identity(
            fdoc,
            requested_title=title,
            requested_year=year,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id
        )
        if is_match:
            valid_fids.append(fid)
            fname = fdoc.get("file_name", "")
            caption = fdoc.get("caption", "") or ""
            langs = detect_file_languages(fname, caption)
            for l in langs:
                if l:
                    new_langs.add(l)
            q = extract_quality_from_filename(fname)
            if q and q != "Unknown":
                new_quals.add(q)
        else:
            removed_fids.append(fid)
            logger.info(f"[RESYNC MOVIE REJECT]\nmovie_id={mid}\ntitle={title}\nyear={year}\nfile_name={fdoc.get('file_name')}\nreason={reason}")

    # Update database
    await super_movies_col.update_one(
        {"_id": ObjectId(mid)},
        {
            "$set": {
                "file_ids": valid_fids,
                "languages": list(new_langs) if new_langs else (movie.get("languages") or []),
                "qualities": list(new_quals) if new_quals else (movie.get("qualities") or []),
                "updated_at": datetime.utcnow()
            }
        }
    )

    stats = {
        "movie_id": mid,
        "title": title,
        "year": str(year),
        "total_initial": len(old_fids),
        "valid_retained": len(valid_fids),
        "removed_mismatches": len(removed_fids),
        "languages": list(new_langs),
        "qualities": list(new_quals)
    }
    logger.info(f"[RESYNC MOVIE FINISHED]\nstats={stats}")
    return stats


async def sync_movie_filter_for_files(file_docs, *, trigger="file_add"):
    """
    Central helper to automatically synchronize new movie files into existing Super Movie Filter(s).
    Additive, idempotent, preserves all existing file_ids and metadata.
    """
    if not file_docs:
        return
    if isinstance(file_docs, dict):
        file_docs = [file_docs]

    from plugins.pm_filter import detect_file_languages
    from plugins.series import extract_quality_from_filename

    # Group file_docs by matching Super Movie
    matched_updates = {}

    for fdoc in file_docs:
        try:
            fid = fdoc.get("file_id")
            if not fid:
                continue
            fname = fdoc.get("file_name", "")
            caption = fdoc.get("caption", "") or ""

            langs = detect_file_languages(fname, caption)
            qual = extract_quality_from_filename(fname)

            movie = await find_matching_super_movie(fname, caption)
            if not movie:
                logger.info(f"[AUTO MOVIE FILTER SYNC SKIP]\nreason=no_existing_filter\nfile_name={fname}\ntrigger={trigger}")
                continue

            mid = str(movie["_id"])
            if mid not in matched_updates:
                matched_updates[mid] = {
                    "movie": movie,
                    "new_file_ids": [],
                    "new_langs": set(),
                    "new_quals": set()
                }

            existing_fids = set(movie.get("file_ids") or [])
            if fid not in existing_fids and fid not in matched_updates[mid]["new_file_ids"]:
                matched_updates[mid]["new_file_ids"].append(fid)
            
            for l in langs:
                if l and l not in (movie.get("languages") or []):
                    matched_updates[mid]["new_langs"].add(l)
            if qual and qual != "Unknown" and qual not in (movie.get("qualities") or []):
                matched_updates[mid]["new_quals"].add(qual)
        except Exception as fe:
            logger.error(f"[AUTO MOVIE FILTER SYNC ERROR]\nfile_id={fdoc.get('file_id')}\nerror={fe}", exc_info=True)

    for mid, info in matched_updates.items():
        try:
            movie = info["movie"]
            new_fids = info["new_file_ids"]
            new_langs = list(info["new_langs"])
            new_quals = list(info["new_quals"])
            existing_fids = movie.get("file_ids") or []
            title = movie.get("title", "")
            year = movie.get("year", "N/A")

            if not new_fids and not new_langs and not new_quals:
                logger.info(
                    f"[AUTO MOVIE FILTER SYNC]\n"
                    f"movie_id={mid}\n"
                    f"title={title}\n"
                    f"year={year}\n"
                    f"new_files=0\n"
                    f"reason=already_linked\n"
                    f"trigger={trigger}"
                )
                continue

            update_op = {
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
            if new_fids:
                update_op["$addToSet"] = {"file_ids": {"$each": new_fids}}
            
            merged_langs = list(dict.fromkeys((movie.get("languages") or []) + new_langs))
            merged_quals = list(dict.fromkeys((movie.get("qualities") or []) + new_quals))
            update_op["$set"]["languages"] = merged_langs
            update_op["$set"]["qualities"] = merged_quals

            await super_movies_col.update_one({"_id": ObjectId(mid)}, update_op)

            total_files = len(existing_fids) + len(new_fids)
            logger.info(
                f"[AUTO MOVIE FILTER SYNC]\n"
                f"movie_id={mid}\n"
                f"title={title}\n"
                f"year={year}\n"
                f"new_files={len(new_fids)}\n"
                f"existing_files={len(existing_fids)}\n"
                f"total_files={total_files}\n"
                f"new_languages={', '.join(new_langs) or 'None'}\n"
                f"new_qualities={', '.join(new_quals) or 'None'}\n"
                f"trigger={trigger}"
            )

            verify_doc = await get_super_movie(mid)
            if verify_doc:
                v_fids = verify_doc.get("file_ids") or []
                all_present = all(nf in v_fids for nf in new_fids)
                if all_present:
                    logger.info(
                        f"[AUTO MOVIE FILTER SYNC VERIFY]\n"
                        f"result=SUCCESS\n"
                        f"movie_id={mid}\n"
                        f"files={len(v_fids)}"
                    )
                else:
                    logger.error(
                        f"[AUTO MOVIE FILTER SYNC VERIFY]\n"
                        f"result=FAILED\n"
                        f"movie_id={mid}\n"
                        f"expected={total_files}\n"
                        f"found={len(v_fids)}"
                    )
        except Exception as e:
            logger.error(
                f"[AUTO MOVIE FILTER SYNC ERROR]\n"
                f"movie_id={mid}\n"
                f"title={info.get('movie', {}).get('title', '')}\n"
                f"error={e}",
                exc_info=True
            )


async def sync_series_filter_for_files(file_docs, *, trigger="file_add"):
    """
    Central helper to automatically synchronize incoming series files into matching Series Filter(s).
    Extracts Series Name, Season, Episode, Language, Quality and inserts into sfiles_col and updates series_col.
    """
    if not file_docs:
        return
    if isinstance(file_docs, dict):
        file_docs = [file_docs]

    from plugins.pm_filter import detect_file_languages
    from plugins.series import extract_quality_from_filename, _extract_episode_number, clean_series_title

    for fdoc in file_docs:
        try:
            fid = fdoc.get("file_id")
            if not fid:
                continue
            fname = fdoc.get("file_name", "")
            caption = fdoc.get("caption", "") or ""
            fsize = fdoc.get("file_size", 0)

            clean_name = clean_series_title(fname)
            m_season = re.search(r"\bS(?:eason)?[\s\.\-_]?(\d{1,2})\b", fname, re.IGNORECASE)
            season = int(m_season.group(1)) if m_season else 1
            episode = _extract_episode_number(fname) or 0

            matches = await search_series(clean_name)
            if not matches:
                stripped = re.sub(r"\b(s\d{1,2}|e\d{1,4}|ep\d{1,4}|season\s*\d{1,2}|episode\s*\d{1,4}|2160p|1080p|720p|480p|360p|4k|mkv|mp4|avi)\b", " ", clean_name, flags=re.IGNORECASE)
                stripped = re.sub(r"\s+", " ", stripped).strip()
                if stripped:
                    matches = await search_series(stripped)

            if not matches:
                continue

            series_doc = matches[0]
            series_id = str(series_doc["_id"])

            langs = detect_file_languages(fname, caption)
            qual = extract_quality_from_filename(fname)
            lang = langs[0] if langs else "Multi"

            existing = await sfiles_col.find_one({
                "series_id": _sid_query(series_id),
                "file_id": str(fid)
            })
            if existing:
                continue

            file_record = {
                "series_id": series_id,
                "language": lang,
                "season": season,
                "episode": episode,
                "quality": qual,
                "file_id": str(fid),
                "file_name": fname,
                "file_size": fsize,
                "created_at": datetime.utcnow()
            }
            await sfiles_col.insert_one(file_record)
            logger.info(
                f"[AUTO SERIES FILTER SYNC]\n"
                f"series_id={series_id}\n"
                f"title={series_doc.get('name')}\n"
                f"season={season}\n"
                f"episode={episode}\n"
                f"quality={qual}\n"
                f"language={lang}\n"
                f"file={fname}\n"
                f"trigger={trigger}"
            )

            update_fields = {}
            if lang and lang not in (series_doc.get("languages") or []):
                update_fields.setdefault("$addToSet", {})["languages"] = lang
            if season and season not in (series_doc.get("seasons") or []):
                update_fields.setdefault("$addToSet", {})["seasons"] = season
            if qual and qual != "Unknown" and qual not in (series_doc.get("qualities") or []):
                update_fields.setdefault("$addToSet", {})["qualities"] = qual

            if update_fields:
                await series_col.update_one({"_id": ObjectId(series_id)}, update_fields)
        except Exception as e:
            logger.error(f"[AUTO SERIES FILTER SYNC ERROR] {e}", exc_info=True)


async def sync_existing_movie_filter(movie_id: str) -> dict:
    """
    Admin helper to resync an existing Super Movie Filter by searching ia_filterdb
    for strictly matching title/year files, removing mismatched files, rebuilding languages & qualities.
    """
    movie = await get_super_movie(movie_id)
    if not movie or movie.get("status") == "deleted":
        return {"success": False, "error": "Movie not found"}

    title = movie.get("title", "")
    year = movie.get("year")
    imdb_id = movie.get("imdb_id")
    tmdb_id = movie.get("tmdb_id")
    clean_title = clean_series_title(title)
    
    from database.ia_filterdb import col, sec_col, MULTIPLE_DATABASE, get_search_results, get_file_details
    from plugins.pm_filter import detect_file_languages
    from plugins.series import extract_quality_from_filename
    from utils import match_movie_identity, extract_release_year, normalize_title_for_matching

    candidate_docs = []
    seen_fids = set()

    files, _, _ = await get_search_results(0, clean_title, max_results=500, offset=0, filter=True)
    for f in (files or []):
        fid = f.get("file_id")
        if fid and fid not in seen_fids:
            seen_fids.add(fid)
            candidate_docs.append(f)

    existing_fids = movie.get("file_ids") or []
    for fid in existing_fids:
        if fid not in seen_fids:
            seen_fids.add(fid)
            fdoc = await get_file_details(fid)
            if fdoc:
                candidate_docs.append(fdoc)

    # Detect known conflicting years for this normalized title
    known_conflicts = set()
    norm_req = normalize_title_for_matching(title)
    for d in candidate_docs:
        fn = d.get("file_name", "")
        if normalize_title_for_matching(fn) == norm_req:
            fy = extract_release_year(fn, d.get("caption", ""))
            if fy:
                known_conflicts.add(fy)

    valid_fids = []
    removed_fids = []
    all_langs = set()
    all_quals = set()

    for f in candidate_docs:
        fid = f.get("file_id")
        if not fid:
            continue
        fname = f.get("file_name", "")
        cap = f.get("caption", "") or ""
        
        is_match, reason = match_movie_identity(
            f,
            requested_title=title,
            requested_year=year,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            known_conflicts=known_conflicts
        )

        if is_match:
            valid_fids.append(fid)
            flangs = detect_file_languages(fname, cap)
            fqual = extract_quality_from_filename(fname)
            for l in flangs:
                if l:
                    all_langs.add(l)
            if fqual and fqual != "Unknown":
                all_quals.add(fqual)
        else:
            removed_fids.append(fid)
            logger.info(f"[SYNC MOVIE FILTER REJECT]\nmovie_id={movie_id}\ntitle={title}\nyear={year}\nfile_name={fname}\nreason={reason}")

    valid_fids = list(dict.fromkeys(valid_fids))
    languages_list = list(all_langs) if all_langs else (movie.get("languages") or [])
    qualities_list = list(all_quals) if all_quals else (movie.get("qualities") or [])

    await super_movies_col.update_one(
        {"_id": ObjectId(movie_id)},
        {
            "$set": {
                "file_ids": valid_fids,
                "languages": languages_list,
                "qualities": qualities_list,
                "updated_at": datetime.utcnow()
            }
        }
    )

    logger.info(
        f"[AUTO MOVIE FILTER SYNC]\n"
        f"movie_id={movie_id}\n"
        f"title={title}\n"
        f"year={year}\n"
        f"total_files={len(valid_fids)}\n"
        f"removed_mismatches={len(removed_fids)}\n"
        f"trigger=admin_resync"
    )

    return {
        "success": True,
        "total_files": len(valid_fids),
        "removed_mismatches": len(removed_fids),
        "languages": languages_list,
        "qualities": qualities_list
    }


async def get_movie_files_for_identity(title: str, year: str | int = None, imdb_id: str = None, tmdb_id: str = None) -> list:
    from database.ia_filterdb import get_search_results
    from utils import match_movie_identity, normalize_title_for_matching, extract_release_year

    clean_title = clean_series_title(title)
    files, _, _ = await get_search_results(0, clean_title, max_results=500, offset=0, filter=True)
    if not files:
        return []

    # Detect known conflicting years for this normalized title
    known_conflicts = set()
    norm_req = normalize_title_for_matching(title)
    for d in files:
        fn = d.get("file_name", "")
        if normalize_title_for_matching(fn) == norm_req:
            fy = extract_release_year(fn, d.get("caption", ""))
            if fy:
                known_conflicts.add(fy)

    matched = []
    seen = set()
    for f in files:
        fid = f.get("file_id")
        if fid and fid not in seen:
            is_match, reason = match_movie_identity(
                f,
                requested_title=title,
                requested_year=year,
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
                known_conflicts=known_conflicts
            )
            if is_match:
                seen.add(fid)
                matched.append(f)

    return matched


async def scan_movie_batch_by_name_year(
    title: str,
    year: str | int = None,
    imdb_id: str = None,
    tmdb_id: str = None
) -> dict:
    """
    Dedicated batch scanner to find ONLY files belonging strictly to an exact movie name + release year.
    Queries database candidates broadly, extracts release year, enforces strict Name + Year
    matching, and returns structured batch scan results.
    """
    from utils import match_movie_identity, normalize_title_for_matching, extract_release_year
    from plugins.pm_filter import detect_file_languages
    from plugins.series import extract_quality_from_filename, get_movie_candidates

    logger.info(
        f"[AUTO MOVIE BATCH] START\n"
        f"title={title}\n"
        f"year={year}"
    )

    req_year_str = str(year).strip() if (year and str(year).strip() not in ["N/A", "None", "0", ""]) else None

    # Retrieve candidate files broadly
    candidate_docs = await get_movie_candidates(0, title=title, year=year, limit=500)
    scanned_count = len(candidate_docs)
    logger.info(f"[AUTO MOVIE BATCH] SCANNED count={scanned_count}")

    matching_files = []
    year_mismatch_count = 0
    title_mismatch_count = 0
    unknown_year_count = 0
    series_count = 0

    norm_req_title = normalize_title_for_matching(title)
    known_conflicts = set()
    for d in candidate_docs:
        fn = d.get("file_name", "")
        if normalize_title_for_matching(fn) == norm_req_title:
            fy = extract_release_year(fn, d.get("caption", ""))
            if fy:
                known_conflicts.add(fy)

    for fdoc in candidate_docs:
        fname = fdoc.get("file_name", "")
        cap = fdoc.get("caption", "") or ""
        f_year = extract_release_year(fname, cap)

        is_match, reason = match_movie_identity(
            fdoc,
            requested_title=title,
            requested_year=year,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            known_conflicts=known_conflicts
        )

        if is_match:
            langs = detect_file_languages(fname, cap)
            l_val = langs[0] if langs else "English"
            q_val = extract_quality_from_filename(fname)

            fdoc_copy = dict(fdoc)
            fdoc_copy["language"] = l_val
            fdoc_copy["quality"] = q_val
            fdoc_copy["title"] = title
            matching_files.append(fdoc_copy)
        else:
            if reason == "YEAR_MISMATCH":
                year_mismatch_count += 1
            elif reason == "TITLE_MISMATCH":
                title_mismatch_count += 1
            elif reason in ("UNKNOWN_YEAR", "YEAR_NOT_FOUND_IN_FILENAME"):
                unknown_year_count += 1
            elif reason == "IS_SERIES":
                series_count += 1
            else:
                title_mismatch_count += 1

    logger.info(f"[AUTO MOVIE BATCH] MATCHED count={len(matching_files)}")
    logger.info(f"[AUTO MOVIE BATCH] REJECTED YEAR count={year_mismatch_count}")
    logger.info(f"[AUTO MOVIE BATCH] REJECTED TITLE count={title_mismatch_count}")
    logger.info("[AUTO MOVIE BATCH] COMPLETE")

    result = {
        "title": title,
        "year": req_year_str,
        "files_scanned": scanned_count,
        "matching_files": matching_files,
        "year_mismatch": year_mismatch_count,
        "title_mismatch": title_mismatch_count,
        "unknown_year": unknown_year_count,
        "series_count": series_count,
        "matched_count": len(matching_files),
        "all_matching_files": matching_files,
        "valid_files": matching_files,
        "total_scanned": scanned_count,
        "total_matched": len(matching_files),
        "total_rejected_year": year_mismatch_count,
        "total_rejected_title": title_mismatch_count,
        "total_new": len(matching_files),
        "total_duplicates": 0
    }
    return result


async def scan_movie_files_by_identity(
    title: str,
    year: str | int = None,
    imdb_id: str = None,
    tmdb_id: str = None
) -> dict:
    """Alias for scan_movie_batch_by_name_year for backward compatibility."""
    return await scan_movie_batch_by_name_year(title, year, imdb_id=imdb_id, tmdb_id=tmdb_id)


async def scan_series_batch_by_name(
    title: str,
    series_id: str = None
) -> dict:
    """
    Dedicated batch scanner for series. Uses Series Name as primary identity,
    scanning for languages, seasons, episodes, and qualities without requiring year matching.
    """
    from plugins.series import scan_sdatabase_for_series
    return await scan_sdatabase_for_series(0, title=title, season=None, series_id=series_id)


