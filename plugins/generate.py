
from database.db import db
import asyncio
async def ensure_quota(user_id: int, cost: int = 1):
    # If user is premium, allow regardless of quota (but still return remaining quota)
    try:
        is_p = await db.is_premium(user_id)
        if is_p:
            return True, None
        remaining = await db.get_quota(user_id)
        if remaining <= 0:
            return False, 0
        new_rem = await db.decrement_quota(user_id, cost)
        if new_rem < 0:
            return False, 0
        return True, new_rem
    except Exception as e:
        # on DB error, be permissive but log
        print(f"Quota check error for {user_id}: {e}")
        return True, None

# generate.py kept for backward compatibility (login/logout flows)
import traceback, time, sys
from pyrogram import Client, filters
from pyrogram.types import Message
from asyncio.exceptions import TimeoutError
from pyrogram.errors import (ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid)
from config import API_ID, API_HASH
from database.db import db

SESSION_STRING_SIZE = 200

def _log(msg: str):
    print(f"[generate] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout(client: Client, message: Message):
    try:
        user_session = await db.get_session(message.from_user.id)
        if not user_session:
            return await message.reply_text("You are not logged in.")
        await db.set_session(message.from_user.id, session=None)
        await message.reply_text("✅ Logged out successfully.")
        _log(f"User {message.from_user.id} logged out (session cleared).")
    except Exception as e:
        _log(f"logout error: {e}")
        await message.reply_text("❌ Logout failed (see logs).")