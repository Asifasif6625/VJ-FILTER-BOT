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
    Fast path: substring check before regex extraction with leading prefix marker stripping.
    """
    from utils import strip_file_prefix_markers
    target_str = str(target_year)
    file_name = getattr(media, 'file_name', '') or ''
    has_in_filename = target_str in file_name
    
    caption_text = ""
    if caption:
        caption_text = getattr(caption, 'html', None) or str(caption)
    has_in_caption = target_str in caption_text if caption_text else False

    if not has_in_filename and not has_in_caption:
        return False

    if has_in_filename:
        clean_file_name = strip_file_prefix_markers(file_name)
        years_in_filename = extract_years_from_text(clean_file_name)
        if target_year in years_in_filename:
            return True

    if has_in_caption:
        clean_caption_text = strip_file_prefix_markers(caption_text)
        years_in_caption = extract_years_from_text(clean_caption_text)
        if target_year in years_in_caption:
            return True

    return False


async def update_yindex_progress(session_id: str, bot=None, force: bool = False, status_override: str = None, reply_markup="KEEP"):
    """
    Authoritative progress updater for /yindex.
    Reads live session counters and edits the single progress message with throttling.
    """
    sessions = getattr(temp, "YINDEX_SESSIONS", {})
    session = sessions.get(session_id)
    if not session:
        return

    now = time.monotonic()
    last_update = session.get("last_progress_update", 0.0)
    last_scanned = session.get("last_scanned_update", 0)
    scanned_diff = session.get("scanned", 0) - last_scanned

    # Throttled check unless forced
    if not force:
        if scanned_diff < 50 and (now - last_update) < 3.0:
            return

    target_year = session.get("year")
    scanned = session.get("scanned", 0)
    matching = session.get("matching", 0)
    indexed = session.get("indexed", 0)
    already_indexed = session.get("already_indexed", 0)
    skipped = session.get("skipped", 0)
    failed = session.get("failed", 0)
    stop_requested = session.get("stop_requested", False)
    is_running = session.get("is_running", False)

    # Determine status & title
    if status_override:
        status_text = status_override
        title_text = "📅 <b>Year Indexing Started</b>"
        if "Stopped" in status_override or "🔴" in status_override:
            title_text = "🛑 <b>Year Indexing Stopped</b>"
        elif "Completed" in status_override or "✅" in status_override:
            title_text = "✅ <b>Year Indexing Completed</b>"
        elif "Failed" in status_override or "⚠️" in status_override:
            title_text = "⚠️ <b>Year Indexing Failed</b>"
    elif stop_requested and is_running:
        title_text = "📅 <b>Year Indexing Started</b>"
        status_text = "🟡 Stopping..."
    elif stop_requested and not is_running:
        title_text = "🛑 <b>Year Indexing Stopped</b>"
        status_text = "🔴 Stopped by admin"
    elif not is_running:
        title_text = "✅ <b>Year Indexing Completed</b>"
        status_text = "✅ Completed"
    else:
        title_text = "📅 <b>Year Indexing Started</b>"
        status_text = "🟢 Indexing..."

    text = (
        f"{title_text}\n\n"
        f"<b>Year:</b> <code>{target_year}</code>\n\n"
        f"<b>Scanned:</b> <code>{scanned}</code>\n"
        f"<b>Matching Files:</b> <code>{matching}</code>\n"
        f"<b>Indexed:</b> <code>{indexed}</code>\n"
        f"<b>Already Indexed:</b> <code>{already_indexed}</code>\n"
        f"<b>Skipped:</b> <code>{skipped}</code>\n"
        f"<b>Failed:</b> <code>{failed}</code>\n\n"
        f"<b>Status:</b> {status_text}"
    )

    if reply_markup == "KEEP":
        if is_running and not stop_requested:
            markup = InlineKeyboardMarkup([[InlineKeyboardButton('🛑 STOP INDEXING', callback_data=f'yindex_stop:{session_id}')]])
        else:
            markup = None
    else:
        markup = reply_markup

    progress_msg = session.get("progress_msg")
    chat_id = session.get("progress_chat_id")
    message_id = session.get("progress_message_id")

    session["last_progress_update"] = now
    session["last_scanned_update"] = scanned

    try:
        if progress_msg and hasattr(progress_msg, "edit_text"):
            await progress_msg.edit_text(text, reply_markup=markup)
        elif bot and chat_id and message_id:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.debug(f"[YINDEX UPDATE PROGRESS ERROR] session={session_id} error={e}")


@Client.on_callback_query(filters.regex(r'^(yindex_stop|yindex_cancel)'))
async def yindex_stop_callback(bot, query):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        try:
            return await query.answer("⚠️ You are not allowed to stop this indexing task.", show_alert=True)
        except Exception:
            return
    
    raw_data = query.data
    if ":" in raw_data:
        session_id = raw_data.split(":", 1)[1].strip()
    elif "#" in raw_data:
        session_id = raw_data.split("#", 1)[1].strip()
    else:
        session_id = ""

    sessions = getattr(temp, "YINDEX_SESSIONS", {})
    session = sessions.get(session_id)
    
    # Fallback to search by admin_id if legacy session_id passed
    if not session and session_id.isdigit():
        for s in sessions.values():
            if s.get("admin_id") == int(session_id) and s.get("is_running"):
                session = s
                break

    if not session or not session.get("is_running"):
        try:
            return await query.answer("ℹ️ This indexing task is no longer running.", show_alert=False)
        except Exception:
            return

    if session.get("admin_id") != user_id and user_id not in ADMINS:
        try:
            return await query.answer("⚠️ You are not allowed to stop this indexing task.", show_alert=True)
        except Exception:
            return

    if session.get("stop_requested"):
        logger.info(f"[YINDEX] STOP ALREADY REQUESTED session={session.get('session_id')}")
        try:
            return await query.answer("Stop already requested. Waiting for safe exit...", show_alert=False)
        except Exception:
            return

    # Set cancellation flag BEFORE answering callback
    session["stop_requested"] = True
    actual_session_id = session.get("session_id", session_id)
    logger.info(f"[YINDEX] STOP REQUESTED session={actual_session_id}")

    try:
        await query.answer("Stopping Year Indexing... 🛑", show_alert=False)
    except Exception as e:
        logger.warning(f"[YINDEX] STOP CALLBACK ANSWER FAILED: {e}")

    # Immediately edit message to show Stopping... and remove STOP button
    try:
        await update_yindex_progress(
            actual_session_id,
            bot=bot,
            force=True,
            status_override="🟡 Stopping...",
            reply_markup=None
        )
    except Exception as e:
        logger.warning(f"[YINDEX] STOP PROGRESS EDIT FAILED: {e}")


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
    if not hasattr(temp, "YINDEX_SESSIONS") or not isinstance(temp.YINDEX_SESSIONS, dict):
        temp.YINDEX_SESSIONS = {}
    
    active_sessions = [
        s for s in temp.YINDEX_SESSIONS.values()
        if s.get("admin_id") == user_id and s.get("is_running")
    ]
    if active_sessions:
        return await message.reply(
            "⚠️ A Year Indexing task is already running.\n"
            "Please stop the current task before starting another one."
        )

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

    # Generate unique session ID
    session_id = f"{user_id}_{int(time.time())}"
    session = {
        "session_id": session_id,
        "admin_id": user_id,
        "year": target_year,
        "chat_id": resolved_chat_id,
        "stop_requested": False,
        "is_running": True,
        "scanned": 0,
        "matching": 0,
        "indexed": 0,
        "already_indexed": 0,
        "skipped": 0,
        "failed": 0,
        "created_at": time.time(),
        "last_progress_update": time.monotonic(),
        "last_scanned_update": 0,
    }
    temp.YINDEX_SESSIONS[session_id] = session

    # Initialize Start Indexing Progress Message
    stop_btn = InlineKeyboardMarkup([[InlineKeyboardButton('🛑 STOP INDEXING', callback_data=f'yindex_stop:{session_id}')]])
    progress_msg = await vj.reply_text(
        f"📅 <b>Year Indexing Started</b>\n\n"
        f"<b>Year:</b> <code>{target_year}</code>\n\n"
        f"<b>Scanned:</b> <code>0</code>\n"
        f"<b>Matching Files:</b> <code>0</code>\n"
        f"<b>Indexed:</b> <code>0</code>\n"
        f"<b>Already Indexed:</b> <code>0</code>\n"
        f"<b>Skipped:</b> <code>0</code>\n"
        f"<b>Failed:</b> <code>0</code>\n\n"
        f"<b>Status:</b> 🟢 Indexing...",
        reply_markup=stop_btn
    )

    session["progress_chat_id"] = progress_msg.chat.id
    session["progress_message_id"] = progress_msg.id
    session["progress_msg"] = progress_msg

    # Run Year Indexing
    await year_index_files_to_db(
        session=session,
        chat=resolved_chat_id,
        lst_msg_id=last_msg_id or 1000000,
        msg=progress_msg,
        bot=bot
    )


async def year_index_files_to_db(session: dict, chat, lst_msg_id: int, msg, bot, admin_id: int = None):
    """
    Scans the source channel and indexes only files matching the target year.
    Supports real-time throttled progress updates and safe cooperative STOP via session["stop_requested"].
    """
    if isinstance(session, int):
        # Backward compatibility if target_year passed as first arg
        target_year = session
        admin_uid = admin_id or 0
        session_id = f"{admin_uid}_{int(time.time())}"
        session = {
            "session_id": session_id,
            "admin_id": admin_uid,
            "year": target_year,
            "chat_id": chat,
            "stop_requested": False,
            "is_running": True,
            "scanned": 0,
            "matching": 0,
            "indexed": 0,
            "already_indexed": 0,
            "skipped": 0,
            "failed": 0,
            "created_at": time.time(),
            "last_progress_update": time.monotonic(),
            "last_scanned_update": 0,
            "progress_msg": msg,
            "progress_chat_id": getattr(getattr(msg, "chat", None), "id", None),
            "progress_message_id": getattr(msg, "id", None),
        }
        if not hasattr(temp, "YINDEX_SESSIONS") or not isinstance(temp.YINDEX_SESSIONS, dict):
            temp.YINDEX_SESSIONS = {}
        temp.YINDEX_SESSIONS[session_id] = session
    else:
        session_id = session.get("session_id")
        target_year = session.get("year")
        admin_uid = session.get("admin_id")
        session["progress_msg"] = msg
        session["progress_chat_id"] = getattr(getattr(msg, "chat", None), "id", None)
        session["progress_message_id"] = getattr(msg, "id", None)

    logger.info(f"[YINDEX] START session={session_id} year={target_year} channel={chat}")
    set_wizard_session(admin_uid, "YINDEX", "YINDEX_RUNNING", {"session_id": session_id, "year": target_year, "chat_id": chat})

    batch_size = 200
    current = temp.CURRENT if getattr(temp, 'CURRENT', 1) > 0 else 1
    interrupted_reason = None
    empty_batches_count = 0
    max_empty_batches = 2

    async def fetch_batch(b_ids):
        if not b_ids:
            return []
        for attempt in range(3):
            if session.get("stop_requested"):
                return None
            try:
                return await bot.get_messages(chat, b_ids)
            except FloodWait as e:
                logger.warning(f"[YINDEX FLOODWAIT] session={session_id} Sleeping {e.value}s")
                await asyncio.sleep(e.value)
            except Exception as ge:
                logger.warning(f"[YINDEX GET_MESSAGES RETRY] session={session_id} Attempt {attempt + 1}/3 for batch {b_ids[0]}-{b_ids[-1]}: {ge}")
                await asyncio.sleep(2 * (attempt + 1))
        return None

    # Start fetching initial batch
    initial_end = min(current + batch_size, lst_msg_id + 1)
    initial_ids = list(range(current, initial_end))
    prefetch_task = asyncio.create_task(fetch_batch(initial_ids)) if initial_ids else None

    try:
        while True:
            if session.get("stop_requested") or not prefetch_task:
                break

            messages = await prefetch_task
            prefetch_task = None

            if session.get("stop_requested"):
                break

            if messages is None:
                logger.error(f"[YINDEX] Failed to fetch batch starting at {current} after retries")
                interrupted_reason = "Telegram network error fetching channel messages."
                break

            # Schedule next batch prefetch immediately while current batch is processed in parallel
            next_current = current + batch_size
            if next_current <= lst_msg_id and not session.get("stop_requested"):
                next_end = min(next_current + batch_size, lst_msg_id + 1)
                next_ids = list(range(next_current, next_end))
                if next_ids:
                    prefetch_task = asyncio.create_task(fetch_batch(next_ids))

            # Check if entire batch is empty and we've reached or passed lst_msg_id
            if all(getattr(m, 'empty', True) for m in messages):
                empty_batches_count += 1
                if current >= lst_msg_id and empty_batches_count >= max_empty_batches:
                    break
            else:
                empty_batches_count = 0

            for message in messages:
                if session.get("stop_requested"):
                    break

                session["scanned"] += 1

                if getattr(message, 'empty', False):
                    session["skipped"] += 1
                    continue
                elif not message.media:
                    session["skipped"] += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    session["skipped"] += 1
                    continue

                media_type_attr = getattr(message.media, 'value', str(message.media))
                media = getattr(message, str(media_type_attr), None)
                if not media:
                    session["skipped"] += 1
                    continue

                media.caption = message.caption

                # Check if file/caption matches the requested year (sub-microsecond fast path)
                if not file_matches_year(media, message.caption, target_year):
                    session["skipped"] += 1
                    continue

                if session.get("stop_requested"):
                    break

                session["matching"] += 1

                try:
                    aynav, vnay = await save_file(media)
                    if aynav:
                        session["indexed"] += 1
                    elif vnay == 0:
                        session["already_indexed"] += 1
                    else:
                        session["failed"] += 1
                except Exception as fe:
                    logger.exception(f"[YINDEX SAVE ERROR] session={session_id} error={fe}")
                    session["failed"] += 1

                # Live progress update when matching file is indexed
                await update_yindex_progress(session_id, bot=bot)

            # Live progress update per batch
            await update_yindex_progress(session_id, bot=bot)

            if session.get("stop_requested"):
                break

            current += batch_size

    except Exception as e:
        logger.exception(f"[YINDEX FATAL ERROR] session={session_id} error={e}")
        interrupted_reason = str(e)

    finally:
        if prefetch_task and not prefetch_task.done():
            prefetch_task.cancel()
        session["is_running"] = False
        clear_wizard_session(admin_uid)

    # Final summary update (STOP button removed, final forced update)
    if session.get("stop_requested"):
        logger.info(f"[YINDEX] STOPPED session={session_id} scanned={session['scanned']} indexed={session['indexed']}")
        await update_yindex_progress(
            session_id,
            bot=bot,
            force=True,
            status_override="🔴 Stopped by admin",
            reply_markup=None
        )
    elif interrupted_reason:
        logger.error(f"[YINDEX] ERROR session={session_id} error={interrupted_reason}")
        await update_yindex_progress(
            session_id,
            bot=bot,
            force=True,
            status_override=f"<code>{interrupted_reason}</code>",
            reply_markup=None
        )
    else:
        logger.info(f"[YINDEX] COMPLETED session={session_id} scanned={session['scanned']} indexed={session['indexed']}")
        await update_yindex_progress(
            session_id,
            bot=bot,
            force=True,
            status_override="✅ Completed",
            reply_markup=None
        )


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
