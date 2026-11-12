# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json, asyncio, logging, time
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
logger = logging.getLogger(__name__)
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

# First Database For File Saving 
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

try:
    col.create_index([("file_name", 1)], background=True)
    col.create_index([("file_id", 1)], background=True)
    col.create_index([("file_ids", 1)], background=True)
    col.create_index([("file_name", 1), ("file_size", 1)], background=True)
    col.create_index([("chat_id", 1), ("message_id", 1)], background=True)
except Exception:
    pass

if MULTIPLE_DATABASE:
    try:
        sec_col.create_index([("file_name", 1)], background=True)
        sec_col.create_index([("file_id", 1)], background=True)
        sec_col.create_index([("file_ids", 1)], background=True)
        sec_col.create_index([("file_name", 1), ("file_size", 1)], background=True)
        sec_col.create_index([("chat_id", 1), ("message_id", 1)], background=True)
    except Exception:
        pass


def clean_file_name(file_name, caption=None):
    raw_name = file_name or caption or "file"
    cleaned = re.sub(r"(_|\-|\.|\+)", " ", str(raw_name))
    unwanted_chars = ['[', ']', '(', ')']
    for char in unwanted_chars:
        cleaned = cleaned.replace(char, '')
    cleaned = ' '.join(filter(lambda x: not x.startswith('@'), cleaned.split()))
    return cleaned

async def save_file(media, bot_id=None, sync_filters=True, return_doc=False):
    """Save file in the database with dual-bot and multi-token caching support (Optimized Fast Mode)."""
    from datetime import datetime
    from utils import temp
    file_id = unpack_new_file_id(media.file_id)
    raw_fname = getattr(media, "file_name", None)
    raw_cap = None
    if getattr(media, "caption", None):
        raw_cap = media.caption.html if hasattr(media.caption, "html") else str(media.caption)

    file_name = clean_file_name(raw_fname, raw_cap)
    chat_id = getattr(media, "chat_id", None)
    message_id = getattr(media, "message_id", None)
    file_sz = getattr(media, "file_size", 0)
    bot_id = bot_id or getattr(media, "bot_id", None)
    bot_id_str = str(bot_id) if bot_id else None

    # Step 1: Consolidated Single-Roundtrip Duplicate Check
    or_clauses = [{'file_id': file_id}, {'file_ids': file_id}]
    if chat_id and message_id:
        or_clauses.append({'chat_id': chat_id, 'message_id': message_id})
    if file_name and file_sz:
        or_clauses.append({'file_name': file_name, 'file_size': file_sz})

    def _sync_find_existing():
        try:
            doc = col.find_one({'$or': or_clauses})
            if doc:
                return doc, col
            if MULTIPLE_DATABASE:
                s_doc = sec_col.find_one({'$or': or_clauses})
                if s_doc:
                    return s_doc, sec_col
            # Secondary fallback by file_name if not found
            fname_candidates = [file_name]
            if raw_fname and raw_fname != file_name:
                fname_candidates.append(raw_fname)
            doc = col.find_one({'file_name': {'$in': fname_candidates}})
            if doc:
                return doc, col
            if MULTIPLE_DATABASE:
                s_doc = sec_col.find_one({'file_name': {'$in': fname_candidates}})
                if s_doc:
                    return s_doc, sec_col
        except Exception as qe:
            logger.debug(f"[FIND EXISTING ERROR] {qe}")
        return None, None

    existing_doc, target_col = await asyncio.to_thread(_sync_find_existing)

    if existing_doc and target_col:
        old_file_id = existing_doc.get("file_id")
        old_bot_map = existing_doc.get("bot_file_map", {})
        
        already_registered = False
        if bot_id_str and old_bot_map.get(bot_id_str) == file_id:
            already_registered = True
        elif not bot_id_str and old_file_id == file_id:
            already_registered = True

        update_fields = {
            'updated_at': datetime.utcnow()
        }
        if file_sz and not existing_doc.get("file_size"):
            update_fields['file_size'] = file_sz
        if raw_cap and not existing_doc.get("caption"):
            update_fields['caption'] = raw_cap
        if chat_id and not existing_doc.get("chat_id"):
            update_fields['chat_id'] = chat_id
        if message_id and not existing_doc.get("message_id"):
            update_fields['message_id'] = message_id

        if bot_id_str:
            update_fields[f'bot_file_map.{bot_id_str}'] = file_id

        is_primary = (bot_id and bot_id == getattr(temp, "ME", None)) or not old_file_id
        if is_primary:
            update_fields['file_id'] = file_id

        def _sync_update():
            try:
                target_col.update_one(
                    {"_id": existing_doc["_id"]},
                    {
                        "$set": update_fields,
                        "$addToSet": {"file_ids": file_id}
                    }
                )
            except Exception as ue:
                logger.debug(f"[UPDATE EXISTING ERROR] {ue}")

        await asyncio.to_thread(_sync_update)

        migrated_file_doc = {**existing_doc, **update_fields}

        # Sync with Super Movies & Series if sync_filters is True
        if sync_filters:
            try:
                from database.series_db import super_movies_col, sfiles_col, sync_movie_filter_for_files, sync_series_filter_for_files
                if old_file_id:
                    await super_movies_col.update_many(
                        {"$or": [{"file_ids": old_file_id}, {"file_ids": file_id}]},
                        {"$addToSet": {"file_ids": file_id}, "$set": {"updated_at": datetime.utcnow()}}
                    )
                    s_up_set = {"updated_at": datetime.utcnow()}
                    if chat_id:
                        s_up_set["chat_id"] = chat_id
                    if message_id:
                        s_up_set["message_id"] = message_id
                    if is_primary:
                        s_up_set["file_id"] = file_id
                    if bot_id_str:
                        s_up_set[f"bot_file_map.{bot_id_str}"] = file_id
                    await sfiles_col.update_many(
                        {"$or": [{"file_id": old_file_id}, {"file_ids": old_file_id}]},
                        {
                            "$set": s_up_set,
                            "$addToSet": {"file_ids": file_id}
                        }
                    )
                await sync_movie_filter_for_files([migrated_file_doc], trigger="bot_file_cache")
                await sync_series_filter_for_files([migrated_file_doc], trigger="bot_file_cache")
            except Exception as se:
                logger.debug(f"[BOT FILE CACHE FILTER SYNC ERROR] {se}")

        is_saved = not already_registered
        code = 1 if is_saved else 0
        if return_doc:
            return is_saved, code, migrated_file_doc
        return is_saved, code

    # Step 2: New file insertion
    file = {
        'file_id': file_id,
        'file_ids': [file_id],
        'file_name': file_name,
        'file_size': file_sz,
        'caption': raw_cap
    }
    if bot_id_str:
        file['bot_file_map'] = {bot_id_str: file_id}
    if chat_id:
        file['chat_id'] = chat_id
    if message_id:
        file['message_id'] = message_id

    def _sync_insert():
        try:
            col.insert_one(file)
            return True, 1
        except DuplicateKeyError:
            return False, 0
        except Exception as e:
            if MULTIPLE_DATABASE:
                try:
                    sec_col.insert_one(file)
                    return True, 1
                except DuplicateKeyError:
                    return False, 0
            logger.debug(f"[INSERT FILE ERROR] {e}")
            return False, 2

    is_saved, code = await asyncio.to_thread(_sync_insert)

    if sync_filters and code in (0, 1):
        try:
            from database.series_db import sync_movie_filter_for_files, sync_series_filter_for_files
            m_matched = await sync_movie_filter_for_files([file], trigger="ia_filterdb_col")
            s_matched = await sync_series_filter_for_files([file], trigger="ia_filterdb_col")
            if not m_matched and not s_matched:
                from database.series_db import schedule_delayed_normal_announcement_for_file
                await schedule_delayed_normal_announcement_for_file(file, delay=60)
        except Exception as se:
            logger.debug(f"[AUTO FILTER SYNC ERROR] {se}")

    if return_doc:
        return is_saved, code, file
    return is_saved, code


