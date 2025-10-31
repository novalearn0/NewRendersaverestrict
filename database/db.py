
import os
import motor.motor_asyncio
from typing import Optional, List
import datetime

DB_URI = os.getenv("MONGO_URI") or os.getenv("DB_URI") or os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "vsavebot")

if not DB_URI:
    # Do not raise at import time to allow local linting without env
    raise RuntimeError("MONGO_URI / DB_URI not set in environment. Please set it in Railway environment variables.")

_client = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
_db = _client[DB_NAME]
_users = _db["users"]
_thumbs = _db["thumbs"]

class Database:
    def __init__(self):
        self.users = _users
        self.thumbs = _thumbs

    # Users
    async def add_user(self, user_id: int, name: str = ""):
        await self.users.update_one(
            {"user_id": int(user_id)},
            {"$set": {"user_id": int(user_id), "name": name, "created_at": datetime.datetime.utcnow()}},
            upsert=True
        )

    async def delete_user(self, user_id: int):
        await self.users.delete_one({"user_id": int(user_id)})
        await self.thumbs.delete_many({"user_id": int(user_id)})

    async def get_all_users(self) -> List[dict]:
        cursor = self.users.find({})
        res = []
        async for doc in cursor:
            res.append(doc)
        return res

    async def total_users_count(self) -> int:
        return await self.users.count_documents({})

    # Session and API creds
    async def set_session(self, user_id: int, session: Optional[str]):
        await self.users.update_one({"user_id": int(user_id)}, {"$set": {"session": session}}, upsert=True)

    async def get_session(self, user_id: int) -> Optional[str]:
        doc = await self.users.find_one({"user_id": int(user_id)})
        return doc.get("session") if doc else None

    async def set_api_id(self, user_id: int, api_id: int):
        await self.users.update_one({"user_id": int(user_id)}, {"$set": {"api_id": int(api_id)}}, upsert=True)

    async def get_api_id(self, user_id: int) -> Optional[int]:
        doc = await self.users.find_one({"user_id": int(user_id)})
        return doc.get("api_id") if doc else None

    async def set_api_hash(self, user_id: int, api_hash: str):
        await self.users.update_one({"user_id": int(user_id)}, {"$set": {"api_hash": api_hash}}, upsert=True)

    async def get_api_hash(self, user_id: int) -> Optional[str]:
        doc = await self.users.find_one({"user_id": int(user_id)})
        return doc.get("api_hash") if doc else None

    # Thumbs / thumbnails
    async def set_thumb(self, user_id: int, file_id: str, current: bool = False):
        await self.thumbs.insert_one({
            "user_id": int(user_id),
            "file_id": file_id,
            "created_at": datetime.datetime.utcnow(),
            "current": bool(current)
        })
        if current:
            await self.set_current_thumb(user_id, file_id)

    async def delete_thumb(self, user_id: int, file_id: str):
        await self.thumbs.delete_one({"user_id": int(user_id), "file_id": file_id})

    async def get_thumbs(self, user_id: int) -> List[str]:
        cursor = self.thumbs.find({"user_id": int(user_id)}).sort("created_at", -1)
        res = []
        async for doc in cursor:
            res.append(doc.get("file_id"))
        return res

    async def set_current_thumb(self, user_id: int, file_id: str):
        await self.thumbs.update_many({"user_id": int(user_id)}, {"$set": {"current": False}})
        await self.thumbs.update_one({"user_id": int(user_id), "file_id": file_id}, {"$set": {"current": True, "updated_at": datetime.datetime.utcnow()}}, upsert=True)

    async def get_current_thumb(self, user_id: int) -> Optional[str]:
        doc = await self.thumbs.find_one({"user_id": int(user_id), "current": True})
        if doc:
            return doc.get("file_id")
        doc2 = await self.thumbs.find_one({"user_id": int(user_id)}, sort=[("created_at", -1)])
        return doc2.get("file_id") if doc2 else None

    # Premium / quota management
    async def grant_premium(self, user_id: int, days: int = 30):
        # Grant premium for `days` days (stores expiry)
        expiry = datetime.datetime.utcnow() + datetime.timedelta(days=int(days))
        await self.users.update_one({"user_id": int(user_id)}, {"$set": {"premium_until": expiry}}, upsert=True)

    async def revoke_premium(self, user_id: int):
        # Remove premium status
        await self.users.update_one({"user_id": int(user_id)}, {"$unset": {"premium_until": ""}})

    async def is_premium(self, user_id: int) -> bool:
        doc = await self.users.find_one({"user_id": int(user_id)})
        if not doc:
            return False
        expiry = doc.get("premium_until")
        if not expiry:
            return False
        if isinstance(expiry, datetime.datetime):
            return expiry > datetime.datetime.utcnow()
        try:
            return datetime.datetime.fromisoformat(expiry) > datetime.datetime.utcnow()
        except Exception:
            return False

    async def set_quota(self, user_id: int, quota: int):
        await self.users.update_one({"user_id": int(user_id)}, {"$set": {"quota": int(quota)}}, upsert=True)

    async def get_quota(self, user_id: int) -> int:
        doc = await self.users.find_one({"user_id": int(user_id)})
        if not doc:
            return 0
        return int(doc.get("quota", 0))

    async def decrement_quota(self, user_id: int, amount: int = 1) -> int:
        # Decrement quota atomically and return remaining quota (or -1 if none)
        res = await self.users.find_one_and_update(
            {"user_id": int(user_id), "quota": {"$gte": amount}},
            {"$inc": {"quota": -int(amount)}},
            return_document=True
        )
        if not res:
            return -1
        return int(res.get("quota", 0))


db = Database()
