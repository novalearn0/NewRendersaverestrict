from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from database.db import db
from pyrogram import Client, filters
from config import ADMINS
import asyncio, datetime, time, traceback

async def broadcast_messages(user_id: int, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        wait_time = getattr(e, "value", None) or getattr(e, "x", None) or 0
        await asyncio.sleep(int(wait_time))
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        return False, "Deleted"
    except UserIsBlocked:
        await db.delete_user(int(user_id))
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        return False, "Error"
    except Exception:
        return False, "Error"

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast(bot, message):
    try:
        users = await db.get_all_users()
    except Exception as e:
        return await message.reply_text(f"❌ Failed to fetch user list from DB:\n{e}")
    if not users:
        return await message.reply_text("⚠️ No users found in database.")
    b_msg = message.reply_to_message
    if not b_msg:
        return await message.reply_text("Please reply to the message you want to broadcast.")
    sts = await message.reply_text("📣 Broadcasting started...")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = blocked = deleted = failed = success = 0
    async for user in users:
        uid = user.get("id") if isinstance(user, dict) else None
        if uid is None:
            done += 1; failed += 1; continue
        ok, status = await broadcast_messages(int(uid), b_msg)
        if ok: success += 1
        else:
            if status == "Blocked": blocked += 1
            elif status == "Deleted": deleted += 1
            else: failed += 1
        done += 1
        if done % 20 == 0 or done == total_users:
            try:
                await sts.edit_text(f"📣 Broadcast in progress...\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\n✅ Success: {success}\n🚫 Blocked: {blocked}\n🗑 Deleted: {deleted}\n⚠️ Failed: {failed}")
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                pass
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    try:
        await sts.edit_text(f"✅ **Broadcast Completed** ✅\n🕒 Time taken: {time_taken}\n\n👥 Total Users: {total_users}\n📤 Completed: {done}\n✅ Success: {success}\n🚫 Blocked: {blocked}\n🗑 Deleted: {deleted}\n⚠️ Failed: {failed}")
    except Exception as e:
        await message.reply_text(f"✅ Broadcast completed but failed to update status:\n{e}")