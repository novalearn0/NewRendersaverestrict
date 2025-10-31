import os, time, sys
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

try:
    from config import ADMINS as CFG_ADMINS
except Exception:
    CFG_ADMINS = 0
ADMIN_ID = int(os.getenv("ADMIN_ID") or os.getenv("ADMINS") or CFG_ADMINS or 0)

try:
    from database.db import db
except Exception:
    db = None

KB_BASE = [
    [InlineKeyboardButton("🔑 Login", callback_data="menu_login"),
     InlineKeyboardButton("⛔ Logout", callback_data="menu_logout")],
    [InlineKeyboardButton("🧰 Wizard Help", callback_data="menu_help"),
     InlineKeyboardButton("📁 Set Thumbnail", callback_data="menu_setthumb")],
]

def _log(msg: str):
    print(f"[start] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

@Client.on_message(filters.private & filters.command("start"))
async def start_handler(client: Client, message: Message):
    try:
        user = message.from_user
        user_id = user.id
        name = (user.first_name or "").strip() or user.username or "there"
        if db is not None:
            try:
                await db.add_user(user_id, name)
                _log(f"User added to DB: uid={user_id} name={name}")
            except Exception:
                _log(f"DB add_user failed (may already exist) uid={user_id}")
        text = (f"👋 Hello, {name}!\n\n✅ Your bot is up and running.\n\nUse the buttons below for quick actions — no typing needed.")
        kb = [row.copy() for row in KB_BASE]
        try:
            if user_id == ADMIN_ID:
                kb.append([InlineKeyboardButton("📣 Broadcast (Admin)", callback_data="menu_broadcast")])
        except Exception:
            pass
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        _log(f"/start replied to uid={user_id}")
    except Exception as e:
        _log(f"start_handler error: {e}")
        try:
            await message.reply_text("⚠️ Something went wrong while starting. Check logs.")
        except Exception:
            pass

@Client.on_message(filters.private & filters.command("menu"))
async def menu_command(client: Client, message: Message):
    try:
        user = message.from_user
        uid = user.id
        text = "👋 Menu — quick shortcuts. Use buttons below instead of typing commands."
        kb = [row.copy() for row in KB_BASE]
        if uid == ADMIN_ID:
            kb.append([InlineKeyboardButton("📣 Broadcast (Admin)", callback_data="menu_broadcast")])
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        _log(f"/menu shown to uid={uid}")
    except Exception as e:
        _log(f"menu_command error: {e}")
        try:
            await message.reply_text("⚠️ Failed to open menu. Check logs.")
        except:
            pass

@Client.on_callback_query(filters.regex(r"^menu_"))
async def menu_buttons(client: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data or ""
        uid = callback_query.from_user.id
        _log(f"menu callback {data} from uid={uid}")
        if data == "menu_login":
            await callback_query.answer("To login: send /login and follow the prompts.", show_alert=False)
            try:
                await callback_query.message.edit_text("🔑 To login, send /login and follow the steps in chat.")
            except Exception:
                pass
        elif data == "menu_logout":
            await callback_query.answer("To logout: send /logout.", show_alert=False)
        elif data == "menu_help":
            await callback_query.answer("Wizard help", show_alert=False)
            help_text = ("🧰 Wizard Help:\n\n1) Send /wizard to start the wizard.\n2) Or paste a t.me link (e.g. https://t.me/channel/100-105) — the bot will auto-start.\n\nFollow the prompts to choose where to save and whether to change thumbnails.")
            try:
                await callback_query.message.edit_text(help_text)
            except Exception:
                pass
        elif data == "menu_setthumb":
            await callback_query.answer("Set thumbnail", show_alert=False)
            try:
                await callback_query.message.edit_text("📁 Use /setthumb and reply to an image, or send /setthumb then upload an image.")
            except Exception:
                pass
        elif data == "menu_broadcast":
            if uid == ADMIN_ID:
                await callback_query.answer("Broadcast: reply to a message with /broadcast to send to all users.", show_alert=False)
                try:
                    await callback_query.message.edit_text("📣 Admin: reply to a message with /broadcast to send it to all users.")
                except Exception:
                    pass
            else:
                await callback_query.answer("You're not authorized for broadcast.", show_alert=True)
        else:
            await callback_query.answer("Unknown action", show_alert=True)
    except Exception as e:
        _log(f"menu_buttons handler error: {e}")
        try:
            await callback_query.answer("Internal error (see logs).", show_alert=True)
        except:
            pass
