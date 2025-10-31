from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio, time, os, platform, datetime
try:
    import psutil
except Exception:
    psutil = None
from database.db import db
from config import ADMINS

START_TIME = time.time()

@Client.on_message(filters.command("status") & filters.user(ADMINS))
async def status_cmd(client: Client, message: Message):
    """Admin-only status overview"""
    try:
        uptime = int(time.time() - START_TIME)
        uptime_str = str(datetime.timedelta(seconds=uptime))
        # DB checks
        try:
            total_users = await db.total_users_count()
        except Exception as e:
            total_users = f"DB error: {e}"
        # premium count (approx)
        try:
            cursor = db.users.find({"premium_until": {"$exists": True}})
            premium_count = 0
            async for _ in cursor:
                premium_count += 1
        except Exception:
            premium_count = "N/A"
        text = (
            f"<b>Bot Status</b>\n"
            f"Uptime: {uptime_str}\n"
            f"Python: {platform.python_version()}\n"
            f"Platform: {platform.system()} {platform.release()}\n"
            f"Total users (db): {total_users}\n"
            f"Premium users: {premium_count}\n"
            f"Working dir: {os.getcwd()}\n"
        )
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"Error getting status: {e}")

@Client.on_message(filters.command("grantpremium") & filters.user(ADMINS))
async def grant_premium_cmd(client: Client, message: Message):
    """Usage: /grantpremium <user_id> <days>"""
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /grantpremium <user_id> <days>")
    try:
        uid = int(args[1])
        days = int(args[2])
        await db.grant_premium(uid, days)
        await message.reply_text(f"✅ Granted premium to {uid} for {days} days.")
    except Exception as e:
        await message.reply_text(f"Failed to grant premium: {e}")

@Client.on_message(filters.command("revokepremium") & filters.user(ADMINS))
async def revoke_premium_cmd(client: Client, message: Message):
    """Usage: /revokepremium <user_id>"""
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text("Usage: /revokepremium <user_id>")
    try:
        uid = int(args[1])
        await db.revoke_premium(uid)
        await message.reply_text(f"✅ Revoked premium for {uid}.")
    except Exception as e:
        await message.reply_text(f"Failed to revoke premium: {e}")

@Client.on_message(filters.command("mypremium") & filters.private)
async def my_premium_cmd(client: Client, message: Message):
    uid = message.from_user.id
    try:
        is_p = await db.is_premium(uid)
        quota = await db.get_quota(uid)
        if is_p:
            await message.reply_text(f"✅ You are PREMIUM. Quota: {quota}")
        else:
            await message.reply_text(f"❌ You are not premium. Quota: {quota}\nContact admin to upgrade.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")


@Client.on_message(filters.command("setquota") & filters.user(ADMINS))
async def set_quota_cmd(client: Client, message: Message):
    """Usage: /setquota <user_id> <amount>"""
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /setquota <user_id> <amount>")
    try:
        uid = int(args[1])
        amt = int(args[2])
        await db.set_quota(uid, amt)
        await message.reply_text(f"✅ Set quota for {uid} to {amt}.")
    except Exception as e:
        await message.reply_text(f"Failed to set quota: {e}")
