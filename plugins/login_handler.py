import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid)
from database.db import db

def get_env_int(name):
    v = os.getenv(name)
    try:
        return int(v) if v else None
    except Exception:
        return None

DEFAULT_API_ID = get_env_int("API_ID")
DEFAULT_API_HASH = os.getenv("API_HASH") or None
SESSION_STRING_MIN_LEN = 100

LOGIN_FLOW = {}

@Client.on_message(filters.private & filters.command("login"))
async def login_start(bot: Client, message: Message):
    uid = message.from_user.id
    if uid in LOGIN_FLOW:
        return await message.reply_text("⚠️ Login already in progress. Send /cancel to abort or continue the current flow.")
    LOGIN_FLOW[uid] = {"step": "ask_api_id"}
    await message.reply_text("Send your API ID from my.telegram.org (or send /skip to use bot default)." )

@Client.on_message(filters.private & filters.command("cancel"))
async def login_cancel(bot: Client, message: Message):
    uid = message.from_user.id
    if LOGIN_FLOW.pop(uid, None):
        return await message.reply_text("❌ Login cancelled.")
    return await message.reply_text("No active login process.")

@Client.on_message(filters.private & ~filters.command(["start","help","login","logout","cancel","resend"]))
async def login_message_handler(bot: Client, message: Message):
    uid = message.from_user.id
    if uid not in LOGIN_FLOW:
        return
    state = LOGIN_FLOW[uid]
    text = (message.text or "").strip()
    try:
        if state["step"] == "ask_api_id":
            if text.lower() == "/skip":
                api_id = DEFAULT_API_ID
                api_hash = DEFAULT_API_HASH
                if not api_id or not api_hash:
                    LOGIN_FLOW.pop(uid, None)
                    return await message.reply_text("Bot default API credentials not configured. Provide API ID and API HASH.")
                state.update({"api_id": api_id, "api_hash": api_hash, "step": "ask_phone"})
                return await message.reply_text("Using bot default API credentials. Now send your phone number with country code.")
            try:
                api_id = int(text)
            except Exception:
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ Invalid API ID. Start /login and send numeric API ID.")
            state["api_id"] = api_id
            state["step"] = "ask_api_hash"
            return await message.reply_text("Now send your API HASH (from my.telegram.org)." )
        if state["step"] == "ask_api_hash":
            api_hash = text
            if not api_hash:
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ API HASH missing. Start /login again.")
            state["api_hash"] = api_hash
            state["step"] = "ask_phone"
            return await message.reply_text("Now send your phone number with country code (example: +9198...). Send /cancel to abort.")
        if state["step"] == "ask_phone":
            phone = text
            state["phone"] = phone
            api_id = state.get("api_id")
            api_hash = state.get("api_hash")
            temp = Client(":memory:", api_id=api_id, api_hash=api_hash)
            await temp.connect()
            try:
                sent = await temp.send_code(phone)
            except PhoneNumberInvalid:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ Phone number invalid. Start /login again.")
            except Exception as e:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text(f"❌ Failed to send code: {e}")
            state["phone_code_hash"] = sent.phone_code_hash
            state["step"] = "ask_code"
            await temp.disconnect()
            return await message.reply_text("✅ Code sent. Now send the code you received (digits only). If OTP expires, send /resend to request a new code.")
        if state["step"] == "ask_code":
            if text.lower() == "/cancel":
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("Login cancelled.")
            phone_code = text.replace(" ", "")
            api_id = state.get("api_id")
            api_hash = state.get("api_hash")
            phone = state.get("phone")
            code_hash = state.get("phone_code_hash")
            temp = Client(":memory:", api_id=api_id, api_hash=api_hash)
            await temp.connect()
            try:
                await temp.sign_in(phone, code_hash, phone_code)
            except PhoneCodeInvalid:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ OTP invalid. Start /login again or use /resend.")
            except PhoneCodeExpired:
                await temp.disconnect()
                state["step"] = "ask_phone"
                return await message.reply_text("❌ OTP expired. Send /resend to request a new code or /login to restart.")
            except SessionPasswordNeeded:
                await temp.disconnect()
                state["step"] = "ask_password"
                return await message.reply_text("🔐 Two-step enabled. Send your password now.")
            except Exception as e:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text(f"❌ Sign-in error: {e}")
            try:
                string_session = await temp.export_session_string()
            except Exception as e:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text(f"❌ Failed to export session: {e}")
            await temp.disconnect()
            if not string_session or len(string_session) < SESSION_STRING_MIN_LEN:
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ Session string invalid. Try /login again.")
            await db.set_session(uid, string_session)
            await db.set_api_id(uid, int(api_id))
            await db.set_api_hash(uid, api_hash)
            LOGIN_FLOW.pop(uid, None)
            return await message.reply_text("✅ Account logged in successfully. You can now use private channel features.")
        if state["step"] == "ask_password":
            pw = text
            api_id = state.get("api_id")
            api_hash = state.get("api_hash")
            phone = state.get("phone")
            code_hash = state.get("phone_code_hash")
            temp = Client(":memory:", api_id=api_id, api_hash=api_hash)
            await temp.connect()
            try:
                await temp.check_password(pw)
            except PasswordHashInvalid:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text("❌ Invalid password. Start /login again.")
            except Exception as e:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text(f"❌ Error verifying password: {e}")
            try:
                string_session = await temp.export_session_string()
            except Exception as e:
                await temp.disconnect()
                LOGIN_FLOW.pop(uid, None)
                return await message.reply_text(f"❌ Failed to export session: {e}")
            await temp.disconnect()
            if not string_session or len(string_session) < SESSION_STRING_MIN_LEN:
                return await message.reply_text("❌ Session string invalid. Try /login again.")
            await db.set_session(uid, string_session)
            await db.set_api_id(uid, int(api_id))
            await db.set_api_hash(uid, api_hash)
            LOGIN_FLOW.pop(uid, None)
            return await message.reply_text("✅ Account logged in successfully. You can now use private channel features.")
    except Exception as e:
        LOGIN_FLOW.pop(uid, None)
        try:
            await message.reply_text(f"❌ Unexpected error: {e}")
        except:
            pass
