# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import logging
from datetime import datetime
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Lowercase, strip extra spaces — used for search."""
    return re.sub(r"\s+", " ", name.strip().lower())


async def _ensure_indexes():
    """Create useful indexes once at startup."""
    try:
        await series_col.create_index("normalized_name")
        await sfiles_col.create_index(
            ["series_id", "language", "season", "episode", "quality"]
        )
        await sbatch_col.create_index(
            ["series_id", "language", "season", "quality"]
        )
    except Exception as e:
        logger.warning(f"Series DB index creation: {e}")


# ─── Series CRUD ──────────────────────────────────────────────────────────────

async def create_series(data: dict) -> str:
    """
    Insert a new series document.
    data keys: name, year, genre, description, poster,
                languages, seasons, qualities, created_by
    Returns the new _id string.
    """
    doc = {
        "name": data.get("name", ""),
        "normalized_name": _normalize(data.get("name", "")),
        "year": data.get("year", "N/A"),
        "genre": data.get("genre", "N/A"),
        "rating": data.get("rating", ""),
        "description": data.get("description", ""),
        "poster": data.get("poster", ""),
        "languages": data.get("languages", []),
        "seasons": data.get("seasons", []),
        "qualities": data.get("qualities", []),
        "created_by": data.get("created_by"),
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


async def search_series(query: str) -> list[dict]:
    """Regex search across series names.  Returns up to 5 matches."""
    q = query.strip()
    if not q:
        return []
    try:
        raw = r"(^|\s)" + re.escape(q)
        regex = re.compile(raw, re.IGNORECASE)
    except Exception:
        regex = re.compile(re.escape(q), re.IGNORECASE)
    cursor = series_col.find(
        {"normalized_name": regex, "status": "active"}
    ).limit(5)
    return [doc async for doc in cursor]


async def update_series(series_id: str, data: dict):
    """Partial update on a series document."""
    data["updated_at"] = datetime.utcnow()
    await series_col.update_one(
        {"_id": ObjectId(series_id)},
        {"$set": data}
    )


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
    existing = await sfiles_col.find_one({
        "series_id": data["series_id"],
        "language":  data["language"],
        "season":    data["season"],
        "episode":   data["episode"],
        "quality":   data["quality"],
        "message_id": data["message_id"],
    })
    if existing:
        return False, "duplicate"

    doc = {
        "series_id":  data["series_id"],
        "language":   data["language"],
        "season":     int(data["season"]),
        "episode":    int(data["episode"]),
        "quality":    data["quality"],
        "chat_id":    data.get("chat_id"),
        "message_id": data.get("message_id"),
        "file_id":    data.get("file_id", ""),
        "file_name":  data.get("file_name", ""),
        "file_size":  data.get("file_size", 0),
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


async def replace_series_file(data: dict):
    """Replace an existing episode file document."""
    await sfiles_col.delete_many({
        "series_id": data["series_id"],
        "language":  data["language"],
        "season":    data["season"],
        "episode":   data["episode"],
        "quality":   data["quality"],
        "message_id": data["message_id"],
    })
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
        "series_id": series_id,
        "language":  language,
        "season":    int(season),
        "episode":   int(episode),
        "quality":   quality,
    })
    return [doc async for doc in cursor]


async def list_series_languages(series_id: str) -> list[str]:
    """Distinct languages with at least one file saved."""
    return await sfiles_col.distinct("language", {"series_id": series_id})


async def list_series_seasons(series_id: str, language: str) -> list[int]:
    """Distinct season numbers for (series, language)."""
    vals = await sfiles_col.distinct(
        "season", {"series_id": series_id, "language": language}
    )
    return sorted(vals)


async def list_season_qualities(series_id: str, language: str, season: int) -> list[str]:
    """Distinct qualities for (series, language, season)."""
    return await sfiles_col.distinct(
        "quality",
        {
            "series_id": series_id,
            "language":  language,
            "season":    int(season),
        }
    )


async def list_quality_episodes(
    series_id: str, language: str, season: int, quality: str
) -> list[int]:
    """Distinct episodes for (series, language, season, quality)."""
    vals = await sfiles_col.distinct(
        "episode",
        {
            "series_id": series_id,
            "language":  language,
            "season":    int(season),
            "quality":   quality,
        }
    )
    return sorted(vals)


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
