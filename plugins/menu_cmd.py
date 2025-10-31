from database.db import db
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import time, sys, traceback

KB = [
    [InlineKeyboardButton("🔑 Login", callback_data="menu_login"),
     InlineKeyboardButton("⛔ Logout", callback_data="menu_logout")],
    [InlineKeyboardButton("🧰 Wizard Help", callback_data="menu_help"),
     InlineKeyboardButton("📁 Set Thumbnail", callback_data="menu_setthumb")],
]

def _log(msg: str):
    print(f"[menu_cmd] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

@Client.on_message(filters.private & filters.command("menu"))
async def menu_command(c: Client, m: Message):
    try:
        _log(f"menu_command triggered by uid={m.from_user.id} name={m.from_user.first_name}")
        await m.reply_text("👋 Main Menu — use buttons below for quick actions.", reply_markup=InlineKeyboardMarkup(KB))
    except Exception as e:
        _log(f"menu_command error: {e}\n{traceback.format_exc()}")

@Client.on_callback_query(filters.regex(r"^menu_"))
async def menu_callbacks(c: Client, q: CallbackQuery):
    user = q.from_user
    data = q.data or ""
    try:
        _log(f"menu_callback {data} from uid={user.id} name={user.first_name}")
        if data == "menu_login":
            try:
                await q.answer("🔑 Use /login to connect your account.", show_alert=False)
                await q.message.edit_text("🔑 To login, send /login and follow the prompts.")
            except Exception:
                await q.answer("🔑 Use /login to connect your account.", show_alert=False)
        elif data == "menu_logout":
            try:
                await q.answer("⛔ Logout invoked.", show_alert=False)
                await q.message.edit_text("⛔ To logout, send /logout.")
            except Exception:
                await q.answer("⛔ To logout, send /logout.", show_alert=False)
        elif data == "menu_help":
            try:
                await q.answer("🧰 Wizard help shown.", show_alert=False)
                await q.message.edit_text("🧰 Wizard Help:\n1) Send /wizard to start the wizard.\n2) Or paste a t.me link (e.g. https://t.me/channel/100-105).\nThen follow prompts.")
            except Exception:
                await q.answer("🧰 Send /wizard or paste a t.me link to start.", show_alert=False)
        elif data == "menu_setthumb":
            try:
                await q.answer("📁 Set thumbnail", show_alert=False)
                await q.message.edit_text("📁 Use /setthumb and reply to an image, or send /setthumb then upload an image.")
            except Exception:
                await q.answer("📁 Use /setthumb to set your thumbnail.", show_alert=False)
        elif data == "menu_broadcast":
            try:
                await q.answer("📣 Admin broadcast: reply with /broadcast.", show_alert=False)
                await q.message.edit_text("📣 Admin: reply to a message with /broadcast to send to all users.")
            except Exception:
                await q.answer("📣 Admin broadcast: reply with /broadcast.", show_alert=False)
        else:
            await q.answer("Unknown action", show_alert=True)
    except Exception as e:
        _log(f"menu_callbacks error: {e}\n{traceback.format_exc()}")
        try:
            await q.answer("Internal error (see logs).", show_alert=True)
        except:
            pass
