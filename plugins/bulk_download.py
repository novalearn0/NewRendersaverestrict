from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio, os, tempfile, time
from database.db import db

@Client.on_message(filters.command("bulkdownload") & filters.private)
async def bulkdownload_cmd(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text("Usage: /bulkdownload <chat_id> <start_id> <end_id> [autothumb:yes/no]")
    chat = args[1]
    try:
        start = int(args[2]); end = int(args[3])
    except:
        return await message.reply_text("Start and end must be integers.")
    auto_thumb = (len(args) >=5 and args[4].lower().startswith('y'))
    uid = message.from_user.id
    # Use user client if available for private channels
    session = await db.get_session(uid)
    api_id = await db.get_api_id(uid)
    api_hash = await db.get_api_hash(uid)
    uclient = None
    use_user = bool(session and api_id and api_hash)
    if use_user:
        try:
            from pyrogram import Client as UserClient
            uclient = UserClient(name=f'user_{uid}', api_id=api_id, api_hash=api_hash, session_string=session)
            await uclient.connect()
        except Exception as e:
            await message.reply_text(f"Could not create user client: {e}\nFalling back to bot client.")

    total = end - start + 1
    if total > 500:
        await message.reply_text("Limit is 500 messages per run. Reducing to 500.")
        end = start + 499

    sent = 0; failed = 0
    user_thumb = await db.get_current_thumb(uid)
    for msg_id in range(start, end+1):
        try:
            src = uclient or client
            msg = await src.get_messages(chat, msg_id)
            if not msg:
                failed += 1; continue
            # Handle video with autothumb
            if getattr(msg, 'video', None) and auto_thumb and user_thumb:
                try:
                    path = await src.download_media(msg, file_name=os.path.join(tempfile.gettempdir(), f'tmp_{msg.message_id}'))
                    if path:
                        await client.send_video(uid, path, thumb=user_thumb)
                        try: os.remove(path)
                        except: pass
                        sent += 1; continue
                except Exception:
                    pass
            # Fast copy or forward
            try:
                await client.copy_message(uid, chat, msg_id)
                sent += 1
            except Exception:
                try:
                    await client.forward_messages(uid, chat, msg_id)
                    sent += 1
                except Exception:
                    failed += 1
            await asyncio.sleep(0.2)
        except Exception:
            failed += 1
            await asyncio.sleep(0.2)
    if uclient:
        try: await uclient.disconnect()
        except: pass
    await message.reply_text(f'Done. Sent: {sent}, Failed: {failed}')
