# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, re, asyncio, time
from utils import temp, set_wizard_session, clear_wizard_session, get_wizard_session
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()


def extract_years_from_text(text: str) -> list[int]:
    """
    Extract standalone 4-digit years (1900-2099) from text.
    Uses negative lookbehind and lookahead to ensure standalone 4-digit matching (e.g. not 20260 or 12026).
    """
    if not text:
        return []
    matches = re.findall(r'(?<!\d)(19\d\d|20\d\d)(?!\d)', str(text))
    return [int(m) for m in matches]


def file_matches_year(media, caption, target_year: int) -> bool:
    """
    Check if a media file or its caption contains the requested target year.
    Year may appear anywhere in filename or caption (before/after SxxEyy, beginning/middle/end).
    """
    file_name = getattr(media, 'file_name', '') or ''
    years_in_filename = extract_years_from_text(file_name)
    if target_year in years_in_filename:
        return True
    
    caption_text = ""
    if caption:
        caption_text = getattr(caption, 'html', None) or str(caption)
    years_in_caption = extract_years_from_text(caption_text)
    return target_year in years_in_caption


@Client.on_callback_query(filters.regex(r'^yindex_cancel'))
async def yindex_cancel_callback(bot, query):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return await query.answer("Unauthorized.", show_alert=True)
    
    parts = query.data.split("#")
    target_admin = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else user_id
    if user_id != target_admin and user_id not in ADMINS:
        return await query.answer("You cannot cancel this operation.", show_alert=True)
    
    if not hasattr(temp, "YINDEX_CANCEL") or not isinstance(temp.YINDEX_CANCEL, dict):
        temp.YINDEX_CANCEL = {}
    temp.YINDEX_CANCEL[target_admin] = True
    await query.answer("Cancelling Year Indexing...", show_alert=True)


@Client.on_message(filters.private & filters.command('yindex') & filters.user(ADMINS))
async def yindex_command(bot, message):
    user_id = message.from_user.id

    # 1. Parse and validate year
    text_parts = message.text.strip().split()
    if len(text_parts) < 2:
        return await message.reply(
            "❌ Invalid format! Please specify a 4-digit year (1900-2099).\n\n"
            "**Usage:** <code>/yindex 2026</code>"
        )
    
    year_str = text_parts[1].strip()
    if not re.fullmatch(r'(19\d\d|20\d\d)', year_str):
        return await message.reply(
            "❌ Invalid year! Please provide a valid 4-digit year between 1900 and 2099.\n\n"
            "**Example:** <code>/yindex 2026</code>"
        )
    
    target_year = int(year_str)

    # 2. Prevent duplicate concurrent yindex jobs from the same admin
    if not hasattr(temp, "YINDEX_RUNNING") or not isinstance(temp.YINDEX_RUNNING, dict):
        temp.YINDEX_RUNNING = {}
    if temp.YINDEX_RUNNING.get(user_id):
        return await message.reply("⚠️ You already have an active Year Indexing process running. Please wait for it to complete or cancel it.")

    # 3. Prompt admin for source channel / forwarded message
    try:
        vj = await bot.ask(
            message.chat.id,
            "📅 Year Indexing\n\nSend a file from the database channel or forward any message from the database channel."
        )
    except Exception as e:
        logger.error(f"[YINDEX ASK ERROR] {e}")
        return

    # Extract channel info
    chat_id = None
    last_msg_id = None

    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id
    elif getattr(vj, 'forward_origin', None) and getattr(vj.forward_origin, 'chat', None):
        chat_id = vj.forward_origin.chat.username or vj.forward_origin.chat.id
        last_msg_id = getattr(vj.forward_origin, 'message_id', None)
    elif vj.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(vj.text.strip())
        if match:
            chat_id = match.group(4)
            last_msg_id = int(match.group(5))
            if chat_id.isnumeric():
                chat_id = int("-100" + chat_id)
        else:
            return await vj.reply("❌ Please forward a message/file directly from the database channel.")
    else:
        return await vj.reply("❌ Please forward a message/file directly from the database channel.")

    if not chat_id:
        return await vj.reply("❌ Please forward a message/file directly from the database channel.")

    # 4. Verify channel accessibility
    try:
        target_chat = await bot.get_chat(chat_id)
        resolved_chat_id = target_chat.id
    except ChannelInvalid:
        return await vj.reply("❌ Unable to access the channel. Make sure I am an admin in the channel.")
    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply("❌ Invalid channel username or link specified.")
    except Exception as e:
        logger.exception(e)
        return await vj.reply(f"❌ Error accessing channel: {e}")

    # Validate last_msg_id if present
    if last_msg_id:
        try:
            k = await bot.get_messages(resolved_chat_id, last_msg_id)
            if k.empty:
                logger.warning(f"Message {last_msg_id} was empty or deleted in {resolved_chat_id}")
        except Exception as e:
            return await vj.reply(f"❌ Make sure I am an admin in the database channel.\nError: {e}")

    # Initialize Progress Message
    cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton('Cancel', callback_data=f'yindex_cancel#{user_id}')]])
    progress_msg = await vj.reply_text(
        f"📅 **Year Indexing Starting...**\n\n"
        f"**Year:** <code>{target_year}</code>\n"
        f"**Channel:** <code>{resolved_chat_id}</code>\n"
        f"**Status:** Initializing scan...",
        reply_markup=cancel_btn
    )

    # Run Year Indexing
    await year_index_files_to_db(
        target_year=target_year,
        chat=resolved_chat_id,
        lst_msg_id=last_msg_id or 1000000,
        msg=progress_msg,
        bot=bot,
        admin_id=user_id
    )


