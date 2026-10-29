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
except Exception:
    pass

if MULTIPLE_DATABASE:
    try:
        sec_col.create_index([("file_name", 1)], background=True)
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

async def save_file(media):
    """Save file in the database with automatic bot token migration support."""
    from datetime import datetime
    file_id = unpack_new_file_id(media.file_id)
    raw_fname = getattr(media, "file_name", None)
    raw_cap = None
    if getattr(media, "caption", None):
        raw_cap = media.caption.html if hasattr(media.caption, "html") else str(media.caption)

    file_name = clean_file_name(raw_fname, raw_cap)
    chat_id = getattr(media, "chat_id", None)
    message_id = getattr(media, "message_id", None)
    file_sz = getattr(media, "file_size", 0)

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': file_sz,
        'caption': raw_cap
    }
    if chat_id:
        file['chat_id'] = chat_id
    if message_id:
        file['message_id'] = message_id

    # 1. Exact match check (already saved with this exact file_id)
    found_exact = {'file_id': file_id}
    collections_to_check = [col, sec_col] if MULTIPLE_DATABASE else [col]
    for collection in collections_to_check:
        if collection.find_one(found_exact):
            return False, 0

    # 2. Token migration check: same file exists, but file_id is different (old bot token)
    target_col = None
    existing_doc = None

    # Check 2a: Exact match on file_name AND file_size
    query_exact = {'file_name': file_name, 'file_size': file_sz}
    existing_doc = col.find_one(query_exact)
    if existing_doc:
        target_col = col
    elif MULTIPLE_DATABASE:
        existing_doc = sec_col.find_one(query_exact)
        if existing_doc:
            target_col = sec_col

    # Check 2b: Match on file_name only
    if not existing_doc:
        existing_doc = col.find_one({'file_name': file_name})
        if existing_doc:
            target_col = col
        elif MULTIPLE_DATABASE:
            existing_doc = sec_col.find_one({'file_name': file_name})
            if existing_doc:
                target_col = sec_col

    # Check 2c: Match on raw uncleaned media.file_name if different
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
        if old_file_id != file_id:
            # File exists under old bot token: migrate file_id and channel coordinates in-place
            update_fields = {
                'file_id': file_id,
                'file_size': file_sz or existing_doc.get("file_size", 0),
                'caption': raw_cap or existing_doc.get("caption"),
                'updated_at': datetime.utcnow()
            }
            if chat_id:
                update_fields['chat_id'] = chat_id
            if message_id:
                update_fields['message_id'] = message_id

            target_col.update_one({"_id": existing_doc["_id"]}, {"$set": update_fields})
            print(f"[TOKEN MIGRATION] Updated {file_name}: old_file_id={str(old_file_id)[:12]}... -> new_file_id={str(file_id)[:12]}...")

            # Seamlessly migrate Super Movies & Series database records
            try:
                from database.series_db import super_movies_col, sfiles_col, sync_movie_filter_for_files, sync_series_filter_for_files
                if old_file_id:
                    # Update super movies file_ids list
                    await super_movies_col.update_many(
                        {"file_ids": old_file_id},
                        {"$set": {"file_ids.$": file_id, "updated_at": datetime.utcnow()}}
                    )
                    # Update series files record
                    s_up = {"file_id": file_id}
                    if chat_id:
                        s_up["chat_id"] = chat_id
                    if message_id:
                        s_up["message_id"] = message_id
                    await sfiles_col.update_many(
                        {"file_id": old_file_id},
                        {"$set": s_up}
                    )
                migrated_file_doc = {**existing_doc, **update_fields}
                await sync_movie_filter_for_files([migrated_file_doc], trigger="token_migration")
                await sync_series_filter_for_files([migrated_file_doc], trigger="token_migration")
            except Exception as se:
                print(f"[TOKEN MIGRATION FILTER SYNC ERROR] {se}")
            return True, 1
        else:
            return False, 0

    # 3. New file insertion
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
    found = {'file_id': file_id}
    collections_to_check = [col, sec_col] if MULTIPLE_DATABASE else [col]
    for collection in collections_to_check:
        if collection.find_one(found):
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
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})

async def get_bulk_file_details(file_ids: list[str]) -> dict[str, dict]:
    """
    Bulk preloads file details for a list of file IDs in a single query.
    Returns a dict mapping file_id -> file document.
    """
    if not file_ids:
        return {}
    file_map = {}
    q = {"file_id": {"$in": file_ids}}
    for doc in col.find(q):
        fid = doc.get("file_id")
        if fid:
            file_map[fid] = doc
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
    
