# plugins/setthumb.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import time, sys, traceback, asyncio
from database.db import db

WAIT_TIMEOUT = 120
AWAITING = {}

def _log(msg: str):
    print(f"[setthumb] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

async def _save(user_id: int, file_id: str):
    try:
        # prefer multi-thumb API if exists
        if hasattr(db, "add_thumb"):
            await db.add_thumb(user_id, file_id)
        elif hasattr(db, "set_thumb"):
            await db.set_thumb(user_id, file_id)
        # set as current if possible
        if hasattr(db, "set_current_thumb"):
            await db.set_current_thumb(user_id, file_id)
        return True
    except Exception as e:
        _log(f"_save db error: {e}")
        return False

@Client.on_message(filters.private & filters.command("setthumb"))
async def cmd_setthumb(client: Client, message: Message):
    user_id = message.from_user.id
    # immediate reply-to photo
    if message.reply_to_message and getattr(message.reply_to_message, "photo", None):
        file_id = message.reply_to_message.photo.file_id
        ok = await _save(user_id, file_id)
        return await message.reply_text("✅ Thumbnail saved." if ok else "❌ DB save failed.")
    # otherwise wait for a new photo
    prev = AWAITING.get(user_id)
    if prev and not prev.done():
        prev.cancel()
    async def waiter():
        try:
            await asyncio.sleep(WAIT_TIMEOUT)
            if AWAITING.get(user_id) is task:
                AWAITING.pop(user_id, None)
                try:
                    await client.send_message(user_id, "⏱ Timeout — no image received. Try /setthumb again.")
                except:
                    pass
        except asyncio.CancelledError:
            pass
    task = asyncio.create_task(waiter())
    AWAITING[user_id] = task
    await message.reply_text(f"📸 Send the image to save as thumbnail (you have {WAIT_TIMEOUT}s). Or reply to an image with /setthumb.")

@Client.on_message(filters.private & filters.photo)
async def photo_receive(client: Client, message: Message):
    user_id = message.from_user.id
    if not AWAITING.get(user_id):
        return
    task = AWAITING.pop(user_id, None)
    if task and not task.done():
        task.cancel()
    try:
        file_id = message.photo.file_id
        ok = await _save(user_id, file_id)
        await message.reply_text("✅ Thumbnail saved." if ok else "❌ Failed to save thumbnail.")
    except Exception as e:
        _log(f"photo_receive error: {e}\n{traceback.format_exc()}")
        await message.reply_text("❌ Error saving thumbnail.")

def _thumb_kb(thumbs: list):
    kb = []
    for f in thumbs:
        kb.append([InlineKeyboardButton("Use", callback_data=f"thumb_use:{f}"),
                   InlineKeyboardButton("Delete", callback_data=f"thumb_del:{f}")])
    if not kb:
        return InlineKeyboardMarkup([[InlineKeyboardButton("No thumbs", callback_data="thumb_none")]])
    return InlineKeyboardMarkup(kb)

@Client.on_message(filters.private & filters.command("thumbs"))
async def cmd_thumbs(client: Client, message: Message):
    uid = message.from_user.id
    thumbs = []
    if hasattr(db, "get_thumbs"):
        thumbs = await db.get_thumbs(uid)
    else:
        one = await db.get_thumb(uid)
        if one:
            thumbs = [one]
    if not thumbs:
        return await message.reply_text("You have no saved thumbnails. Use /setthumb.")
    try:
        await client.send_photo(uid, photo=thumbs[0],
                                caption=f"Saved thumbnails: {len(thumbs)}",
                                reply_markup=_thumb_kb(thumbs))
    except Exception:
        await message.reply_text("Saved thumbnails:\n" + "\n".join(thumbs), reply_markup=_thumb_kb(thumbs))

@Client.on_callback_query(filters.regex(r"^thumb_"))
async def thumb_cb(client: Client, q: CallbackQuery):
    data = q.data or ""
    uid = q.from_user.id
    if data.startswith("thumb_use:"):
        file_id = data.split(":",1)[1]
        if hasattr(db, "set_current_thumb"):
            await db.set_current_thumb(uid, file_id)
        else:
            await db.set_thumb(uid, file_id)
        await q.answer("✅ Selected as current thumbnail.")
        try:
            await q.message.edit_caption("✅ Selected as current thumbnail.")
        except:
            pass
    elif data.startswith("thumb_del:"):
        fid = data.split(":",1)[1]
        if hasattr(db, "delete_thumb"):
            await db.delete_thumb(uid, fid)
        await q.answer("🗑 Deleted")
        # update keyboard if possible
        thumbs = []
        if hasattr(db, "get_thumbs"):
            thumbs = await db.get_thumbs(uid)
        if thumbs:
            try:
                await q.message.edit_reply_markup(_thumb_kb(thumbs))
            except:
                pass
    else:
        await q.answer("Unknown", show_alert=True)
