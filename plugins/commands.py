# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os, string, logging, random, asyncio, time, datetime, re, sys, json, base64
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import *
from database.ia_filterdb import col, sec_col, get_file_details, unpack_new_file_id, get_bad_files
from database.users_chats_db import db, delete_all_referal_users, get_referal_users_count, get_referal_all_users, referal_add_user
from database.join_reqs import JoinReqs
from info import CLONE_MODE, OWNER_LNK, REACTIONS, CHANNELS, REQUEST_TO_JOIN_MODE, TRY_AGAIN_BTN, ADMINS, SHORTLINK_MODE, PREMIUM_AND_REFERAL_MODE, STREAM_MODE, AUTH_CHANNEL, REFERAL_PREMEIUM_TIME, REFERAL_COUNT, PAYMENT_TEXT, PAYMENT_QR, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, CHNL_LNK, GRP_LNK, REQST_CHANNEL, SUPPORT_CHAT, MAX_B_TN, VERIFY, SHORTLINK_API, SHORTLINK_URL, TUTORIAL, VERIFY_TUTORIAL, IS_TUTORIAL, URL
from utils import get_settings, pub_is_subscribed, get_size, is_subscribed, save_group_settings, temp, verify_user, check_token, check_verification, get_token, get_shortlink, get_tutorial, get_seconds
from database.connections_mdb import active_connection
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
logger = logging.getLogger(__name__)

BATCH_FILES = {}
join_db = JoinReqs



