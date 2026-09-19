import motor.motor_asyncio
import logging
from info import AUTH_CHANNEL, OTHER_DB_URI, DATABASE_URI

logger = logging.getLogger(__name__)

# Global singleton client and in-memory cache
_SHARED_CLIENT = None
_SHARED_COL = None
_JOIN_REQ_CACHE = set()

def _get_client():
    global _SHARED_CLIENT
    if _SHARED_CLIENT is not None:
        return _SHARED_CLIENT
    uri = OTHER_DB_URI or DATABASE_URI
    if uri:
        try:
            _SHARED_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(uri)
            return _SHARED_CLIENT
        except Exception as e:
            logger.error(f"[JOIN_REQS CLIENT INIT ERROR] {e}")
            return None
    return None

def _get_collection():
    global _SHARED_COL
    if _SHARED_COL is not None:
        return _SHARED_COL
    client = _get_client()
    if client:
        try:
            db = client["JoinReqs"]
            ch_name = str(AUTH_CHANNEL) if AUTH_CHANNEL else "default"
            _SHARED_COL = db[ch_name]
            return _SHARED_COL
        except Exception as e:
            logger.error(f"[JOIN_REQS INIT ERROR] {e}")
            return None
    return None

class JoinReqs:

    def __init__(self):
        self.col = _get_collection()

    def isActive(self):
        return self.col is not None or len(_JOIN_REQ_CACHE) > 0

    async def add_user(self, user_id, first_name="", username="", date=None):
        try:
            uid = int(user_id)
        except Exception:
            return False
        _JOIN_REQ_CACHE.add(uid)
        col = _get_collection()
        if col is None:
            return True
        try:
            doc = {
                "user_id": uid,
                "first_name": first_name or "",
                "username": username or "",
                "date": date
            }
            await col.update_one({"user_id": uid}, {"$set": doc}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"[JOIN_REQS ADD_USER ERROR] {e}")
            return True

    async def get_user(self, user_id):
        try:
            uid = int(user_id)
        except Exception:
            return None
        if uid in _JOIN_REQ_CACHE:
            return {"user_id": uid}
        client = _get_client()
        if client is not None:
            try:
                db = client["JoinReqs"]
                col_names = await db.list_collection_names()
                for c_name in col_names:
                    doc = await db[c_name].find_one({"user_id": uid})
                    if doc:
                        _JOIN_REQ_CACHE.add(uid)
                        return doc
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_USER MULTI ERROR] {e}")
        col = _get_collection()
        if col is not None:
            try:
                doc = await col.find_one({"user_id": uid})
                if doc:
                    _JOIN_REQ_CACHE.add(uid)
                return doc
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_USER ERROR] {e}")
                return None
        return None

    async def get_all_users(self):
        client = _get_client()
        users = []
        seen = set()
        if client is not None:
            try:
                db = client["JoinReqs"]
                col_names = await db.list_collection_names()
                for c_name in col_names:
                    docs = await db[c_name].find().to_list(10000)
                    for d in docs:
                        uid = d.get("user_id")
                        if uid and uid not in seen:
                            seen.add(uid)
                            users.append(d)
                if users:
                    return users
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_ALL_USERS MULTI ERROR] {e}")
        col = _get_collection()
        if col is not None:
            try:
                docs = await col.find().to_list(10000)
                for d in docs:
                    uid = d.get("user_id")
                    if uid and uid not in seen:
                        seen.add(uid)
                        users.append(d)
                if users:
                    return users
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_ALL_USERS ERROR] {e}")
        return [{"user_id": u} for u in _JOIN_REQ_CACHE]

    async def delete_user(self, user_id):
        try:
            uid = int(user_id)
        except Exception:
            return False
        _JOIN_REQ_CACHE.discard(uid)
        client = _get_client()
        if client is not None:
            try:
                db = client["JoinReqs"]
                col_names = await db.list_collection_names()
                for c_name in col_names:
                    await db[c_name].delete_one({"user_id": uid})
            except Exception as e:
                logger.error(f"[JOIN_REQS DELETE_USER MULTI ERROR] {e}")
        col = _get_collection()
        if col is not None:
            try:
                await col.delete_one({"user_id": uid})
                return True
            except Exception as e:
                logger.error(f"[JOIN_REQS DELETE_USER ERROR] {e}")
                return False
        return True

    async def delete_all_users(self):
        _JOIN_REQ_CACHE.clear()
        total_deleted = 0
        client = _get_client()
        if client is not None:
            try:
                db = client["JoinReqs"]
                col_names = await db.list_collection_names()
                for c_name in col_names:
                    res = await db[c_name].delete_many({})
                    total_deleted += res.deleted_count if res else 0
                return total_deleted
            except Exception as e:
                logger.error(f"[JOIN_REQS DELETE_ALL_USERS MULTI ERROR] {e}")
        col = _get_collection()
        if col is not None:
            try:
                res = await col.delete_many({})
                return res.deleted_count if res else 0
            except Exception as e:
                logger.error(f"[JOIN_REQS DELETE_ALL_USERS ERROR] {e}")
                return 0
        return total_deleted

    async def get_all_users_count(self):
        total_count = 0
        client = _get_client()
        if client is not None:
            try:
                db = client["JoinReqs"]
                col_names = await db.list_collection_names()
                for c_name in col_names:
                    c_cnt = await db[c_name].count_documents({})
                    total_count += c_cnt
                if total_count > 0:
                    return total_count
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_COUNT MULTI ERROR] {e}")
        col = _get_collection()
        if col is not None:
            try:
                return await col.count_documents({})
            except Exception as e:
                logger.error(f"[JOIN_REQS GET_COUNT ERROR] {e}")
        return len(_JOIN_REQ_CACHE)


