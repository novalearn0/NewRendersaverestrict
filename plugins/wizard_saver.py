# plugins/wizard_saver.py
import re, asyncio, time, sys
from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db
from pyrogram.errors import FloodWait, RPCError

USER_STATE = {}
CONCURRENT_JOBS = 2
_job_semaphore = asyncio.Semaphore(CONCURRENT_JOBS)

def _log(msg: str):
    print(f"[wizard_saver] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

def parse_link(text: str):
    m = re.search(r"t\.me/(?:(c)/)?([A-Za-z0-9_]+)/(\d+)(?:[-–](\d+))?", text)
    if not m:
        return None
    is_c = bool(m.group(1))
    chat_raw = m.group(2)
    start = int(m.group(3))
    end = int(m.group(4)) if m.group(4) else start
    if is_c:
        chat = "-100" + str(chat_raw)
    else:
        chat = chat_raw
    return {"chat": chat, "start": start, "end": end}

async def send_safe(method, *args, retries=3, backoff=2, **kwargs):
    attempt = 0
    while True:
        try:
            return await method(*args, **kwargs)
        except FloodWait as e:
            wait = int(getattr(e, "value", 0) or 0)
            _log(f"FloodWait sleep {wait}s")
            await asyncio.sleep(wait or 5)
            attempt += 1
            if attempt > retries:
                raise
        except RPCError:
            await asyncio.sleep(backoff)
            attempt += 1
            if attempt > retries:
                raise
        except Exception:
            raise

@Client.on_message(filters.private & filters.text & ~filters.command(["start","help","login","logout","broadcast","setthumb","wizard","menu","cancel"]))
async def wizard_handler(bot: Client, message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    parsed = parse_link(text)
    if uid not in USER_STATE and parsed:
        USER_STATE[uid] = {"step": 2, "link": parsed}
        _log(f"Auto-start flow for uid={uid} link={parsed}")
        await send_safe(bot.send_message, uid, "✅ Link received!\nWhere to save? Send `self`, `here` or chat_id/@username.")
        return

    if uid not in USER_STATE:
        USER_STATE[uid] = {"step": 1}
        _log(f"Started step1 for uid={uid}")
        await send_safe(bot.send_message, uid, "📎 Send Telegram post link or range (e.g. https://t.me/channel/100-105)")
        return

    state = USER_STATE[uid]
    # step 1: expecting link
    if state.get("step") == 1:
        parsed = parse_link(text)
        if not parsed:
            await send_safe(bot.send_message, uid, "❌ Invalid link. Please send a valid Telegram post link.")
            _log(f"Invalid link from uid={uid}: {text[:120]}")
            return
        state["link"] = parsed
        state["step"] = 2
        await send_safe(bot.send_message, uid, "✅ Link received! Now send where to save: `self`, `here` or chat_id/@username.")
        return

    # step 2: destination
    if state.get("step") == 2:
        dest_text = text.lower()
        if dest_text in ("self","saved","me"):
            dest = uid
        elif dest_text == "here":
            dest = message.chat.id
        else:
            dest = text
            if isinstance(dest, str) and dest.isdigit():
                dest = int(dest)
        state["dest"] = dest
        state["step"] = 3
        await send_safe(bot.send_message, uid, "📸 Apply custom thumbnail for videos? Reply `yes` or `no`.")
        return

    # step 3: thumbnail option -> start background job
    if state.get("step") == 3:
        state["auto_thumb"] = text.lower() in ("yes","y","true")
        await send_safe(bot.send_message, uid, "⚙️ Starting download — I'll update progress occasionally.")
        asyncio.create_task(_run_bulk_with_semaphore(bot, message, state, uid))
        USER_STATE.pop(uid, None)
        return

async def _run_bulk_with_semaphore(bot, message, state, uid):
    async with _job_semaphore:
        try:
            await process_bulk(bot, message, state)
        except Exception as e:
            _log(f"Job error uid={uid}: {e}")
            try:
                await send_safe(bot.send_message, uid, f"❌ Error during processing: {e}")
            except:
                pass

async def process_bulk(bot: Client, message: Message, state: dict):
    info = state["link"]
    dest = state["dest"]
    auto_thumb = state.get("auto_thumb", False)

    session = await db.get_session(message.from_user.id)
    api_id = await db.get_api_id(message.from_user.id)
    api_hash = await db.get_api_hash(message.from_user.id)

    use_user_client = bool(session and api_id and api_hash)
    uclient = None
    if use_user_client:
        try:
            from pyrogram import Client as UserClient
            uclient = UserClient(":memory:", api_id=api_id, api_hash=api_hash, session_string=session)
            await uclient.connect()
            _log(f"Using user client for uid={message.from_user.id}")
        except Exception as e:
            await send_safe(bot.send_message, message.from_user.id, f"❌ Failed to create user client: {e}")
            return
    else:
        uclient = bot
        _log("Using bot client (public only)")

    chat = info["chat"]
    start, end = info["start"], info["end"]
    total = end - start + 1
    done = 0
    failed = 0
    user_thumb = await db.get_current_thumb(message.from_user.id) if hasattr(db, "get_current_thumb") else await db.get_thumb(message.from_user.id)

    MAX_RANGE = 200
    if total > MAX_RANGE:
        await send_safe(bot.send_message, message.from_user.id, f"⚠️ Range large ({total}). Limiting to {MAX_RANGE}.")
        end = start + MAX_RANGE -1
        total = MAX_RANGE

    PROG_STEP = max(10, total // 10)

    for msg_id in range(start, end + 1):
        try:
            if uclient is bot:
                try:
                    chat_param = int(chat) if isinstance(chat, str) and chat.lstrip("-").isdigit() else chat
                except:
                    chat_param = chat
                msg = await bot.get_messages(chat_param, msg_id)
            else:
                msg = await uclient.get_messages(chat, msg_id)

            if not msg:
                failed += 1
                continue

            if getattr(msg, "video", None) and auto_thumb and user_thumb:
                try:
                    await send_safe(bot.send_video, dest, video=msg.video.file_id, caption=msg.caption or "", thumb=user_thumb)
                except Exception:
                    await send_safe(msg.copy, dest)
            else:
                await send_safe(msg.copy, dest)

            done += 1
            if done % PROG_STEP == 0 or done == total:
                await send_safe(bot.send_message, message.from_user.id, f"✅ Progress: {done}/{total}")
            await asyncio.sleep(1)
        except FloodWait as e:
            wait = int(getattr(e, "value", 0) or 0)
            await asyncio.sleep(wait or 5)
        except Exception:
            failed += 1
            continue

    if use_user_client and uclient and uclient is not bot:
        try:
            await uclient.disconnect()
        except:
            pass

    await send_safe(bot.send_message, message.from_user.id, f"🎉 Done! Sent {done}. Failed: {failed}")
    _log(f"process_bulk finished uid={message.from_user.id} done={done} failed={failed}")
