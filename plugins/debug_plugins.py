from pyrogram import Client, filters
from pyrogram.types import Message
import pkgutil, importlib, sys, time

def _log(msg: str):
    print(f"[debug_plugins] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}", file=sys.stdout, flush=True)

@Client.on_message(filters.private & filters.command("whoami"))
async def whoami(c: Client, m: Message):
    me = await c.get_me()
    _log(f"/whoami by {m.from_user.id} -> @{me.username}")
    await m.reply_text(f"VSave restricted:\nBot user: @{me.username}")

@Client.on_message(filters.private & filters.command(["listplugins", "listplugin", "plugins"]))
async def listplugins(c: Client, m: Message):
    try:
        import plugins
        names = [mod.name for mod in pkgutil.iter_modules(plugins.__path__)]
        _log(f"/listplugins by {m.from_user.id} -> found {len(names)} plugins")
        await m.reply_text("VSave restricted:\nPlugins found:\n" + "\n".join(names))
    except Exception as e:
        _log(f"Error listing plugins: {e}")
        await m.reply_text(f"❌ Failed to list plugins:\n{e}")