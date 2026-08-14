# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, os, json, base64, logging
from utils import temp
from pyrogram import filters, Client, enums
from pyrogram.errors import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    vj = await bot.ask(chat_id=message.from_user.id, text="Now Send Me Your Message Which You Want To Store.")
    file_type = vj.media
    allowed_types = [
        enums.MessageMediaType.VIDEO,
        enums.MessageMediaType.AUDIO,
        enums.MessageMediaType.DOCUMENT,
        enums.MessageMediaType.PHOTO,
    ]
    if file_type not in allowed_types:
        return await vj.reply("Send me only video, audio, document, or photo.")
    if getattr(vj, 'has_protected_content', False) and message.chat.id not in ADMINS:
        return await message.reply("okDa")

    # Get the raw Pyrogram file_id directly — do NOT unpack it
    media_obj = getattr(vj, file_type.value)
    raw_file_id = media_obj.file_id

    prefix = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string = prefix + raw_file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    await message.reply(f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={outstr}")

@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    if " " not in message.text:
        return await message.reply(
            "Use correct format.\nExample <code>/batch https://t.me/VJ_Botz/10 https://t.me/VJ_Botz/20</code>.",
            parse_mode=enums.ParseMode.HTML,
        )
    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply(
            "Use correct format.\nExample <code>/batch https://t.me/VJ_Botz/10 https://t.me/VJ_Botz/20</code>.",
            parse_mode=enums.ParseMode.HTML,
        )
    cmd, first, last = links
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

    match = regex.match(first)
    if not match:
        return await message.reply('Invalid first link.')
    f_chat_id = match.group(4)
    f_msg_id  = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int("-100" + f_chat_id)

    match = regex.match(last)
    if not match:
        return await message.reply('Invalid second link.')
    l_chat_id = match.group(4)
    l_msg_id  = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int("-100" + l_chat_id)

    if str(f_chat_id) != str(l_chat_id):
        return await message.reply("Chat IDs do not match — both links must be from the same channel.")

    if f_msg_id > l_msg_id:
        return await message.reply("First link must have a lower message ID than the second.")

    try:
        chat = await bot.get_chat(f_chat_id)
        chat_id = chat.id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there first.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid link specified.')
    except Exception as e:
        return await message.reply(f'Error: {e}')

    sts = await message.reply(
        f"⏳ Generating batch link...\nScanning messages {f_msg_id} → {l_msg_id}\n"
        "This may take time depending on number of messages."
    )

    # ── FILE_STORE_CHANNEL fast-path ──────────────────────────────────────────
    if chat_id in FILE_STORE_CHANNEL:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"Here is your link https://t.me/{temp.U_NAME}?start=DSTORE-{b_64}")

    # ── Verify bot can read the channel ───────────────────────────────────────
    try:
        await bot.get_messages(chat_id, f_msg_id)
    except Exception as e:
        return await sts.edit(
            f"❌ <b>Cannot read messages from this channel.</b>\n\n"
            f"Make sure the bot is added as an <b>admin</b> in the channel.\n\n"
            f"<code>{e}</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Collect media messages using chunked get_messages ────────────────────
    outlist   = []
    og_msg    = 0
    errors    = 0
    is_pbatch = cmd.lower().strip() == "/pbatch"

    for chunk_start in range(f_msg_id, l_msg_id + 1, 200):
        chunk_end = min(chunk_start + 199, l_msg_id)
        try:
            messages = await bot.get_messages(chat_id, list(range(chunk_start, chunk_end + 1)))
            for msg in messages:
                if not msg or msg.empty or msg.service:
                    errors += 1
                    continue
                if not msg.media:
                    errors += 1
                    continue
                try:
                    file_type = msg.media
                    file      = getattr(msg, file_type.value)
                    if not file:
                        errors += 1
                        continue
                    caption = getattr(msg, 'caption', '') or ''
                    outlist.append({
                        "file_id": file.file_id,
                        "caption": caption,
                        "title":   getattr(file, "file_name", "") or "",
                        "size":    getattr(file, "file_size", 0) or 0,
                        "protect": is_pbatch,
                    })
                    og_msg += 1
                except Exception as ex:
                    logger.warning(f"batch scan error mid={msg.id}: {ex}")
                    errors += 1
        except Exception as ex:
            logger.warning(f"batch chunk error {chunk_start}-{chunk_end}: {ex}")
            errors += (chunk_end - chunk_start + 1)

    if og_msg == 0:
        return await sts.edit(
            "❌ <b>No media files found</b> in the given range.\n\n"
            "• Make sure the bot is an <b>admin</b> in the channel.\n"
            "• Make sure the messages in the range contain files.",
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Write JSON → upload → generate link ──────────────────────────────────
    json_path = f"batchmode_{message.from_user.id}.json"
    with open(json_path, "w+") as out:
        json.dump(outlist, out)

    post = await bot.send_document(
        LOG_CHANNEL,
        json_path,
        file_name="Batch.json",
        caption="⚠️ Generated for filestore.",
    )
    os.remove(json_path)

    msg_id = post.id
    
    logger.info("BATCH JSON UPLOADED")
    logger.info(f"LOG_CHANNEL MSG ID: {msg_id}")
    logger.info("BATCH LINK GENERATED")
    
    # Store whether it's pbatch or normal batch via a prefix
    prefix = "PBATCH-" if message.command[0] == "pbatch" else "BATCH-"
    
    await sts.edit(
        f"✅ <b>Batch link generated!</b>\n\n"
        f"📦 Contains <code>{og_msg}</code> files"
        + (f" (<code>{errors}</code> skipped)" if errors else "") + ".\n\n"
        f"🔗 <code>https://t.me/{temp.U_NAME}?start={prefix}{msg_id}</code>",
        parse_mode=enums.ParseMode.HTML,
    )
