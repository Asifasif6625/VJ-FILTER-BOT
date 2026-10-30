# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
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

async def save_file(media, bot_id=None):
    """Save file in the database with dual-bot and multi-token caching support."""
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

    # Step 1: Find if this file already exists in MongoDB
    target_col = None
    existing_doc = None

    # 1a: Exact match on channel coordinates (chat_id and message_id)
    if chat_id and message_id:
        coord_q = {'chat_id': chat_id, 'message_id': message_id}
        existing_doc = col.find_one(coord_q)
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one(coord_q)
            if existing_doc:
                target_col = sec_col

    # 1b: Exact match on file_name and file_size
    if not existing_doc:
        query_exact = {'file_name': file_name, 'file_size': file_sz}
        existing_doc = col.find_one(query_exact)
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one(query_exact)
            if existing_doc:
                target_col = sec_col

    # 1c: Match on file_id in primary file_id or file_ids list
    if not existing_doc:
        found_exact = {'$or': [{'file_id': file_id}, {'file_ids': file_id}]}
        existing_doc = col.find_one(found_exact)
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one(found_exact)
            if existing_doc:
                target_col = sec_col

    # 1d: Match on file_name only
    if not existing_doc:
        existing_doc = col.find_one({'file_name': file_name})
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one({'file_name': file_name})
            if existing_doc:
                target_col = sec_col

    # 1e: Match on raw uncleaned file name if different
    if not existing_doc and raw_fname and raw_fname != file_name:
        existing_doc = col.find_one({'file_name': raw_fname})
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one({'file_name': raw_fname})
            if existing_doc:
                target_col = sec_col

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

        # If primary bot or if file_id was missing/empty, update main file_id
        is_primary = (bot_id and bot_id == getattr(temp, "ME", None)) or not old_file_id
        if is_primary:
            update_fields['file_id'] = file_id

        target_col.update_one(
            {"_id": existing_doc["_id"]},
            {
                "$set": update_fields,
                "$addToSet": {"file_ids": file_id}
            }
        )

        if not already_registered:
            print(f"[BOT FILE CACHE] Updated {file_name}: bot={bot_id_str} fid={str(file_id)[:12]}...")

        # Sync with Super Movies & Series
        try:
            from database.series_db import super_movies_col, sfiles_col, sync_movie_filter_for_files, sync_series_filter_for_files
            if old_file_id:
                # Add file_id to super movies without removing other bot file_ids
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
            migrated_file_doc = {**existing_doc, **update_fields}
            await sync_movie_filter_for_files([migrated_file_doc], trigger="bot_file_cache")
            await sync_series_filter_for_files([migrated_file_doc], trigger="bot_file_cache")
        except Exception as se:
            print(f"[BOT FILE CACHE FILTER SYNC ERROR] {se}")

        return (True, 1) if not already_registered else (False, 0)

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

    try:
        col.insert_one(file)
        print(f"{file_name} is successfully saved.")
        try:
            from database.series_db import sync_movie_filter_for_files, sync_series_filter_for_files
            await sync_movie_filter_for_files([file], trigger="ia_filterdb_col")
            await sync_series_filter_for_files([file], trigger="ia_filterdb_col")
        except Exception as se:
            print(f"[AUTO FILTER SYNC ERROR] {se}")
        return True, 1
    except DuplicateKeyError:
        print(f"{file_name} is already saved.")
        return False, 0
    except Exception as e:
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                print(f"{file_name} is successfully saved.")
                try:
                    from database.series_db import sync_movie_filter_for_files, sync_series_filter_for_files
                    await sync_movie_filter_for_files([file], trigger="ia_filterdb_sec_col")
                    await sync_series_filter_for_files([file], trigger="ia_filterdb_sec_col")
                except Exception as se:
                    print(f"[AUTO FILTER SYNC ERROR] {se}")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
        else:
            print(f"Error saving file: {e}")
            return False, 2

def is_file_already_saved(file_id, file_name):
    """Check if the exact file_id is already saved in either collection."""
    found = {'$or': [{'file_id': file_id}, {'file_ids': file_id}]}
    collections_to_check = [col, sec_col] if MULTIPLE_DATABASE else [col]
    for collection in collections_to_check:
        if collection.find_one(found, {"_id": 1}):
            return True
    return False

async def get_search_results(chat_id, query, file_type=None, max_results=5, offset=0, filter=False):
    """For given query return (results, next_offset)"""
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 5
    
    query = query.strip()
    if not query:
        raw_pattern = '.'
    else:
        words = [re.escape(w) for w in query.split() if w]
        if len(words) == 1:
            raw_pattern = r'(\b|[\.\+\-_])' + words[0] + r'(\b|[\.\+\-_])'
        else:
            raw_pattern = r'.*[\s\.\+\-_]'.join(words)
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        regex = re.compile(re.escape(query), flags=re.IGNORECASE)
    filter_criteria = {'file_name': regex}
    files = []
    if MULTIPLE_DATABASE:
        cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        
        for file in cursor1:
            files.append(file)
        for file in cursor2:
            if len(files) >= max_results:
                break
            files.append(file)
        files = files[:max_results]
    else:
        cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        
        for file in cursor:
            files.append(file)

    total_results = col.count_documents(filter_criteria) if not MULTIPLE_DATABASE else (col.count_documents(filter_criteria) + sec_col.count_documents(filter_criteria))

    # Fallback search if no results and query contains punctuation or apostrophe (e.g. Butcher's vs Butchers)
    if not files and query and any(c in query for c in ("'", "’", "-", ":", ".")):
        alt_query = re.sub(r"['’\-:\.]+", " ", query).strip()
        alt_words = [re.escape(w) for w in alt_query.split() if len(w) > 1]
        if alt_words:
            alt_pattern = r'.*[\s\.\+\-_]'.join(alt_words)
            try:
                alt_regex = re.compile(alt_pattern, flags=re.IGNORECASE)
                alt_filter = {'file_name': alt_regex}
                if MULTIPLE_DATABASE:
                    alt_cur1 = col.find(alt_filter).sort('$natural', -1).skip(offset).limit(max_results)
                    alt_cur2 = sec_col.find(alt_filter).sort('$natural', -1).skip(offset).limit(max_results)
                    for file in alt_cur1:
                        files.append(file)
                    for file in alt_cur2:
                        if len(files) >= max_results:
                            break
                        files.append(file)
                    files = files[:max_results]
                else:
                    alt_cur = col.find(alt_filter).sort('$natural', -1).skip(offset).limit(max_results)
                    for file in alt_cur:
                        files.append(file)
                total_results = col.count_documents(alt_filter) if not MULTIPLE_DATABASE else (col.count_documents(alt_filter) + sec_col.count_documents(alt_filter))
            except Exception:
                pass

    next_offset = "" if (offset + len(files)) >= total_results or (offset + max_results) >= total_results else (offset + max_results)

    return files, next_offset, total_results

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
    