async def process_series_start(client: Client, user_id: int, req_key: str, message: Message = None):
    import utils
    from utils import temp
    import info
    import logging
    log = logging.getLogger(__name__)
    AUTH_CHANNEL = getattr(info, "AUTH_CHANNEL", None)
    
    log.info(f"[SERIES START]\naction=REQUEST_RECEIVED\nrequest_key={req_key}\nuser_id={user_id}")
    log.info(f"[SERIES START]\nrequest_key={req_key}\naction=REQUEST_RECEIVED")
    
    req = getattr(temp, "SERIES_STATE", {}).get(req_key)
    if not req:
        req = getattr(temp, "GETALL", {}).get(req_key)
    if not req:
        from database.series_db import get_temp_request
        req = await get_temp_request(req_key)
        if req:
            temp.SERIES_STATE[req_key] = req
            temp.GETALL[req_key] = req
            
    if not req:
        from plugins.series import to_series_font
        log.warning(f"[SERIES START]\naction=REQUEST_NOT_FOUND\nrequest_key={req_key}")
        msg_text = f"<b><i>⚠️ {to_series_font('Request expired. Please search the series again.')}</i></b>"
        if message:
            await message.reply(msg_text)
        else:
            await client.send_message(user_id, msg_text)
        return
        
    if req.get("type") == "movie" or req.get("request_type") == "movie":
        log.info(f"[MOVIE START TRACE] Delivering movie files for req_key={req_key}")
        if AUTH_CHANNEL:
            sub = await utils.is_subscribed(client, user_id)
            if not sub:
                log.info(f"[MOVIE START]\naction=MEMBERSHIP_CHECK\nresult=NOT_JOINED\nrequest_key={req_key}")
                if not req.get("join_message_id"):
                    try:
                        invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
                        text = (
                            "📢 **Channel Join Request**\n\n"
                            "ഫയലുകൾ ലഭിക്കുന്നതിന് മുമ്പ് ഞങ്ങളുടെ ചാനലിലേക്ക് Join Request അയയ്ക്കുക.\n\n"
                            "Request അയച്ച ശേഷം താഴെയുള്ള Try Again ബട്ടൺ ക്ലിക്ക് ചെയ്യുക.\n\n"
                            "Please send a Join Request to our channel before getting the files.\n\n"
                            "After sending the request, click Try Again below."
                        )
                        btn = [
                            [InlineKeyboardButton("📢 Send Join Request", url=invite_link.invite_link)],
                            [InlineKeyboardButton("🔄 Try Again", callback_data=f"checksub#series#{req_key}")]
                        ]
                        join_msg = await client.send_message(
                            chat_id=user_id,
                            text=text,
                            reply_markup=InlineKeyboardMarkup(btn),
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                        req["join_message_id"] = join_msg.id
                        from database.series_db import save_temp_request
                        await save_temp_request(req_key, req)
                    except Exception as e:
                        log.error(f"Failed to create join request: {e}")
                return
        
        req["delivery_status"] = "sending"
        files = req.get("files", [])
        await send_movie_files_to_user(
            client=client,
            user_id=user_id,
            files=files,
            movie_title=req.get("movie_title", req.get("title")),
            language=req.get("language"),
            quality=req.get("quality")
        )
        req["delivery_status"] = "completed"
        return

    full_id = req.get("full_id") or req.get("series_id")
    if full_id and len(str(full_id)) != 24:
        from plugins.series import _get_full_id
        full_id = await _get_full_id(str(full_id))
        if full_id:
            req["full_id"] = full_id
            req["series_id"] = full_id

    log.info(
        f"[SERIES START TRACE]\n"
        f"request_key={req_key}\n"
        f"user_id={user_id}\n"
        f"sid={req.get('sid')}\n"
        f"full_id={full_id}\n"
        f"language={req.get('language')}\n"
        f"season={req.get('season')}\n"
        f"quality={req.get('quality')}"
    )

    owner = req.get("user_id", req.get("user"))
    if owner and int(owner) != int(user_id):
        from plugins.series import to_series_font
        log.warning(f"[SERIES START]\naction=OWNERSHIP_MISMATCH\nrequest_key={req_key}\nowner={owner}\nuser_id={user_id}")
        msg_text = f"<b><i>⚠️ {to_series_font('This link is not for you!')}</i></b>"
        if message:
            await message.reply(msg_text)
        else:
            await client.send_message(user_id, msg_text)
        return
        
    status = str(req.get("delivery_status", req.get("state", ""))).lower()
    if status == "completed":
        from plugins.series import to_series_font
        if message:
            await message.reply(f"✅ {to_series_font('Files already sent.')}")
        return
    if status == "sending":
        from plugins.series import to_series_font
        if message:
            await message.reply(f"⏳ {to_series_font('Files are already being sent.')}")
        return
        
    if AUTH_CHANNEL:
        sub = await utils.is_subscribed(client, user_id)
        if not sub:
            log.info(f"[SERIES START]\naction=MEMBERSHIP_CHECK\nresult=NOT_JOINED\nrequest_key={req_key}")
            log.info(f"[SERIES START]\nmembership=NOT_JOINED")
            
            # Send exactly ONE Join Request message if not already pending
            if not req.get("join_message_id"):
                try:
                    invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
                    text = (
                        "📢 **Channel Join Request**\n\n"
                        "ഫയലുകൾ ലഭിക്കുന്നതിന് മുമ്പ് ഞങ്ങളുടെ ചാനലിലേക്ക് Join Request അയയ്ക്കുക.\n\n"
                        "Request അയച്ച ശേഷം താഴെയുള്ള Try Again ബട്ടൺ ക്ലിക്ക് ചെയ്യുക.\n\n"
                        "Please send a Join Request to our channel before getting the files.\n\n"
                        "After sending the request, click Try Again below."
                    )
                    btn = [
                        [InlineKeyboardButton("📢 Send Join Request", url=invite_link.invite_link)],
                        [InlineKeyboardButton("🔄 Try Again", callback_data=f"checksub#series#{req_key}")]
                    ]
                    join_msg = await client.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=InlineKeyboardMarkup(btn),
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                    req["join_message_id"] = join_msg.id
                    from database.series_db import save_temp_request
                    await save_temp_request(req_key, req)
                    log.info(f"[JOIN REQUEST]\nrequest_key={req_key}\naction=CREATED\nmessage_id={join_msg.id}")
                except Exception as e:
                    log.error(f"Failed to create join request: {e}")
            return
        else:
            log.info(f"[SERIES START]\naction=MEMBERSHIP_CHECK\nresult=JOINED\nrequest_key={req_key}")
            log.info(f"[SERIES START]\nmembership=JOINED")
            
    from plugins.series import deliver_series_request
    import time
    timing_dict = {
        "start": time.perf_counter(),
        "received": time.perf_counter(),
        "loaded": time.perf_counter(),
        "membership": time.perf_counter()
    }
    await deliver_series_request(client, req_key, user_id, query=None, timing=timing_dict)



@Client.on_message(filters.command("start") & filters.incoming, group=-10)
async def start(client, message):
    import logging
    log = logging.getLogger(__name__)
    
    payload = message.command[1] if len(message.command) > 1 else ""
    log.info(f"[START HANDLER]\npayload={payload}")
    log.info(f"[DEBUG START] Raw text: {message.text}")
    
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup, disable_web_page_preview=True)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        if PREMIUM_AND_REFERAL_MODE == True:
            buttons = [[
                InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
            ]]
        else:
            buttons = [[
                InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
            ]]
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('ᴄʀᴇᴀᴛᴇ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        m=await message.reply_sticker("CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ") 
        await asyncio.sleep(1)
        await m.delete()
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    data = message.command[1]

    if data.startswith("fsub_"):
        req_id = data.split("_", 1)[1]
        req = temp.GROUP_MOVIE_REQS.get(req_id)
        if not req:
            return await message.reply("<b><i>Sorry, this request has expired. Please search again.</b></i>")
        if message.from_user.id != req["user"]:
            return await message.reply("<b><i>⚠️ This request is not for you!</b></i>")
            
        import logging
        logging.getLogger(__name__).info(f"[GROUP MOVIE] SHOW JOIN REQUEST")
        
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
        except Exception as e:
            await message.reply_text("Make sure Bot is admin in Forcesub channel")
            return
            
        text = (
            "📢 **Channel Join Request**\n\n"
            "ഫയൽ ലഭിക്കുന്നതിന് മുമ്പ് ഞങ്ങളുടെ ചാനലിലേക്ക് Join Request അയയ്ക്കുക.\n\n"
            "Request അയച്ച ശേഷം താഴെയുള്ള Try Again ബട്ടൺ ക്ലിക്ക് ചെയ്യുക.\n\n"
            "Please send a Join Request to our channel before getting the file.\n\n"
            "After sending the request, click Try Again below."
        )
        btn = [
            [InlineKeyboardButton("📢 Send Join Request", url=invite_link.invite_link)],
            [InlineKeyboardButton("🔄 Try Again", callback_data=f"checksub#movie#{req_id}")]
        ]
        await client.send_message(
            chat_id=message.from_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
        
    # --- SERIES GROUP TO PM FLOW ---
    if data.startswith("all_"):
        file_id = data.split("_", 1)[1]
        await process_series_start(client, message.from_user.id, file_id, message=message)
        return
    # --- END SERIES GROUP TO PM FLOW ---

    # --- SERIES & MOVIE DEEP LINK PM FLOW ---
    if data.startswith("series_"):
        series_key = data.split("_", 1)[1]
        from plugins.series import process_series_deeplink
        await process_series_deeplink(client, message, series_key)
        return

    if data.startswith("movie_") or data.startswith("smovie_"):
        movie_key = data.split("_", 1)[1]
        from plugins.series import process_movie_deeplink
        await process_movie_deeplink(client, message, movie_key)
        return
    # --- END SERIES & MOVIE DEEP LINK PM FLOW ---
    
    # Global Force Subscribe Check
    if AUTH_CHANNEL and (message.from_user.id not in ADMINS):
        if not await is_subscribed(client, message.from_user.id):
            try:
                invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL), creates_join_request=True)
            except Exception as e:
                log.error(f"Failed to create invite link for AUTH_CHANNEL: {e}")
                invite_link = None

            if invite_link:
                req_cmd = data if len(message.command) > 1 else ""
                text = (
                    "📢 **Channel Join Request**\n\n"
                    "ഫയൽ ലഭിക്കുന്നതിന് മുമ്പ് ഞങ്ങളുടെ ചാനലിലേക്ക് Join Request അയയ്ക്കുക.\n\n"
                    "Request അയച്ച ശേഷം താഴെയുള്ള Try Again ബട്ടൺ ക്ലിക്ക് ചെയ്യുക.\n\n"
                    "Please send a Join Request to our channel before getting the files.\n\n"
                    "After sending the request, click Try Again below."
                )
                btn = [
                    [InlineKeyboardButton("📢 Send Join Request", url=invite_link.invite_link)],
                    [InlineKeyboardButton("🔄 Try Again", callback_data=f"checksub#all#{req_cmd}" if req_cmd else f"checksub#main#0")]
                ]
                return await client.send_message(
                    chat_id=message.from_user.id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=enums.ParseMode.MARKDOWN
                )
    
    if data.split("-", 1)[0] == "VJ":
        user_id = int(data.split("-", 1)[1])
        vj = await referal_add_user(user_id, message.from_user.id)
        if vj and PREMIUM_AND_REFERAL_MODE == True:
            await message.reply(f"<b>You have joined using the referral link of user with ID {user_id}\n\nSend /start again to use the bot</b>")
            num_referrals = await get_referal_users_count(user_id)
            await client.send_message(chat_id = user_id, text = "<b>{} start the bot with your referral link\n\nTotal Referals - {}</b>".format(message.from_user.mention, num_referrals))
            if num_referrals == REFERAL_COUNT:
                time = REFERAL_PREMEIUM_TIME       
                seconds = await get_seconds(time)
                if seconds > 0:
                    expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                    user_data = {"id": user_id, "expiry_time": expiry_time} 
                    await db.update_user(user_data)  # Use the update_user method to update or insert user data
                    await delete_all_referal_users(user_id)
                    await client.send_message(chat_id = user_id, text = "<b>You Have Successfully Completed Total Referal.\n\nYou Added In Premium For {}</b>".format(REFERAL_PREMEIUM_TIME))
                    return 
        else:
            if PREMIUM_AND_REFERAL_MODE == True:
                buttons = [[
                    InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)
                ]]
            else:
                buttons = [[
                    InlineKeyboardButton("⚙️ 𝓑𝓞𝓣 𝓤𝓟𝓓𝓐𝓣𝓔 𝓒𝓗𝓐𝓝𝓝𝓔𝓛 ⚙️", url="https://t.me/+d8zuVyrBBcNkYzI1")
                ],[
                    InlineKeyboardButton("📂 𝓙𝓞𝓘𝓝 𝓕𝓞𝓡 𝓤𝓟𝓓𝓐𝓣𝓔 𝓒𝓗𝓐𝓝𝓝𝓔𝓛 📂", url="https://t.me/+rjw2I6MtjW8xYzRl")
                ],[
                    InlineKeyboardButton("🔰 𝓑𝓞𝓣 𝓐𝓑𝓞𝓤𝓣 𝓟𝓐𝓝𝓔𝓛 🔰", callback_data="about")
                ]]
            if CLONE_MODE == True:
                buttons.append([InlineKeyboardButton('ᴄʀᴇᴀᴛᴇ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
            reply_markup = InlineKeyboardMarkup(buttons)
            m=await message.reply_sticker("CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ") 
            await asyncio.sleep(1)
            await m.delete()
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return 
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    if data.split("-", 1)[0] in ["BATCH", "PBATCH"]:
        sts = await message.reply("<b>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        is_pbatch = data.split("-", 1)[0] == "PBATCH"
        identifier = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(identifier)
        if not msgs:
            try:
                # If identifier is an integer, it's a message ID in LOG_CHANNEL
                msg_id = int(identifier)
                post = await client.get_messages(LOG_CHANNEL, msg_id)
                if not post or not post.document:
                    await sts.edit("FAILED TO LOCATE BATCH DATA IN LOG_CHANNEL")
                    return
                file_id = post.document.file_id
            except ValueError:
                # Fallback to old raw file_id logic
                file_id = identifier

            try:
                file = await client.download_media(file_id)
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
                os.remove(file)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"BATCH DOWNLOAD ERROR: {e}")
                await sts.edit("FAILED TO DOWNLOAD BATCH DATA")
                return await client.send_message(LOG_CHANNEL, f"UNABLE TO OPEN FILE.\n{e}")
            BATCH_FILES[identifier] = msgs

        def batch_files_caption_builder(msg_doc, idx, total_count):
            title = msg_doc.get("title")
            size = get_size(int(msg_doc.get("size", 0)))
            f_caption = msg_doc.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception:
                    pass
            if not f_caption:
                f_caption = f"{title}" if title else ""
            return f_caption

        try:
            await sts.delete()
        except Exception:
            pass

        sent_messages = await send_batch_files(
            client=client,
            chat_id=message.from_user.id,
            files=msgs,
            user_id=message.from_user.id,
            custom_caption_builder=batch_files_caption_builder
        )

        if sent_messages:
            try:
                k = await client.send_message(
                    chat_id=message.from_user.id,
                    text="<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.</i></b></blockquote>",
                    parse_mode=enums.ParseMode.HTML
                )
                from utils import schedule_filter_message_delete
                if k:
                    schedule_filter_message_delete(client, k.chat.id, k.id, 600)
            except Exception:
                pass
        return
    
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("<b>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        filesarr = []
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                file_type = msg.media
                file = getattr(msg, file_type.value)
                size = get_size(int(file.file_size))
                file_name = getattr(media, 'file_name', '')
                f_caption = getattr(msg, 'caption', file_name)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name=file_name, file_size='' if size is None else size, file_caption=f_caption)
                    except:
                        f_caption = getattr(msg, 'caption', '')
                file_id = file.file_id
                if STREAM_MODE == True:
                    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=file_id)
                    fileName = {quote_plus(get_name(log_msg))}
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
 
                if STREAM_MODE == True:
                    button = [[
                        InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                        InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
                    ],[
                        InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                    ]]
                    reply_markup = InlineKeyboardMarkup(button)
                else:
                    reply_markup = None
                try:
                    p = await msg.copy(message.chat.id, caption="", protect_content=True if protect == "/pbatch" else False, reply_markup=reply_markup)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    p = await msg.copy(message.chat.id, caption="", protect_content=True if protect == "/pbatch" else False, reply_markup=reply_markup)
                except:
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    p = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    p = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except:
                    continue
            filesarr.append(p)
            await asyncio.sleep(1)
        await sts.delete()
        k = await client.send_message(chat_id = message.from_user.id, text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.</i></b></blockquote>")
        await asyncio.sleep(600)
        for x in filesarr:
            await x.delete()
        await k.edit_text("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ</b>")
        return

    elif data.split("-", 1)[0] == "verify":
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(message.from_user.id) != str(userid):
            return await message.reply_text(text="<b>ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ ᴏʀ ᴇxᴘɪʀᴇᴅ ʟɪɴᴋ</b>", protect_content=True)
        is_valid = await check_token(client, userid, token)
        if is_valid == True:
            text = "<b>ʜᴇʏ {} 👋,\n\nʏᴏᴜ ʜᴀᴠᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ...\n\nɴᴏᴡ ʏᴏᴜ ʜᴀᴠᴇ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴛɪʟʟ ᴛᴏᴅᴀʏ ɴᴏᴡ ᴇɴᴊᴏʏ\n\n</b>"
            if PREMIUM_AND_REFERAL_MODE == True:
                text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"           
            await message.reply_text(text=text.format(message.from_user.mention), protect_content=True)
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(text="<b>ɪɴᴠᴀʟɪᴅ ʟɪɴᴋ ᴏʀ ᴇxᴘɪʀᴇᴅ ʟɪɴᴋ</b>", protect_content=True)
            
    if data.startswith("sendfiles"):
        chat_id = int("-" + file_id.split("-")[1])
        userid = message.from_user.id if message.from_user else None
        settings = await get_settings(chat_id)
        pre = 'allfilesp' if settings['file_secure'] else 'allfiles'
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
        btn = [[
            InlineKeyboardButton('ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ', url=g)
        ]]
        if settings['tutorial']:
            btn.append([InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
        text = "<b>✅ ʏᴏᴜʀ ғɪʟᴇ ʀᴇᴀᴅʏ ᴄʟɪᴄᴋ ᴏɴ ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ ʙᴜᴛᴛᴏɴ ᴛʜᴇɴ ᴏᴘᴇɴ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ғɪʟᴇ\n\n</b>"
        if PREMIUM_AND_REFERAL_MODE == True:
            text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴏᴘᴇɴɪɴɢ ʟɪɴᴋ ᴀɴᴅ ᴡᴀᴛᴄʜɪɴɢ ᴀᴅs ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
        k = await client.send_message(chat_id=message.from_user.id, text=text, reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(300)
        await k.edit("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ</b>")
        return
        
    
    elif data.startswith("short"):
        user = message.from_user.id
        chat_id = temp.SHORT.get(user)
        settings = await get_settings(chat_id)
        pre = 'filep' if settings['file_secure'] else 'file'
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
        btn = [[
            InlineKeyboardButton('ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ', url=g)
        ]]
        if settings['tutorial']:
            btn.append([InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
        text = "<b>✅ ʏᴏᴜʀ ғɪʟᴇ ʀᴇᴀᴅʏ ᴄʟɪᴄᴋ ᴏɴ ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ ʙᴜᴛᴛᴏɴ ᴛʜᴇɴ ᴏᴘᴇɴ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ғɪʟᴇ\n\n</b>"
        if PREMIUM_AND_REFERAL_MODE == True:
            text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴏᴘᴇɴɪɴɢ ʟɪɴᴋ ᴀɴᴅ ᴡᴀᴛᴄʜɪɴɢ ᴀᴅs ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
        k = await client.send_message(chat_id=user, text=text, reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(1200)
        await k.edit("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ</b>")
        return
        
    elif data.startswith("allfiles"):
        import logging
        log = logging.getLogger(__name__)
        # Check temp.GETALL first
        files = temp.GETALL.get(file_id)

        if not files:
            log.warning(f"[ALLFILES START] GETALL NOT FOUND file_id={file_id}")
            return

        # Verification check ONCE before batch sending
        if not await db.has_premium_access(message.from_user.id):
            if not await check_verification(client, message.from_user.id) and VERIFY == True:
                btn = [[
                    InlineKeyboardButton("ᴠᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))
                ],[
                    InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ", url=VERIFY_TUTORIAL)
                ]]
                text = "<b>ʜᴇʏ {} 👋,\n\nʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ, ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴏɴ ᴠᴇʀɪғʏ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ ғᴏʀ ᴛᴏᴅᴀʏ</b>"
                if PREMIUM_AND_REFERAL_MODE == True:
                    text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
                return await message.reply_text(
                    text=text.format(message.from_user.mention),
                    protect_content=True,
                    reply_markup=InlineKeyboardMarkup(btn)
                )

        protect_content = True if (hasattr(message, "command") and len(message.command) > 1 and message.command[1].startswith("allfilesp")) else False

        # Bulk preload file details in ONE query
        file_ids_list = [f["file_id"] for f in files if isinstance(f, dict) and "file_id" in f]
        from database.ia_filterdb import get_bulk_file_details
        bulk_map = await get_bulk_file_details(file_ids_list)

        def allfiles_caption_builder(f_doc, idx, total_count):
            title = f_doc.get("file_name")
            raw_sz = f_doc.get("file_size", 0)
            size = get_size(raw_sz) if raw_sz else "Unknown Size"
            f_caption = f_doc.get("caption", "")
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception:
                    pass
            if not f_caption:
                fname_str = f_doc.get('file_name', '')
                f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), fname_str.split()))}"
            return f_caption

        merged_files = []
        for f in files:
            fid = f.get("file_id") if isinstance(f, dict) else f
            if fid:
                f_doc = bulk_map.get(fid, {})
                merged = {**f_doc, **(f if isinstance(f, dict) else {"file_id": fid})}
                if STREAM_MODE:
                    button = [[InlineKeyboardButton('sᴛʀᴇᴀᴍ ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{fid}')]]
                    merged["reply_markup"] = InlineKeyboardMarkup(button)
                merged_files.append(merged)

        sent_messages = await send_batch_files(
            client=client,
            chat_id=message.from_user.id,
            files=merged_files,
            user_id=message.from_user.id,
            protect_content=protect_content,
            custom_caption_builder=allfiles_caption_builder
        )

        if sent_messages:
            try:
                k = await client.send_message(
                    chat_id=message.from_user.id,
                    text="<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.</i></b></blockquote>",
                    parse_mode=enums.ParseMode.HTML
                )
                from utils import schedule_filter_message_delete
                if k:
                    schedule_filter_message_delete(client, k.chat.id, k.id, 600)
            except Exception:
                pass
        return    
        
    elif data.startswith("files"):
        user = message.from_user.id
        if temp.SHORT.get(user)==None:
            await message.reply_text(text="<b>Please Search Again in Group</b>")
        else:
            chat_id = temp.SHORT.get(user)
        settings = await get_settings(chat_id)
        pre = 'filep' if settings['file_secure'] else 'file'
        if settings['is_shortlink'] and not await db.has_premium_access(user):
            g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
            btn = [[
                InlineKeyboardButton('ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ', url=g)
            ]]
            if settings['tutorial']:
                btn.append([InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
            text = "<b>✅ ʏᴏᴜʀ ғɪʟᴇ ʀᴇᴀᴅʏ ᴄʟɪᴄᴋ ᴏɴ ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏᴡ ʙᴜᴛᴛᴏɴ ᴛʜᴇɴ ᴏᴘᴇɴ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ғɪʟᴇ\n\n</b>"
            if PREMIUM_AND_REFERAL_MODE == True:
                text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴏᴘᴇɴɪɴɢ ʟɪɴᴋ ᴀɴᴅ ᴡᴀᴛᴄʜɪɴɢ ᴀᴅs ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
            k = await client.send_message(chat_id=message.from_user.id, text=text, reply_markup=InlineKeyboardMarkup(btn))
            await asyncio.sleep(1200)
            await k.edit("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ</b>")
            return
    user = message.from_user.id
    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
            if not await db.has_premium_access(message.from_user.id):
                if not await check_verification(client, message.from_user.id) and VERIFY == True:
                    btn = [[
                        InlineKeyboardButton("ᴠᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))
                    ],[
                        InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ", url=VERIFY_TUTORIAL)
                    ]]
                    text = "<b>ʜᴇʏ {} 👋,\n\nʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ, ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴏɴ ᴠᴇʀɪғʏ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ ғᴏʀ ᴛᴏᴅᴀʏ</b>"
                    if PREMIUM_AND_REFERAL_MODE == True:
                        text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
                    await message.reply_text(
                        text=text.format(message.from_user.mention),
                        protect_content=True,
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                    return
            if STREAM_MODE == True:
                button = [[InlineKeyboardButton('sᴛʀᴇᴀᴍ ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id}')]]
                reply_markup=InlineKeyboardMarkup(button)
            else:
                reply_markup = None
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
                reply_markup=reply_markup
            )
            filetype = msg.media
            file = getattr(msg, filetype.value)
            title = file.file_name
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            await msg.edit_caption(caption=f_caption)
            btn = [[InlineKeyboardButton("✅ ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ ✅", callback_data=f'del#{file_id}')]]
            k = await msg.reply(text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.</i></b></blockquote>")
            await asyncio.sleep(600)
            await msg.delete()
            await k.edit_text("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴀɢᴀɪɴ ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ</b>",reply_markup=InlineKeyboardMarkup(btn))
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_
    title = files["file_name"]
    size=get_size(files["file_size"])
    f_caption=files["caption"]
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except:
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files['file_name'].split()))}"
    if not await db.has_premium_access(message.from_user.id):
        if not await check_verification(client, message.from_user.id) and VERIFY == True:
            btn = [[
                InlineKeyboardButton("ᴠᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))
            ],[
                InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ", url=VERIFY_TUTORIAL)
            ]]
            text = "<b>ʜᴇʏ {} 👋,\n\nʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴅᴀʏ, ᴘʟᴇᴀꜱᴇ ᴄʟɪᴄᴋ ᴏɴ ᴠᴇʀɪғʏ & ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇꜱꜱ ғᴏʀ ᴛᴏᴅᴀʏ</b>"
            if PREMIUM_AND_REFERAL_MODE == True:
                text += "<b>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴅɪʀᴇᴄᴛ ғɪʟᴇꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴꜱ ᴛʜᴇɴ ʙᴜʏ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 ꜱᴇɴᴅ /plan ᴛᴏ ʙᴜʏ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ</b>"
            await message.reply_text(
                text=text.format(message.from_user.mention),
                protect_content=True,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return
    if STREAM_MODE == True:
        button = [[InlineKeyboardButton('sᴛʀᴇᴀᴍ ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id}')]]
        reply_markup=InlineKeyboardMarkup(button)
    else:
        reply_markup = None
    import logging
    log = logging.getLogger(__name__)
    
    try:
        log.info(f"[FILE SEND] request_id={file_id}")
        log.info(f"[FILE SEND] file_id={file_id}")
        msg = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if pre == 'filep' else False,
            reply_markup=reply_markup
        )
        log.info(f"[FILE SEND] SUCCESS request_id={file_id}")
    except Exception as e:
        log.error(f"[FILE SEND] ERROR: {e}")
        return await message.reply("Error sending file.")
        
    btn = [[InlineKeyboardButton("✅ ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ ✅", callback_data=f'del#{file_id}')]]
    k = await msg.reply(text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ᴏʀ ᴀɴʏ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ.</i></b></blockquote>")
    
    async def delete_file_later():
        await asyncio.sleep(600)
        try:
            await msg.delete()
        except:
            pass
        try:
            await k.edit_text("<b>✅ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴀɢᴀɪɴ ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ</b>",reply_markup=InlineKeyboardMarkup(btn))
        except:
            pass
            
    asyncio.create_task(delete_file_later())
    return   

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
    text = '📑 **Indexed channels/groups**\n'
    for channel in CHANNELS:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    try:
        await message.reply_document('TELEGRAM BOT.LOG')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    reply = await bot.ask(message.from_user.id, "Now Send Me Media Which You Want to delete")
    if reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Send Me Video, File Or Document.', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = col.delete_one({
        'file_id': file_id,
    })
    if not result.deleted_count:
        result = sec_col.delete_one({
            'file_id': file_id,
        })
    if result.deleted_count:
        await msg.edit('File is successfully deleted from database')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        unwanted_chars = ['[', ']', '(', ')']
        for char in unwanted_chars:
            file_name = file_name.replace(char, '')
        file_name = ' '.join(filter(lambda x: not x.startswith('@'), file_name.split()))
    
        result = col.delete_many({
            'file_name': file_name,
            'file_size': media.file_size
        })
        if not result.deleted_count:
            result = sec_col.delete_many({
                'file_name': file_name,
                'file_size': media.file_size
            })
        if result.deleted_count:
            await msg.edit('File is successfully deleted from database')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = col.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size
            })
            if not result.deleted_count:
                result = sec_col.delete_many({
                    'file_name': media.file_name,
                    'file_size': media.file_size
                })
            if result.deleted_count:
                await msg.edit('File is successfully deleted from database')
            else:
                await msg.edit('File not found in database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(text="YES", callback_data="autofilter_delete")
            ],[
                InlineKeyboardButton(text="CANCEL", callback_data="close_data")
            ]]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, query):
    col.drop()
    sec_col.drop()
    await query.answer('Piracy Is Crime')
    await query.message.edit('Succesfully Deleted All The Indexed Files.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return
    
    settings = await get_settings(grp_id)

    try:
        if settings['max_btn']:
            settings = await get_settings(grp_id)
    except KeyError:
    #    await save_group_settings(grp_id, 'fsub', None)
        await save_group_settings(grp_id, 'max_btn', False)
        settings = await get_settings(grp_id)
    if 'is_shortlink' not in settings.keys():
        await save_group_settings(grp_id, 'is_shortlink', False)
    else:
        pass

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Rᴇsᴜʟᴛ Pᴀɢᴇ',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["file_secure"] else '✘ Oғғ',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Iᴍᴅʙ',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["imdb"] else '✘ Oғғ',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Sᴘᴇʟʟ Cʜᴇᴄᴋ',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Wᴇʟᴄᴏᴍᴇ Msɢ',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["welcome"] else '✘ Oғғ',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '10 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Aᴜᴛᴏ-Fɪʟᴛᴇʀ',
                    callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ',
                    callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Mᴀx Bᴜᴛᴛᴏɴs',
                    callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '10' if settings["max_btn"] else f'{MAX_B_TN}',
                    callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'ShortLink',
                    callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ',
                    callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{grp_id}',
                ),
            ],
        ]
        btn = [[
            InlineKeyboardButton("Oᴘᴇɴ Hᴇʀᴇ ↓", callback_data=f"opnsetgrp#{grp_id}"),
            InlineKeyboardButton("Oᴘᴇɴ Iɴ PM ⇲", callback_data=f"opnsetpm#{grp_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply_text(
                text="<b>Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs ʜᴇʀᴇ ?</b>",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )
        else:
            await message.reply_text(
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input!!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")


@Client.on_message((filters.command(["request", "Request"]) | filters.regex("#request") | filters.regex("#Request")) & filters.group)
async def requests(bot, message):
    if REQST_CHANNEL is None: return # Must add REQST_CHANNEL to use this feature
    if message.reply_to_message:
        chat_id = message.chat.id
        reporter = str(message.from_user.id)
        mention = message.from_user.mention
        success = True
        content = message.reply_to_message.text
        try:
            if REQST_CHANNEL is not None:
                btn = [[
                    InlineKeyboardButton('View Request', url=f"{message.reply_to_message.link}"),
                    InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                ]]
                reported_post = await bot.send_message(chat_id=REQST_CHANNEL, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                success = True
            elif len(content) >= 3:
                for admin in ADMINS:
                    btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.reply_to_message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                    ]]
                    reported_post = await bot.send_message(chat_id=admin, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                    success = True
            else:
                if len(content) < 3:
                    await message.reply_text("<b>You must type about your request [Minimum 3 Characters]. Requests can't be empty.</b>")
            if len(content) < 3:
                success = False
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            pass
        
    elif message.text:
        chat_id = message.chat.id
        reporter = str(message.from_user.id)
        mention = message.from_user.mention
        success = True
        content = message.text
        keywords = ["#request", "/request", "#Request", "/Request"]
        for keyword in keywords:
            if keyword in content:
                content = content.replace(keyword, "")
        try:
            if REQST_CHANNEL is not None and len(content) >= 3:
                btn = [[
                    InlineKeyboardButton('View Request', url=f"{message.link}"),
                    InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                ]]
                reported_post = await bot.send_message(chat_id=REQST_CHANNEL, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                success = True
            elif len(content) >= 3:
                for admin in ADMINS:
                    btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                    ]]
                    reported_post = await bot.send_message(chat_id=admin, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                    success = True
            else:
                if len(content) < 3:
                    await message.reply_text("<b>You must type about your request [Minimum 3 Characters]. Requests can't be empty.</b>")
            if len(content) < 3:
                success = False
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            pass

    else:
        success = False
    
    if success:
        link = await bot.create_chat_invite_link(int(REQST_CHANNEL))
        btn = [[
            InlineKeyboardButton('Join Channel', url=link.invite_link),
            InlineKeyboardButton('View Request', url=f"{reported_post.link}")
        ]]
        await message.reply_text("<b>Your request has been added! Please wait for some time.\n\nJoin Channel First & View Request</b>", reply_markup=InlineKeyboardMarkup(btn))
    
@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if message.reply_to_message:
        target_id = message.text.split(" ", 1)[1]
        out = "Users Saved In DB Are:\n\n"
        success = False
        try:
            user = await bot.get_users(target_id)
            users = await db.get_all_users()
            async for usr in users:
                out += f"{usr['id']}"
                out += '\n'
            if str(user.id) in str(out):
                await message.reply_to_message.copy(int(user.id))
                success = True
            else:
                success = False
            if success:
                await message.reply_text(f"<b>Your message has been successfully send to {user.mention}.</b>")
            else:
                await message.reply_text("<b>This user didn't started this bot yet !</b>")
        except Exception as e:
            await message.reply_text(f"<b>Error: {e}</b>")
    else:
        await message.reply_text("<b>Use this command as a reply to any message using the target chat id. For eg: /send userid</b>")

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This command won't work in groups. It only works on my PM !</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, Give me a keyword along with the command to delete files.</b>")
    k = await bot.send_message(chat_id=message.chat.id, text=f"<b>Fetching Files for your query {keyword} on DB... Please wait...</b>")
    files, total = await get_bad_files(keyword)
    await k.delete()
    #await k.edit_text(f"<b>Found {total} files for your query {keyword} !\n\nFile deletion process will start in 5 seconds !</b>")
    #await asyncio.sleep(5)
    btn = [[
       InlineKeyboardButton("Yes, Continue !", callback_data=f"killfilesdq#{keyword}")
    ],[
       InlineKeyboardButton("No, Abort operation !", callback_data="close_data")
    ]]
    await message.reply_text(
        text=f"<b>Found {total} files for your query {keyword} !\n\nDo you want to delete?</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("shortlink"))
async def shortlink(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This command only works on groups !\n\n<u>Follow These Steps to Connect Shortener:</u>\n\n1. Add Me in Your Group with Full Admin Rights\n\n2. After Adding in Grp, Set your Shortener\n\nSend this command in your group\n\n—> /shortlink ""{your_shortener_website_name} {your_shortener_api}\n\n#Sample:-\n/shortlink kpslink.in CAACAgUAAxkBAAEJ4GtkyPgEzpIUC_DSmirN6eFWp4KInAACsQoAAoHSSFYub2D15dGHfy8E\n\nThat's it!!! Enjoy Earning Money 💲\n\n[[[ Trusted Earning Site - https://kpslink.in]]]\n\nIf you have any Doubts, Feel Free to Ask me - @kingvj01\n\n(Puriyala na intha contact la message pannunga - @kngvj01)</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    data = message.text
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>You don't have access to use this command!\n\nAdd Me to Your Own Group as Admin and Try This Command\n\nFor More PM Me With This Command</b>")
    else:
        pass
    try:
        command, shortlink_url, api = data.split(" ")
    except:
        return await message.reply_text("<b>Command Incomplete :(\n\nGive me a shortener website link and api along with the command !\n\nFormat: <code>/shortlink kpslink.in e3d82cdf8f9f4783c42170b515d1c271fb1c4500</code></b>")
    reply = await message.reply_text("<b>Please Wait...</b>")
    shortlink_url = re.sub(r"https?://?", "", shortlink_url)
    shortlink_url = re.sub(r"[:/]", "", shortlink_url)
    await save_group_settings(grpid, 'shortlink', shortlink_url)
    await save_group_settings(grpid, 'shortlink_api', api)
    await save_group_settings(grpid, 'is_shortlink', True)
    await reply.edit_text(f"<b>Successfully added shortlink API for {title}.\n\nCurrent Shortlink Website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code></b>")
    
@Client.on_message(filters.command("setshortlinkoff"))
async def offshortlink(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("I will Work Only in group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>You don't have access to use this command!\n\nAdd Me to Your Own Group as Admin and Try This Command\n\nFor More PM Me With This Command</b>")
    else:
        pass
    await save_group_settings(grpid, 'is_shortlink', False)
    # ENABLE_SHORTLINK = False
    return await message.reply_text("Successfully disabled shortlink")
    
@Client.on_message(filters.command("setshortlinkon"))
async def onshortlink(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("I will Work Only in group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>You don't have access to use this command!\n\nAdd Me to Your Own Group as Admin and Try This Command\n\nFor More PM Me With This Command</b>")
    else:
        pass
    settings = await get_settings(grpid)
    if not settings['shortlink']:
        return await message.reply_text("**First Add Your Shortlink Url And Api By /shortlink Command, Then Turn Me On.**")
    await save_group_settings(grpid, 'is_shortlink', True)
    # ENABLE_SHORTLINK = True
    return await message.reply_text("Successfully enabled shortlink")

@Client.on_message(filters.command("shortlink_info"))
async def showshortlink(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This Command Only Works in Group\n\nTry this command in your own group, if you are using me in your group</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    chat_id=message.chat.id
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>Tʜɪs ᴄᴏᴍᴍᴀɴᴅ Wᴏʀᴋs Oɴʟʏ Fᴏʀ ᴛʜɪs Gʀᴏᴜᴘ Oᴡɴᴇʀ/Aᴅᴍɪɴ\n\nTʀʏ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ʏᴏᴜʀ Oᴡɴ Gʀᴏᴜᴘ, Iғ Yᴏᴜ Aʀᴇ Usɪɴɢ Mᴇ Iɴ Yᴏᴜʀ Gʀᴏᴜᴘ</b>")
    else:
        settings = await get_settings(chat_id) #fetching settings for group
        if 'shortlink' in settings.keys() and 'tutorial' in settings.keys():
            su = settings['shortlink']
            sa = settings['shortlink_api']
            st = settings['tutorial']
            return await message.reply_text(f"<b>Shortlink Website: <code>{su}</code>\n\nApi: <code>{sa}</code>\n\nTutorial: <code>{st}</code></b>")
        elif 'shortlink' in settings.keys() and 'tutorial' not in settings.keys():
            su = settings['shortlink']
            sa = settings['shortlink_api']
            return await message.reply_text(f"<b>Shortener Website: <code>{su}</code>\n\nApi: <code>{sa}</code>\n\nTutorial Link Not Connected\n\nYou can Connect Using /set_tutorial command</b>")
        elif 'shortlink' not in settings.keys() and 'tutorial' in settings.keys():
            st = settings['tutorial']
            return await message.reply_text(f"<b>Tutorial: <code>{st}</code>\n\nShortener Url Not Connected\n\nYou can Connect Using /shortlink command</b>")
        else:
            return await message.reply_text("Shortener url and Tutorial Link Not Connected. Check this commands, /shortlink and /set_tutorial")
        

@Client.on_message(filters.command("set_tutorial"))
async def settutorial(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("This Command Work Only in group\n\nTry it in your own group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    if len(message.command) == 1:
        return await message.reply("<b>Give me a tutorial link along with this command\n\nCommand Usage: /set_tutorial your tutorial link</b>")
    elif len(message.command) == 2:
        reply = await message.reply_text("<b>Please Wait...</b>")
        tutorial = message.command[1]
        await save_group_settings(grpid, 'tutorial', tutorial)
        await save_group_settings(grpid, 'is_tutorial', True)
        await reply.edit_text(f"<b>Successfully Added Tutorial\n\nHere is your tutorial link for your group {title} - <code>{tutorial}</code></b>")
    else:
        return await message.reply("<b>You entered Incorrect Format\n\nFormat: /set_tutorial your tutorial link</b>")

@Client.on_message(filters.command("remove_tutorial"))
async def removetutorial(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("This Command Work Only in group\n\nTry it in your own group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    reply = await message.reply_text("<b>Please Wait...</b>")
    await save_group_settings(grpid, 'tutorial', "")
    await save_group_settings(grpid, 'is_tutorial', False)
    await reply.edit_text(f"<b>Successfully Removed Your Tutorial Link!!!</b>")

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def stop_button(bot, message):
    msg = await bot.send_message(text="**🔄 𝙿𝚁𝙾𝙲𝙴𝚂𝚂𝙴𝚂 𝚂𝚃𝙾𝙿𝙴𝙳. 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙸𝙽𝙶...**", chat_id=message.chat.id)       
    import sys
    import os
    import asyncio
    await asyncio.sleep(3)
    await msg.edit("**✅️ 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙴𝙳. 𝙽𝙾𝚆 𝚈𝙾𝚄 𝙲𝙰𝙽 𝚄𝚂𝙴 𝙼𝙴**")
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("nofsub"))
async def nofsub(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"<b>You are anonymous admin. Turn off anonymous admin and try again this command</b>")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("<b>This Command Work Only in group\n\nTry it in your own group</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await client.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    await save_group_settings(grpid, 'fsub', None)
    await message.reply_text(f"<b>Successfully removed force subscribe from {title}.</b>")

@Client.on_message(filters.command('fsub'))
async def fsub(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"<b>You are anonymous admin. Turn off anonymous admin and try again this command</b>")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("<b>This Command Work Only in group\n\nTry it in your own group</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await client.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    try:
        ids = message.text.split(" ", 1)[1]
        fsub_ids = [int(id) for id in ids.split()]
    except IndexError:
        return await message.reply_text("<b>Command Incomplete!\n\nAdd Multiple Channel By Seperate Space. Like: /fsub id1 id2 id3</b>")
    except ValueError:
        return await message.reply_text('<b>Make Sure Ids are Integer.</b>')        
    channels = "Channels:\n"
    for id in fsub_ids:
        try:
            chat = await client.get_chat(id)
        except Exception as e:
            await message.reply_text(f"<b>Bot is not an admin in {id} or channel is private.</b>")
            return
        channels += f"{chat.title}\n"
    await save_group_settings(grpid, 'fsub', fsub_ids)
    await message.reply_text(f"<b>Successfully added force subscribe in {title}\n\n{channels}</b>")

@Client.on_message(filters.command("add_premium"))
async def add_premium_cmd_handler(client, message):
    if PREMIUM_AND_REFERAL_MODE == False:
        return 
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    if len(message.command) == 3:
        user_id = int(message.command[1])  # Convert the user_id to integer
        time = message.command[2]        
        seconds = await get_seconds(time)
        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            user_data = {"id": user_id, "expiry_time": expiry_time}  # Using "id" instead of "user_id"
            await db.update_user(user_data)  # Use the update_user method to update or insert user data
            await message.reply_text("Premium access added to the user.")            
            await client.send_message(
                chat_id=user_id,
                text=f"<b>ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ꜰᴏʀ {time} ᴇɴᴊᴏʏ 😀\n</b>",                
            )
        else:
            await message.reply_text("Invalid time format. Please use '1day for days', '1hour for hours', or '1min for minutes', or '1month for months' or '1year for year'")
    else:
        await message.reply_text("<b>Usage: /add_premium user_id time \n\nExample /add_premium 1252789 10day \n\n(e.g. for time units '1day for days', '1hour for hours', or '1min for minutes', or '1month for months' or '1year for year')</b>")
        
@Client.on_message(filters.command("remove_premium"))
async def remove_premium_cmd_handler(client, message):
    if PREMIUM_AND_REFERAL_MODE == False:
        return 
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    if len(message.command) == 2:
        user_id = int(message.command[1])  # Convert the user_id to integer
      #  time = message.command[2]
        time = "1s"
        seconds = await get_seconds(time)
        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            user_data = {"id": user_id, "expiry_time": expiry_time}  # Using "id" instead of "user_id"
            await db.update_user(user_data)  # Use the update_user method to update or insert user data
            await message.reply_text("Premium access removed to the user.")
            await client.send_message(
                chat_id=user_id,
                text="<b>premium removed by admins \n\n Contact Admin if this is mistake \n\n 👮 Admin : {} \n</b>".format(OWNER_LNK),                
            )
        else:
            await message.reply_text("Invalid time format.'")
    else:
        await message.reply_text("Usage: /remove_premium user_id")
        
@Client.on_message(filters.command("plan"))
async def plans_cmd_handler(client, message): 
    if PREMIUM_AND_REFERAL_MODE == False:
        return 
    btn = [            
        [InlineKeyboardButton("ꜱᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ 🧾", url=OWNER_LNK)],
        [InlineKeyboardButton("⚠️ ᴄʟᴏsᴇ / ᴅᴇʟᴇᴛᴇ ⚠️", callback_data="close_data")]
    ]
    reply_markup = InlineKeyboardMarkup(btn)
    await message.reply_photo(
        photo=PAYMENT_QR,
        caption=PAYMENT_TEXT,
        reply_markup=reply_markup
    )
        
@Client.on_message(filters.command("myplan"))
async def check_plans_cmd(client, message):
    if PREMIUM_AND_REFERAL_MODE == False:
        return 
    user_id  = message.from_user.id
    if await db.has_premium_access(user_id):         
        remaining_time = await db.check_remaining_uasge(user_id)             
        expiry_time = remaining_time + datetime.datetime.now()
        await message.reply_text(f"**Your plans details are :\n\nRemaining Time : {remaining_time}\n\nExpirytime : {expiry_time}**")
    else:
        btn = [ 
            [InlineKeyboardButton("ɢᴇᴛ ғʀᴇᴇ ᴛʀᴀɪʟ ғᴏʀ 𝟻 ᴍɪɴᴜᴛᴇꜱ ☺️", callback_data="get_trail")],
            [InlineKeyboardButton("ʙᴜʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴ : ʀᴇᴍᴏᴠᴇ ᴀᴅs", callback_data="buy_premium")],
            [InlineKeyboardButton("⚠️ ᴄʟᴏsᴇ / ᴅᴇʟᴇᴛᴇ ⚠️", callback_data="close_data")]
        ]
        reply_markup = InlineKeyboardMarkup(btn)
        m=await message.reply_sticker("CAACAgIAAxkBAAIBTGVjQbHuhOiboQsDm35brLGyLQ28AAJ-GgACglXYSXgCrotQHjibHgQ")         
        await message.reply_text(f"**😢 You Don't Have Any Premium Subscription.\n\n Check Out Our Premium /plan**",reply_markup=reply_markup)
        await asyncio.sleep(2)
        await m.delete()

@Client.on_message(filters.command(["totalrequests", "totalrequest", "total_requests"]) & filters.user(ADMINS))
async def total_requests(client, message):
    if join_db().isActive():
        total = await join_db().get_all_users_count()
        await message.reply_text(
            text=f"📊 **Total Join Requests in Database:** `{total}`",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await message.reply_text("⚠️ Join requests database is not active.")

async def execute_purge_requests(client=None) -> tuple[int, int]:
    """
    Core purge requests logic: deletes join requests from database
    and declines tracked pending join requests in AUTH_CHANNEL.
    Reused by both manual /purgerequests command and 24-hour automatic scheduler.
    """
    import logging
    import asyncio
    from pyrogram.errors import FloodWait
    from utils import temp
    log = logging.getLogger(__name__)
    log.info("[REQUEST PURGE] START")
    log.info(f"[REQUEST PURGE] CHANNEL = {AUTH_CHANNEL}")

    db_count = 0
    users = []
    if join_db().isActive():
        db_count = await join_db().get_all_users_count()
        users = await join_db().get_all_users()
        await join_db().delete_all_users()

    bot_client = client or getattr(temp, "BOT", None)
    declined_count = 0
    if AUTH_CHANNEL and users and bot_client:
        for u in users:
            uid = u.get("user_id")
            if not uid:
                continue
            try:
                await bot_client.decline_chat_join_request(int(AUTH_CHANNEL), int(uid))
                declined_count += 1
            except FloodWait as f:
                await asyncio.sleep(f.value)
                try:
                    await bot_client.decline_chat_join_request(int(AUTH_CHANNEL), int(uid))
                    declined_count += 1
                except Exception:
                    pass
            except Exception:
                pass

    log.info(f"[REQUEST PURGE]\nPurge completed: db_purged={db_count}, channel_declined={declined_count}")
    return db_count, declined_count


@Client.on_message(filters.command(["purgerequests", "purgerrequests", "purgerequest", "purge_requests", "purge_request"]) & filters.user(ADMINS))
async def purge_requests(client, message):
    msg = await message.reply_text("Processing /purgerequests...", parse_mode=enums.ParseMode.MARKDOWN)

    db_count, declined_count = await execute_purge_requests(client)

    text = f"✅ **Purged {db_count} Requests from Database.**\n\n"
    if declined_count > 0:
        text += f"✅ **Declined {declined_count} tracked pending request(s) in Channel.**\n\n"
    text += (
        "⚠️ **Note:** Telegram Bot API does not allow bots to bulk-purge all channel join requests at once "
        "(`HideAllChatJoinRequests` is restricted to user accounts)."
    )

    await msg.edit(text, parse_mode=enums.ParseMode.MARKDOWN)

# ─── BATCH CONCURRENCY CONFIGURATION ──────────────────────────────────────────
BATCH_SEND_CONCURRENCY = int(os.getenv("BATCH_SEND_CONCURRENCY", "8"))


# ─── PARALLEL BATCH FILE DELIVERY ENGINE ─────────────────────────────────────
async def send_batch_files(
    client,
    chat_id,
    files,
    user_id=None,
    protect_content=False,
    reply_markup=None,
    custom_caption_builder=None
):
    """
    High-speed parallel batch file delivery engine with controlled concurrency,
    file order preservation, automatic retries, and 10-minute auto-deletion.
    """
    import asyncio
    import time
    import logging
    from utils import schedule_filter_message_delete, get_size, temp
    from pyrogram.errors import FloodWait

    log = logging.getLogger(__name__)
    target_id = user_id or chat_id
    if not files:
        return []

    start_time = time.monotonic()
    total_files = len(files)

    log.info(
        f"[BATCH SEND START]\n"
        f"chat_id={target_id}\n"
        f"files={total_files}\n"
        f"concurrency={BATCH_SEND_CONCURRENCY}"
    )

    # 1. Preload database records if files is a list of file IDs or partial records needing lookup
    missing_lookup_ids = []
    for f in files:
        if isinstance(f, str):
            missing_lookup_ids.append(f)
        elif isinstance(f, dict) and (not f.get("file_name") or not f.get("file_size")):
            fid = f.get("file_id")
            if fid:
                missing_lookup_ids.append(fid)

    preloaded_map = {}
    if missing_lookup_ids:
        try:
            from database.ia_filterdb import get_bulk_file_details
            preloaded_map = await get_bulk_file_details(missing_lookup_ids)
        except Exception as e:
            log.warning(f"[BATCH SEND] Bulk preload fallback: {e}")

    # 2. Pre-build metadata and captions for all files
    prepared_items = []
    bot_uname = temp.U_NAME if hasattr(temp, "U_NAME") and temp.U_NAME else "BotUsername"

    for idx, f in enumerate(files, 1):
        if isinstance(f, str):
            fid = f
            file_doc = preloaded_map.get(f, {"file_id": f})
        elif isinstance(f, dict):
            fid = f.get("file_id")
            if fid and fid in preloaded_map:
                file_doc = {**preloaded_map[fid], **f}
            else:
                file_doc = f
        else:
            fid = getattr(f, "file_id", None)
            file_doc = getattr(f, "__dict__", {})

        if not fid:
            continue

        if custom_caption_builder:
            cap = custom_caption_builder(file_doc, idx, total_files)
        else:
            fname = file_doc.get("file_name", "File")
            raw_size = file_doc.get("file_size", 0)
            fsize = get_size(raw_size) if raw_size else "Unknown Size"
            lang = file_doc.get("language", "Unknown")
            cap = (
                f"⦿ <i>File name:</i> <code>{fname}</code>\n"
                f"⦿ <i>Size:</i> {fsize}\n"
                f"⦿ <i>Language:</i> {lang}\n"
                f"⦿ <i>File:</i> {idx} / {total_files}\n\n"
                f"@{bot_uname}"
            )

        prepared_items.append({
            "index": idx,
            "file_id": str(fid),
            "caption": cap,
            "protect": file_doc.get("protect", protect_content),
            "reply_markup": file_doc.get("reply_markup", reply_markup)
        })

    if not prepared_items:
        return []

    # 3. Controlled concurrency execution
    sent_results = [None] * len(prepared_items)
    semaphore = asyncio.Semaphore(BATCH_SEND_CONCURRENCY)

    async def _send_item(idx_pos, item):
        fid = item["file_id"]
        cap = item["caption"]
        prot = item["protect"]
        rm = item["reply_markup"]

        log.info(
            f"[BATCH SEND]\n"
            f"index={item['index']}\n"
            f"total={total_files}\n"
            f"file_id={fid}"
        )

        for attempt in range(3):
            try:
                async with semaphore:
                    msg = await client.send_cached_media(
                        chat_id=target_id,
                        file_id=fid,
                        caption=cap,
                        protect_content=prot,
                        reply_markup=rm
                    )
                if msg:
                    schedule_filter_message_delete(client, msg.chat.id, msg.id, 600)
                    sent_results[idx_pos] = msg
                    return msg
            except FloodWait as fw:
                log.warning(f"[BATCH SEND] FloodWait {fw.value}s on file_id={fid}")
                await asyncio.sleep(fw.value + 1)
            except Exception as ex:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    log.error(
                        f"[BATCH SEND FAILED]\n"
                        f"file_id={fid}\n"
                        f"error={ex}"
                    )
                    return None
        return None

    for i, item in enumerate(prepared_items):
        await _send_item(i, item)
        if len(prepared_items) > 1:
            await asyncio.sleep(0.35)

    sent_messages = [m for m in sent_results if m is not None]
    failed_count = total_files - len(sent_messages)
    duration = time.monotonic() - start_time

    log.info(
        f"[BATCH SEND SUCCESS]\n"
        f"sent={len(sent_messages)}\n"
        f"failed={failed_count}\n"
        f"duration={duration:.3f}s"
    )
    log.info(
        f"[BATCH SEND COMPLETE]\n"
        f"total={total_files}\n"
        f"sent={len(sent_messages)}\n"
        f"failed={failed_count}\n"
        f"duration={duration:.3f}s"
    )

    return sent_messages


# ─── SERIES FILE DELIVERY HANDLER (WITH METADATA) ───────────────────────────
async def send_series_files_to_user(client, user_id, files, query=None):
    from utils import get_size, schedule_filter_message_delete, temp
    import logging
    import asyncio
    import html

    log = logging.getLogger(__name__)
    if not files:
        return []

    def _get_episode_num(f):
        ep = f.get("episode")
        if isinstance(ep, int) and ep > 0:
            return (ep, f.get("file_name", ""))
        try:
            if ep is not None and str(ep).strip().lstrip("-").isdigit() and int(str(ep).strip()) > 0:
                return (int(str(ep).strip()), f.get("file_name", ""))
        except Exception:
            pass

        ep_idx = f.get("episode_index")
        if isinstance(ep_idx, int) and ep_idx > 0:
            return (ep_idx, f.get("file_name", ""))
        try:
            if ep_idx is not None and str(ep_idx).strip().lstrip("-").isdigit() and int(str(ep_idx).strip()) > 0:
                return (int(str(ep_idx).strip()), f.get("file_name", ""))
        except Exception:
            pass

        try:
            from plugins.series import _extract_episode_number
            fname = f.get("file_name", "")
            extracted = _extract_episode_number(fname)
            if extracted is not None and extracted > 0:
                return (extracted, fname)
        except Exception:
            pass
        return (99999, f.get("file_name", ""))

    # 1. Sort files strictly numerically by episode number (1, 2, 3... 10)
    sorted_files = sorted(files, key=_get_episode_num)

    # 2. Deduplicate exact duplicate records (same file_id)
    seen_ids = set()
    ordered_files = []
    for f in sorted_files:
        fid = f.get("file_id")
        if fid:
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
        ordered_files.append(f)

    sorted_order = [_get_episode_num(f) for f in ordered_files]

    # 3. Extract common Series metadata context
    first_file = ordered_files[0] if ordered_files else {}
    is_series = any(f.get("is_series") for f in ordered_files)

    series_id = first_file.get("series_id", "")
    season = first_file.get("season", 0)
    language = first_file.get("language", "")
    quality = first_file.get("quality", "")

    # 4. Send metadata ONCE before sending files
    if is_series and language and quality:
        if str(season).isdigit():
            s_num = int(season)
            series_tag = f"#Series {s_num:02d}" if s_num > 0 else "#Series 01"
        else:
            series_tag = f"#{season}"

        lang_clean = str(language).strip().replace(" ", "_")
        lang_tag = f"#{lang_clean}" if not lang_clean.startswith("#") else lang_clean

        qual_clean = str(quality).strip().replace(" ", "_")
        qual_tag = f"#{qual_clean}" if not qual_clean.startswith("#") else qual_clean

        metadata_text = f"{series_tag}\n{lang_tag}\n{qual_tag}"

        log.info(f"[SERIES DELIVERY]\nrequest_id={first_file.get('file_id', '')}\nseries_id={series_id}\nseason={season}\nlanguage={language}\nquality={quality}\ntotal_files={len(ordered_files)}")
        log.info(f"[SERIES DELIVERY]\naction=EPISODES_SORTED\norder={sorted_order}")
        log.info(f"[SERIES DELIVERY]\naction=METADATA_SENT\nmetadata={metadata_text.replace(chr(10), ' ')}")

        try:
            meta_msg = await client.send_message(
                chat_id=user_id,
                text=metadata_text,
                protect_content=False,
            )
            if meta_msg:
                schedule_filter_message_delete(client, meta_msg.chat.id, meta_msg.id, 600)
        except Exception as ex:
            log.warning(f"Failed to send metadata message: {ex}")

    # 5. Caption builder
    bot_uname = temp.U_NAME if hasattr(temp, "U_NAME") and temp.U_NAME else "BotUsername"
    def series_caption_builder(file_doc, idx, total_eps):
        fname = file_doc.get("file_name", "Unknown File")
        if len(fname) > 900:
            fname = fname[:900] + "..."
        file_name = html.escape(fname)

        raw_size = file_doc.get("file_size", 0)
        file_size = get_size(raw_size) if raw_size else "Unknown Size"

        lang_str = file_doc.get("language", "Unknown")
        rating = file_doc.get("series_rating", "")

        f_caption = (
            f"⦿ <i>File name:</i> <code>{file_name}</code>\n"
            f"⦿ <i>Size:</i> {file_size}\n"
            f"⦿ <i>Language:</i> {lang_str}\n"
        )
        if rating and str(rating).lower() not in ["skip", "n/a", ""]:
            f_caption += f"⦿ <i>Rating:</i> ⭐ {rating}\n"

        f_caption += (
            f"⦿ <i>File:</i> {idx} / {total_eps}\n\n"
            f"@{bot_uname}"
        )
        return f_caption

    # 6. Deliver files concurrently with preserved order
    sent_messages = await send_batch_files(
        client=client,
        chat_id=user_id,
        files=ordered_files,
        user_id=user_id,
        custom_caption_builder=series_caption_builder
    )

    log.info(f"[SERIES DELIVERY]\naction=COMPLETED\ntotal_files={len(sent_messages)}")

    # 7. Send final delete notification
    if sent_messages:
        try:
            k = await client.send_message(
                chat_id=user_id,
                text=(
                    "<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\n"
                    "ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>"
                    "(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n"
                    "<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇsᴇ ғɪʟᴇs ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ ᴀɴᴅ sᴛᴀʀᴛ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇʀᴇ</b></i></blockquote>"
                ),
                parse_mode=enums.ParseMode.HTML
            )
            if k:
                schedule_filter_message_delete(client, k.chat.id, k.id, 600)
        except Exception:
            pass

    return sent_messages


# ─── MOVIE FILE DELIVERY HANDLER (DIRECT PM DELIVERY) ────────────────────────
async def send_movie_files_to_user(client, user_id, files, query=None, movie_title=None, language=None, quality=None):
    from utils import get_size, temp, schedule_filter_message_delete
    import logging
    import asyncio

    log = logging.getLogger(__name__)
    if not files:
        return 0

    # 1. Deduplicate files (same file_id)
    seen_ids = set()
    ordered_files = []
    for f in files:
        fid = f.get("file_id")
        if fid:
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
        ordered_files.append(f)

    log.info(f"[MOVIE SEND FILES]\ntitle={movie_title}\nlanguage={language}\nquality={quality}\ncount={len(ordered_files)}")

    # 2. Send metadata tag ONCE if available
    if movie_title and language and quality:
        lang_clean = str(language).strip().replace(" ", "_")
        lang_tag = f"#{lang_clean}" if not lang_clean.startswith("#") else lang_clean
        qual_clean = str(quality).strip().replace(" ", "_")
        qual_tag = f"#{qual_clean}" if not qual_clean.startswith("#") else qual_clean
        metadata_text = f"🎬 <b>{movie_title}</b>\n{lang_tag}\n{qual_tag}"
        try:
            meta_msg = await client.send_message(
                chat_id=user_id,
                text=metadata_text,
                parse_mode=enums.ParseMode.HTML,
                protect_content=False,
            )
            if meta_msg:
                schedule_filter_message_delete(client, meta_msg.chat.id, meta_msg.id, 600)
        except Exception as ex:
            log.warning(f"Failed to send movie metadata message: {ex}")

    # 3. Caption builder
    bot_uname = temp.U_NAME if hasattr(temp, "U_NAME") and temp.U_NAME else "BotUsername"
    def movie_caption_builder(file_doc, idx, total_files):
        file_name = file_doc.get("file_name", "Movie File")
        raw_size = file_doc.get("file_size", 0)
        file_size = get_size(raw_size) if raw_size else "Unknown Size"
        lang_str = language or file_doc.get("language", "Unknown")

        f_caption = (
            f"⦿ <i>File name:</i> <code>{file_name}</code>\n"
            f"⦿ <i>Size:</i> {file_size}\n"
            f"⦿ <i>Language:</i> {lang_str}\n"
            f"⦿ <i>File:</i> {idx} / {total_files}\n\n"
            f"@{bot_uname}"
        )
        return f_caption

    # 4. Deliver files concurrently with preserved order
    sent_messages = await send_batch_files(
        client=client,
        chat_id=user_id,
        files=ordered_files,
        user_id=user_id,
        custom_caption_builder=movie_caption_builder
    )

    # 5. Send final delete notification
    if sent_messages:
        try:
            k = await client.send_message(
                chat_id=user_id,
                text=(
                    "<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\n"
                    "ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ <b><u>10 mins</u> 🫥 <i></b>"
                    "(ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs)</i>.\n\n"
                    "<b><i>ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇsᴇ ғɪʟᴇs ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ ᴀɴᴅ sᴛᴀʀᴛ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛʜᴇʀᴇ</b></i></blockquote>"
                ),
                parse_mode=enums.ParseMode.HTML
            )
            if k:
                schedule_filter_message_delete(client, k.chat.id, k.id, 600)
        except Exception:
            pass

    return len(sent_messages)


