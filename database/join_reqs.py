import motor.motor_asyncio
import logging
from info import AUTH_CHANNEL, OTHER_DB_URI, DATABASE_URI

logger = logging.getLogger(__name__)

class JoinReqs:

    def __init__(self):
        uri = OTHER_DB_URI or DATABASE_URI
        if uri:
            try:
                self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
                self.db = self.client["JoinReqs"]
                ch_name = str(AUTH_CHANNEL) if AUTH_CHANNEL else "default"
                self.col = self.db[ch_name]
            except Exception as e:
                logger.error(f"[JOIN_REQS INIT ERROR] {e}")
                self.client = None
                self.db = None
                self.col = None
        else:
            self.client = None
            self.db = None
            self.col = None

    def isActive(self):
        return self.col is not None

    async def add_user(self, user_id, first_name, username, date):
        if not self.isActive():
            return False
        try:
            doc = {
                "user_id": int(user_id),
                "first_name": first_name or "",
                "username": username or "",
                "date": date
            }
            await self.col.update_one({"user_id": int(user_id)}, {"$set": doc}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"[JOIN_REQS ADD_USER ERROR] {e}")
            return False

    async def get_user(self, user_id):
        if not self.isActive():
            return None
        try:
            return await self.col.find_one({"user_id": int(user_id)})
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_USER ERROR] {e}")
            return None

    async def get_all_users(self):
        if not self.isActive():
            return []
        try:
            return await self.col.find().to_list(None)
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_ALL_USERS ERROR] {e}")
            return []

    async def delete_user(self, user_id):
        if not self.isActive():
            return False
        try:
            await self.col.delete_one({"user_id": int(user_id)})
            return True
        except Exception as e:
            logger.error(f"[JOIN_REQS DELETE_USER ERROR] {e}")
            return False

    async def delete_all_users(self):
        if not self.isActive():
            return 0
        try:
            res = await self.col.delete_many({})
            return res.deleted_count if res else 0
        except Exception as e:
            logger.error(f"[JOIN_REQS DELETE_ALL_USERS ERROR] {e}")
            return 0

    async def get_all_users_count(self):
        if not self.isActive():
            return 0
        try:
            return await self.col.count_documents({})
        except Exception as e:
            logger.error(f"[JOIN_REQS GET_COUNT ERROR] {e}")
            return 0