def is_file_already_saved(file_id, file_name):
    """Check if the exact file_id is already saved in either collection."""
    found = {'$or': [{'file_id': file_id}, {'file_ids': file_id}]}
    collections_to_check = [col, sec_col] if MULTIPLE_DATABASE else [col]
    for collection in collections_to_check:
        if collection.find_one(found, {"_id": 1}):
            return True
    return False

_SEARCH_CACHE = {}
_SEARCH_CACHE_TTL = 60  # seconds

def _sync_search_worker(query: str, offset: int, max_results: int):
    clean_query = query.strip()
    if not clean_query:
        raw_pattern = '.'
    else:
        words = [re.escape(w) for w in clean_query.split() if w]
        if len(words) == 1:
            raw_pattern = r'(\b|[\.\+\-_])' + words[0] + r'(\b|[\.\+\-_])'
        else:
            raw_pattern = r'.*[\s\.\+\-_]'.join(words)
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        regex = re.compile(re.escape(clean_query), flags=re.IGNORECASE)

    filter_criteria = {'file_name': regex}
    projection = {
        "_id": 1, "file_id": 1, "file_name": 1, "file_size": 1,
        "caption": 1, "chat_id": 1, "message_id": 1, "bot_file_map": 1, "file_type": 1
    }

    files = []
    if MULTIPLE_DATABASE:
        cursor1 = col.find(filter_criteria, projection).sort('$natural', -1).skip(offset).limit(max_results)
        for f in cursor1:
            files.append(f)
        if len(files) < max_results:
            cursor2 = sec_col.find(filter_criteria, projection).sort('$natural', -1).skip(offset).limit(max_results - len(files))
            for f in cursor2:
                files.append(f)
    else:
        cursor = col.find(filter_criteria, projection).sort('$natural', -1).skip(offset).limit(max_results)
        for f in cursor:
            files.append(f)

    # Fast total estimation: if returned files < max_results, total is exact without scanning the whole DB
    if len(files) < max_results:
        total_results = offset + len(files)
    else:
        try:
            total_results = col.count_documents(filter_criteria)
            if MULTIPLE_DATABASE:
                total_results += sec_col.count_documents(filter_criteria)
        except Exception:
            total_results = offset + len(files) + 1

    # Fallback search if no results and query contains punctuation or apostrophe (e.g. Butcher's vs Butchers)
    if not files and clean_query and any(c in clean_query for c in ("'", "’", "-", ":", ".")):
        alt_query = re.sub(r"['’\-:\.]+", " ", clean_query).strip()
        alt_words = [re.escape(w) for w in alt_query.split() if len(w) > 1]
        if alt_words:
            alt_pattern = r'.*[\s\.\+\-_]'.join(alt_words)
            try:
                alt_regex = re.compile(alt_pattern, flags=re.IGNORECASE)
                alt_filter = {'file_name': alt_regex}
                if MULTIPLE_DATABASE:
                    alt_cur1 = col.find(alt_filter, projection).sort('$natural', -1).skip(offset).limit(max_results)
                    for f in alt_cur1:
                        files.append(f)
                    if len(files) < max_results:
                        alt_cur2 = sec_col.find(alt_filter, projection).sort('$natural', -1).skip(offset).limit(max_results - len(files))
                        for f in alt_cur2:
                            files.append(f)
                else:
                    alt_cur = col.find(alt_filter, projection).sort('$natural', -1).skip(offset).limit(max_results)
                    for f in alt_cur:
                        files.append(f)
                if len(files) < max_results:
                    total_results = offset + len(files)
                else:
                    total_results = col.count_documents(alt_filter)
                    if MULTIPLE_DATABASE:
                        total_results += sec_col.count_documents(alt_filter)
            except Exception:
                pass

    next_offset = "" if (offset + len(files)) >= total_results or (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results

async def get_search_results(chat_id, query, file_type=None, max_results=5, offset=0, filter=False):
    """For given query return (results, next_offset, total_results) with fast non-blocking worker & memory cache"""
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 5
    try:
        offset = int(offset)
    except Exception:
        offset = 0

    clean_q = str(query or "").strip().lower()
    cache_key = (clean_q, offset, max_results)
    now = time.time()

    if cache_key in _SEARCH_CACHE:
        cached_time, cached_res = _SEARCH_CACHE[cache_key]
        if now - cached_time < _SEARCH_CACHE_TTL:
            return cached_res

    res = await asyncio.to_thread(_sync_search_worker, clean_q, offset, max_results)

    if len(_SEARCH_CACHE) > 500:
        _SEARCH_CACHE.clear()
    _SEARCH_CACHE[cache_key] = (now, res)
    return res

async def get_bad_files(query, file_type=None, use_filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = rf'(\b|[.+-_]){query}(\b|[.+-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[s.+-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], 0

    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def count_documents(collection):
        return collection.count_documents(filter_criteria)

    total_results = (count_documents(col) + count_documents(sec_col) if MULTIPLE_DATABASE else count_documents(col))

    def find_documents(collection):
        return list(collection.find(filter_criteria))

    files = (find_documents(col) + find_documents(sec_col) if MULTIPLE_DATABASE else find_documents(col))

    return files, total_results

async def get_file_details(query):
    doc = col.find_one({'file_id': query})
    if not doc and MULTIPLE_DATABASE:
        doc = sec_col.find_one({'file_id': query})
    if doc:
        return doc
    q = {'$or': [{'file_ids': query}, {'file_id': query}]}
    doc = col.find_one(q)
    if not doc and MULTIPLE_DATABASE:
        doc = sec_col.find_one(q)
    return doc

async def get_bulk_file_details(file_ids: list[str]) -> dict[str, dict]:
    """
    Bulk preloads file details for a list of file IDs in a single query.
    Returns a dict mapping file_id -> file document.
    """
    if not file_ids:
        return {}
    file_map = {}
    q = {"$or": [{"file_id": {"$in": file_ids}}, {"file_ids": {"$in": file_ids}}]}
    for doc in col.find(q):
        fid = doc.get("file_id")
        if fid:
            file_map[fid] = doc
        for f in doc.get("file_ids", []):
            file_map[f] = doc
    if MULTIPLE_DATABASE:
        for doc in sec_col.find(q):
            fid = doc.get("file_id")
            if fid and fid not in file_map:
                file_map[fid] = doc
            for f in doc.get("file_ids", []):
                if f not in file_map:
                    file_map[f] = doc
    return file_map
    if MULTIPLE_DATABASE:
        for doc in sec_col.find(q):
            fid = doc.get("file_id")
            if fid and fid not in file_map:
                file_map[fid] = doc
    return file_map


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")
    
def unpack_new_file_id(new_file_id):
    """Return file_id"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id


async def clear_all_indexed_files(clear_super_file_ids: bool = True) -> dict:
    """
    Safely clears old indexed file records and file IDs without dropping collections.
    Preserves all background indexes on col and sec_col.
    Preserves 100% of Super Movie Filter documents, titles, years, posters, aliases, and settings.
    Preserves 100% of Series Filter documents, titles, keys, posters, captions, and settings.
    Avoids orphaned file references.
    """
    from datetime import datetime
    import logging
    log = logging.getLogger(__name__)

    results = {
        "col_deleted": 0,
        "sec_col_deleted": 0,
        "sfiles_deleted": 0,
        "sbatch_deleted": 0,
        "super_movies_preserved": 0,
        "series_preserved": 0,
        "error": None
    }

    # 1. Clear col (delete_many({}) keeps collection and all indexes intact!)
    try:
        r1 = col.delete_many({})
        results["col_deleted"] = r1.deleted_count
        log.info(f"[DELFILES] Deleted {results['col_deleted']} records from primary collection '{COLLECTION_NAME}'")
    except Exception as e:
        log.error(f"[DELFILES ERROR] Deleting from col: {e}")
        results["error"] = str(e)
        return results

    # 2. Clear sec_col if active
    if MULTIPLE_DATABASE:
        try:
            r2 = sec_col.delete_many({})
            results["sec_col_deleted"] = r2.deleted_count
            log.info(f"[DELFILES] Deleted {results['sec_col_deleted']} records from secondary collection '{COLLECTION_NAME}'")
        except Exception as e:
            log.error(f"[DELFILES ERROR] Deleting from sec_col: {e}")

    # 3. Super Movies: Clear dead file IDs while PRESERVING ALL filter definitions & metadata
    try:
        from database.series_db import (
            super_movies_col,
            sfiles_col,
            sbatch_col,
            series_col,
            invalidate_active_filters_cache
        )

        # Count existing super movie filters
        sm_count = await super_movies_col.count_documents({"status": {"$ne": "deleted"}})
        results["super_movies_preserved"] = sm_count

        if clear_super_file_ids:
            # Reset file arrays and maps to empty; KEEP all titles, years, genres, posters, aliases, configs
            await super_movies_col.update_many(
                {},
                {
                    "$set": {
                        "file_ids": [],
                        "file_map": {},
                        "file_associations": {},
                        "languages": [],
                        "qualities": [],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            log.info(f"[DELFILES] Preserved {sm_count} Super Movie filters, cleared stale file IDs.")

        # 4. Series: Clear episode file mappings in sfiles_col
        sfiles_res = await sfiles_col.delete_many({})
        results["sfiles_deleted"] = sfiles_res.deleted_count
        log.info(f"[DELFILES] Deleted {results['sfiles_deleted']} records from 'series_files'")

        # Clear batch records
        sbatch_res = await sbatch_col.delete_many({})
        results["sbatch_deleted"] = sbatch_res.deleted_count

        # Count preserved series definitions
        s_count = await series_col.count_documents({"status": {"$ne": "deleted"}})
        results["series_preserved"] = s_count

        # Reset series dynamic fields (languages, seasons, qualities) so they populate fresh on reindex
        await series_col.update_many(
            {},
            {
                "$set": {
                    "languages": [],
                    "seasons": [],
                    "qualities": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        log.info(f"[DELFILES] Preserved {s_count} Series definitions.")

        # Invalidate in-memory caches
        try:
            from utils import temp
            if hasattr(temp, "MOVIE_STATE") and isinstance(temp.MOVIE_STATE, dict):
                temp.MOVIE_STATE.clear()
            if hasattr(temp, "SERIES_STATE") and isinstance(temp.SERIES_STATE, dict):
                temp.SERIES_STATE.clear()
            if hasattr(temp, "GETALL") and isinstance(temp.GETALL, dict):
                temp.GETALL.clear()
        except Exception:
            pass

        invalidate_active_filters_cache()

    except Exception as se:
        log.error(f"[DELFILES ERROR] Updating series/super_movies: {se}")
        results["error"] = str(se)

    return results