async def year_index_files_to_db(target_year: int, chat, lst_msg_id: int, msg, bot, admin_id: int):
    """
    Scans the source channel and indexes only files matching the target year.
    Uses chunked streaming, bounded retries, duplicate checking, and periodic progress updates.
    """
    if not hasattr(temp, "YINDEX_RUNNING") or not isinstance(temp.YINDEX_RUNNING, dict):
        temp.YINDEX_RUNNING = {}
    if not hasattr(temp, "YINDEX_CANCEL") or not isinstance(temp.YINDEX_CANCEL, dict):
        temp.YINDEX_CANCEL = {}

    temp.YINDEX_RUNNING[admin_id] = True
    temp.YINDEX_CANCEL[admin_id] = False
    set_wizard_session(admin_id, "YINDEX", "YINDEX_RUNNING", {"year": target_year, "chat_id": chat})

    scanned = 0
    matching = 0
    indexed = 0
    already_indexed = 0
    skipped = 0
    failed = 0

    batch_size = 200
    current = temp.CURRENT if getattr(temp, 'CURRENT', 1) > 0 else 1
    last_update_time = time.time()
    is_cancelled = False
    interrupted_reason = None
    empty_batches_count = 0
    max_empty_batches = 2

    try:
        while True:
            if temp.YINDEX_CANCEL.get(admin_id, False):
                is_cancelled = True
                break

            batch_ids = list(range(current, current + batch_size))
            messages = None

            # Bounded retry for fetching chunk of messages
            for attempt in range(3):
                try:
                    messages = await bot.get_messages(chat, batch_ids)
                    break
                except FloodWait as e:
                    logger.warning(f"[YINDEX FLOODWAIT] Sleeping {e.value}s")
                    await asyncio.sleep(e.value)
                except Exception as ge:
                    logger.warning(f"[YINDEX GET_MESSAGES RETRY] Attempt {attempt + 1}/3 for batch {current}-{current + batch_size}: {ge}")
                    await asyncio.sleep(2 * (attempt + 1))

            if messages is None:
                logger.error(f"[YINDEX] Failed to fetch batch {current}-{current + batch_size} after retries")
                interrupted_reason = "Telegram network error fetching channel messages."
                break

            # Check if entire batch is empty and we've reached or passed lst_msg_id
            if all(getattr(m, 'empty', True) for m in messages):
                empty_batches_count += 1
                if current >= lst_msg_id and empty_batches_count >= max_empty_batches:
                    break
            else:
                empty_batches_count = 0

            for message in messages:
                if temp.YINDEX_CANCEL.get(admin_id, False):
                    is_cancelled = True
                    break

                scanned += 1

                if getattr(message, 'empty', False):
                    skipped += 1
                    continue
                elif not message.media:
                    skipped += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    skipped += 1
                    continue

                media_type_attr = getattr(message.media, 'value', str(message.media))
                media = getattr(message, str(media_type_attr), None)
                if not media:
                    skipped += 1
                    continue

                media.caption = message.caption

                # Check if file/caption matches the requested year
                if not file_matches_year(media, message.caption, target_year):
                    skipped += 1
                    continue

                matching += 1

                try:
                    aynav, vnay = await save_file(media)
                    if aynav:
                        indexed += 1
                    elif vnay == 0:
                        already_indexed += 1
                    else:
                        failed += 1
                except Exception as fe:
                    logger.exception(f"[YINDEX SAVE ERROR] {fe}")
                    failed += 1

                # Periodic progress update
                now = time.time()
                if scanned % 30 == 0 or (now - last_update_time >= 5):
                    last_update_time = now
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Cancel', callback_data=f'yindex_cancel#{admin_id}')]])
                    try:
                        await msg.edit_text(
                            f"📅 **Year Indexing...**\n\n"
                            f"**Year:** <code>{target_year}</code>\n\n"
                            f"**Scanned:** <code>{scanned}</code>\n"
                            f"**Matching:** <code>{matching}</code>\n"
                            f"**Indexed:** <code>{indexed}</code>\n"
                            f"**Already Indexed:** <code>{already_indexed}</code>\n"
                            f"**Failed:** <code>{failed}</code>",
                            reply_markup=reply_markup
                        )
                    except MessageNotModified:
                        pass
                    except Exception as pe:
                        logger.debug(f"[YINDEX PROGRESS EDIT ERROR] {pe}")

            if is_cancelled:
                break

            current += batch_size

    except Exception as e:
        logger.exception(f"[YINDEX FATAL ERROR] {e}")
        interrupted_reason = str(e)

    finally:
        temp.YINDEX_RUNNING[admin_id] = False
        temp.YINDEX_CANCEL.pop(admin_id, None)
        clear_wizard_session(admin_id)

    # Final summary update
    if is_cancelled:
        try:
            await msg.edit_text(
                f"⚠️ **Year Indexing Interrupted**\n\n"
                f"**Year:** <code>{target_year}</code>\n\n"
                f"**Scanned:** <code>{scanned}</code>\n"
                f"**Matching Files:** <code>{matching}</code>\n"
                f"**Indexed:** <code>{indexed}</code>\n"
                f"**Already Indexed:** <code>{already_indexed}</code>\n"
                f"**Skipped:** <code>{skipped}</code>\n"
                f"**Failed:** <code>{failed}</code>\n\n"
                f"**Reason:** Cancelled by admin."
            )
        except Exception as e:
            logger.error(f"[YINDEX FINAL EDIT ERROR] {e}")
    elif interrupted_reason:
        try:
            await msg.edit_text(
                f"⚠️ **Year Indexing Interrupted**\n\n"
                f"**Year:** <code>{target_year}</code>\n\n"
                f"**Scanned:** <code>{scanned}</code>\n"
                f"**Matching Files:** <code>{matching}</code>\n"
                f"**Indexed:** <code>{indexed}</code>\n"
                f"**Already Indexed:** <code>{already_indexed}</code>\n"
                f"**Skipped:** <code>{skipped}</code>\n"
                f"**Failed:** <code>{failed}</code>\n\n"
                f"**Reason:** <code>{interrupted_reason}</code>"
            )
        except Exception as e:
            logger.error(f"[YINDEX FINAL EDIT ERROR] {e}")
    else:
        try:
            await msg.edit_text(
                f"✅ **Year Indexing Completed**\n\n"
                f"**Year:** <code>{target_year}</code>\n\n"
                f"**Scanned:** <code>{scanned}</code>\n"
                f"**Matching Files:** <code>{matching}</code>\n"
                f"**Indexed:** <code>{indexed}</code>\n"
                f"**Already Indexed:** <code>{already_indexed}</code>\n"
                f"**Skipped:** <code>{skipped}</code>\n"
                f"**Failed:** <code>{failed}</code>"
            )
        except Exception as e:
            logger.error(f"[YINDEX FINAL EDIT ERROR] {e}")


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been decliened by our moderators.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
            reply_to_message_id=int(lst_msg_id)
        )
    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    vj = await bot.ask(message.chat.id, "**Now Send Me Your Channel Last Post Link Or Forward A Last Message From Your Index Channel.\n\nAnd You Can Set Skip Number By - /setskip yourskipnumber**")
    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id
    elif vj.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(vj.text)
        if not match:
            return await vj.reply('Invalid link\n\nTry again by /index')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await vj.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await vj.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.id in ADMINS:
        buttons = [[
            InlineKeyboardButton('Yes', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],[
            InlineKeyboardButton('close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup
        )

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [[
        InlineKeyboardButton('Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
    ],[
        InlineKeyboardButton('Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(
        LOG_CHANNEL,
        f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
        reply_markup=reply_markup
    )
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip number should be an integer.")
        await message.reply(f"Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("Give me a skip number")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>")
                    break
                current += 1
                if current % 30 == 0:
                    can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                    reply = InlineKeyboardMarkup(can)
                    try:
                        await msg.edit_text(
                            text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>",
                            reply_markup=reply
                        )
                    except MessageNotModified:
                        pass
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.caption = message.caption
                aynav, vnay = await save_file(media)
                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1
        except Exception as e:
            logger.exception(e)
            k = await msg.edit(f'Error: {e}')
            await k.reply_text(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')
            await k.reply_text("**If You Get Message Not Modified Error Then Skip Your Saved File Then Index Again**")
        else:
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')
