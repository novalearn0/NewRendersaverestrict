from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db

@Client.on_message(filters.command('setthumb') & filters.private)
async def set_thumb_cmd(client: Client, message: Message):
    if message.reply_to_message and getattr(message.reply_to_message, 'photo', None):
        fid = message.reply_to_message.photo.file_id
        await db.set_thumb(message.from_user.id, fid, current=True)
        return await message.reply_text('✅ Thumbnail saved and set.')
    if message.reply_to_message and getattr(message.reply_to_message, 'document', None) and message.reply_to_message.document.mime_type.startswith('image'):
        fid = message.reply_to_message.document.file_id
        await db.set_thumb(message.from_user.id, fid, current=True)
        return await message.reply_text('✅ Thumbnail saved from document and set.')
    await message.reply_text('Reply to an image to save it as thumbnail.')

@Client.on_message(filters.command('listthumbs') & filters.private)
async def list_thumbs(client: Client, message: Message):
    thumbs = await db.get_thumbs(message.from_user.id)
    if not thumbs:
        return await message.reply_text('No thumbnails saved.')
    await message.reply_text('\n'.join(thumbs[:20]))
