# plugins/wizard_cmd.py
from pyrogram import Client, filters
from pyrogram.types import Message
import re, time, sys, traceback

# shared state referenced by wizard_saver
try:
    from plugins.wizard_saver import USER_STATE as WIZ_STATE
except Exception:
    WIZ_STATE = {}

def _log(msg: str):
    print(f"[wizard_cmd] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

def parse_link(text: str):
    m = re.search(r"t\.me/(?:c/)?([A-Za-z0-9_]+)/(\d+)(?:[-–](\d+))?", text)
    if not m:
        return None
    return {"chat": m.group(1), "start": int(m.group(2)), "end": int(m.group(3)) if m.group(3) else int(m.group(2))}

@Client.on_message(filters.private & filters.command("wizard"))
async def wizard_start(c: Client, m: Message):
    uid = m.from_user.id
    try:
        if uid in WIZ_STATE:
            await m.reply_text("⚠️ You already have a wizard flow in progress. Send /cancel to abort.")
            _log(f"/wizard already-in-progress uid={uid}")
            return
        WIZ_STATE[uid] = {"step": 1}
        await m.reply_text(
            "📎 Wizard started.\nSend a t.me post link or range (e.g. https://t.me/channel/100-105).\nSend /cancel to stop."
        )
        _log(f"/wizard started uid={uid}")
    except Exception as e:
        _log(f"wizard_start error: {e}\n{traceback.format_exc()}")

@Client.on_message(filters.private & filters.command("cancel"))
async def wizard_cancel(c: Client, m: Message):
    uid = m.from_user.id
    removed = False
    if WIZ_STATE.pop(uid, None):
        removed = True
    # try clearing login flow if present
    try:
        from plugins.login_handler import LOGIN_FLOW as LOGIN_FLOW_REF
        if isinstance(LOGIN_FLOW_REF, dict) and LOGIN_FLOW_REF.pop(uid, None):
            removed = True
    except Exception:
        pass
    if removed:
        await m.reply_text("✅ Operation cancelled.")
        _log(f"/cancel cleared state uid={uid}")
    else:
        await m.reply_text("ℹ️ No active operation to cancel.")
        _log(f"/cancel nothing to clear uid={uid}")

@Client.on_message(filters.private & filters.text & ~filters.command(["start", "help", "login", "logout", "cancel", "setthumb", "menu", "broadcast"]))
async def wizard_auto_detect(c: Client, m: Message):
    uid = m.from_user.id
    text = (m.text or "").strip()
    if uid in WIZ_STATE:
        _log(f"wizard_auto_detect ignored (already in state) uid={uid}")
        return
    parsed = parse_link(text)
    if not parsed:
        return
    # start flow at step 2 (link already provided)
    WIZ_STATE[uid] = {"step": 2, "link": parsed}
    await m.reply_text("✅ Link received!\nWhere to save? Send `self` (Saved Messages), `here` (this chat) or chat id/@username.")
    _log(f"wizard_auto_detect started for uid={uid} -> {parsed}")
