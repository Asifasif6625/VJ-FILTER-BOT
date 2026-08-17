with open('plugins/commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_block = '''        is_series_batch = any(f.get("is_series") for f in files) if isinstance(files, list) else False
        if is_series_batch:
            log.info(f"[ALL] EXPANDED FILE COUNT: {len(files)}")
            
        filesarr = []
        if is_series_batch:
            log.info(f"[ALL] STARTING SEND LOOP")
            
        for idx, file in enumerate(files, start=1):
            file_id_str = file["file_id"]
            
            if file.get("is_series"):
                f_caption = ""
                protect_content = False
            else:
                files1 = await get_file_details(file_id_str)
                if not files1: continue
                title = files1["file_name"]
                size=get_size(files1["file_size"])
                f_caption=files1.get("caption", "")
            
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                    except:
                        f_caption=f_caption
                if f_caption is None:
                    f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files1['file_name'].split()))}"
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
                        await message.reply_text(
                            text=text.format(message.from_user.mention),
                            protect_content=True,
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                        return
                        
            if STREAM_MODE == True:
                button = [[InlineKeyboardButton('sᴛʀᴇᴀᴍ ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id_str}')]]
                reply_markup=InlineKeyboardMarkup(button)
            else:
                reply_markup = None
                
            try:
                if file.get("is_series"):
                    log.info(f"[ALL] SENDING FILE: {file_id_str}")
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=file_id_str,
                    caption=f_caption,
                    protect_content=True if pre == 'allfilesp' else False,
                    reply_markup=reply_markup
                )
                filesarr.append(msg)
                if file.get("is_series"):
                    log.info(f"SERIES FILE SENT: {file_id_str}")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    msg = await client.send_cached_media(
                        chat_id=message.from_user.id,
                        file_id=file_id_str,
                        caption=f_caption,
                        protect_content=True if pre == 'allfilesp' else False,
                        reply_markup=reply_markup
                    )
                    filesarr.append(msg)
                    if file.get("is_series"):
                        log.info(f"SERIES FILE SENT: {file_id_str}")
                except Exception as e:
                    if file.get("is_series"):
                        log.error(f"Failed to send series file {file_id_str} after FloodWait: {e}")
                    pass
            except Exception as e:
                if file.get("is_series"):
                    log.error(f"Failed to send series file {file_id_str}: {e}")
                continue
                
        if is_series_batch:
            log.info("SERIES SEND COMPLETED")'''

good_block = '''        is_series_batch = any(f.get("is_series") for f in files) if isinstance(files, list) else False
        if is_series_batch:
            log.info(f"[ALL] EXPANDED FILE COUNT: {len(files)}")
            
        filesarr = []
        if is_series_batch:
            log.info(f"[ALL] STARTING SEND LOOP")
            
        for idx, file in enumerate(files, start=1):
            file_id_str = file["file_id"]
            
            if file.get("is_series"):
                f_caption = ""
                protect_content = False
            else:
                files1 = await get_file_details(file_id_str)
                if not files1: continue
                title = files1["file_name"]
                size=get_size(files1["file_size"])
                f_caption=files1.get("caption", "")
            
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                    except:
                        f_caption=f_caption
                if f_caption is None:
                    f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files1['file_name'].split()))}"
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
                        await message.reply_text(
                            text=text.format(message.from_user.mention),
                            protect_content=True,
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                        return
                protect_content = True if (hasattr(message, "command") and len(message.command) > 1 and message.command[1].startswith("allfilesp")) else False
                        
            if STREAM_MODE == True:
                button = [[InlineKeyboardButton('sᴛʀᴇᴀᴍ ᴀɴᴅ ᴅᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id_str}')]]
                reply_markup=InlineKeyboardMarkup(button)
            else:
                reply_markup = None
                
            try:
                if file.get("is_series"):
                    log.info(f"[ALL] SENDING FILE {idx}/{len(files)}")
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=file_id_str,
                    caption=f_caption,
                    protect_content=protect_content,
                    reply_markup=reply_markup
                )
                filesarr.append(msg)
                if file.get("is_series"):
                    log.info(f"[ALL] FILE {idx} SENT")
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    msg = await client.send_cached_media(
                        chat_id=message.from_user.id,
                        file_id=file_id_str,
                        caption=f_caption,
                        protect_content=protect_content,
                        reply_markup=reply_markup
                    )
                    filesarr.append(msg)
                    if file.get("is_series"):
                        log.info(f"[ALL] FILE {idx} SENT")
                except Exception as e:
                    if file.get("is_series"):
                        log.error(f"[ALL] Failed to send series file {file_id_str} after FloodWait: {e}")
                    pass
            except Exception as e:
                if file.get("is_series"):
                    log.error(f"[ALL] Failed to send series file {file_id_str}: {e}")
                continue
                
        if is_series_batch:
            log.info(f"[ALL] SEND COMPLETED: {len(filesarr)}/{len(files)}")'''

if bad_block in content:
    content = content.replace(bad_block, good_block)
    with open('plugins/commands.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Not found')
