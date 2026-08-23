import motor.motor_asyncio
import logging
from info import AUTH_CHANNEL, OTHER_DB_URI, DATABASE_URI

logger = logging.getLogger(__name__)

# Global singleton client and in-memory cache
_SHARED_CLIENT = None
_SHARED_COL = None
_JOIN_REQ_CACHE = set()

def _get_collection():
    global _SHARED_CLIENT, _SHARED_COL
    if _SHARED_COL is not None:
        return _SHARED_COL
    uri = OTHER_DB_URI or DATABASE_URI
    if uri:
        try:
            _SHARED_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(uri)
            db = _SHARED_CLIENT["JoinReqs"]
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

    async def add_user(self, user_id, first_name, username, date):
        uid = int(user_id)
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
        uid = int(user_id)
        if uid in _JOIN_REQ_CACHE:
            return {"user_id": uid}
        col = _get_collection()
        if col is None:
            return None
        try:
            doc = await col.find_one({"user_id": uid})
            if doc:
                _JOIN_REQ_CACHE.add(uid)
            return doc
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_USER ERROR] {e}")
            return None

    async def get_all_users(self):
        col = _get_collection()
        if col is None:
            return [{"user_id": u} for u in _JOIN_REQ_CACHE]
        try:
            return await col.find().to_list(None)
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_ALL_USERS ERROR] {e}")
            return [{"user_id": u} for u in _JOIN_REQ_CACHE]

    async def delete_user(self, user_id):
        uid = int(user_id)
        _JOIN_REQ_CACHE.discard(uid)
        col = _get_collection()
        if col is None:
            return True
        try:
            await col.delete_one({"user_id": uid})
            return True
        except Exception as e:
            logger.error(f"[JOIN_REQS DELETE_USER ERROR] {e}")
            return False

    async def delete_all_users(self):
        _JOIN_REQ_CACHE.clear()
        col = _get_collection()
        if col is None:
            return 0
        try:
            res = await col.delete_many({})
            return res.deleted_count if res else 0
        except Exception as e:
            logger.error(f"[JOIN_REQS DELETE_ALL_USERS ERROR] {e}")
            return 0

    async def get_all_users_count(self):
        col = _get_collection()
        if col is None:
            return len(_JOIN_REQ_CACHE)
        try:
            return await col.count_documents({})
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_COUNT ERROR] {e}")
            return len(_JOIN_REQ_CACHE)


