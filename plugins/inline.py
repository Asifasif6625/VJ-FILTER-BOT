# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import html
import logging
from pyrogram import Client, emoji, enums
from pyrogram.errors import QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultPhoto,
    InlineQuery,
    MessageEntity
)
from pyrogram.enums import MessageEntityType
from utils import is_subscribed, temp, is_gdbot_client, get_delivery_bot_username
from info import AUTH_USERS, AUTH_CHANNEL, PICS
from database.series_db import (
    get_latest_filters,
    search_super_movies,
    search_series,
    clean_series_title
)

logger = logging.getLogger(__name__)

DEFAULT_POSTER = "https://files.catbox.moe/mp2y81.jpg"
PAGE_SIZE = 15
CUSTOM_EMOJI_ID = 4926956800005112527


def _utf16_len(text: str) -> int:
    """Returns the UTF-16 code units length of text for Telegram entity offset calculation."""
    return len(text.encode("utf-16-le")) // 2


def build_movie_caption_and_entities(
    title: str,
    year: str,
    genres: str,
    rating: str,
    quals: str,
    langs: str
) -> tuple[str, list[MessageEntity]]:
    """
    Builds the plain-text caption and explicit MessageEntity list for Super Movie Filter.
    Format:
    ○ Movie: {title}
    ○ Year: {year}
    ○ Genres: {genres}
    ○ Rating: {rating}
    ○ Quality: {quals}
    ○ Languages: {langs}
    """
    lines_meta = [
        ("Movie:", title, True),
        ("Year:", year, False),
        ("Genres:", genres, False),
        ("Rating:", rating, False),
        ("Quality:", quals, False),
        ("Languages:", langs, False)
    ]
    
    entities = []
    caption_lines = []
    current_utf16_offset = 0
    emoji_str = "○"
    
    for idx, (label, val, is_val_bold) in enumerate(lines_meta):
        line_text = f"{emoji_str} {label} {val}"
        line_utf16_len = _utf16_len(line_text)
        
        # 1. Bold entity for label (e.g. "Movie:")
        label_offset = current_utf16_offset + _utf16_len(f"{emoji_str} ")
        label_len = _utf16_len(label)
        entities.append(
            MessageEntity(
                type=MessageEntityType.BOLD,
                offset=label_offset,
                length=label_len
            )
        )
        
        # 2. Bold entity for movie title
        if is_val_bold and val:
            val_offset = label_offset + label_len + _utf16_len(" ")
            val_len = _utf16_len(val)
            entities.append(
                MessageEntity(
                    type=MessageEntityType.BOLD,
                    offset=val_offset,
                    length=val_len
                )
            )
            
        caption_lines.append(line_text)
        current_utf16_offset += line_utf16_len + (_utf16_len("\n") if idx < len(lines_meta) - 1 else 0)
        
    full_caption = "\n".join(caption_lines)
    
    # 3. Italic entity covering the whole metadata block
    entities.append(
        MessageEntity(
            type=MessageEntityType.ITALIC,
            offset=0,
            length=_utf16_len(full_caption)
        )
    )
    
    return full_caption, entities


def build_series_caption_and_entities(
    name: str,
    year: str,
    genres: str,
    rating: str,
    seasons: str,
    langs: str
) -> tuple[str, list[MessageEntity]]:
    """
    Builds the plain-text caption and explicit MessageEntity list for Super Series Filter.
    Format:
    ○ Series: {name}
    ○ Year: {year}
    ○ Genres: {genres}
    ○ Rating: {rating}
    ○ Seasons: {seasons}
    ○ Languages: {langs}
    """
    lines_meta = [
        ("Series:", name, True),
        ("Year:", year, False),
        ("Genres:", genres, False),
        ("Rating:", rating, False),
        ("Seasons:", seasons, False),
        ("Languages:", langs, False)
    ]
    
    entities = []
    caption_lines = []
    current_utf16_offset = 0
    emoji_str = "○"
    
    for idx, (label, val, is_val_bold) in enumerate(lines_meta):
        line_text = f"{emoji_str} {label} {val}"
        line_utf16_len = _utf16_len(line_text)
        
        # 1. Bold entity for label (e.g. "Series:")
        label_offset = current_utf16_offset + _utf16_len(f"{emoji_str} ")
        label_len = _utf16_len(label)
        entities.append(
            MessageEntity(
                type=MessageEntityType.BOLD,
                offset=label_offset,
                length=label_len
            )
        )
        
        # 2. Bold entity for series name
        if is_val_bold and val:
            val_offset = label_offset + label_len + _utf16_len(" ")
            val_len = _utf16_len(val)
            entities.append(
                MessageEntity(
                    type=MessageEntityType.BOLD,
                    offset=val_offset,
                    length=val_len
                )
            )
            
        caption_lines.append(line_text)
        current_utf16_offset += line_utf16_len + (_utf16_len("\n") if idx < len(lines_meta) - 1 else 0)
        
    full_caption = "\n".join(caption_lines)
    
    # 3. Italic entity covering the whole metadata block
    entities.append(
        MessageEntity(
            type=MessageEntityType.ITALIC,
            offset=0,
            length=_utf16_len(full_caption)
        )
    )
    
    return full_caption, entities


async def inline_users(query: InlineQuery):
    """Check if the user is authorized to use inline mode."""
    if AUTH_USERS:
        if query.from_user and query.from_user.id in AUTH_USERS:
            return True
        return False
    if query.from_user and query.from_user.id not in getattr(temp, "BANNED_USERS", []):
        return True
    return False


def _is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://")


def _build_movie_inline_result(movie: dict, bot_username: str) -> InlineQueryResultPhoto:
    doc_id = str(movie.get("_id", ""))
    title = movie.get("title") or movie.get("name") or "Movie"
    title_clean = clean_series_title(title)
    
    year = str(movie.get("year", "N/A")).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    
    rating = str(movie.get("rating", "N/A")).strip()
    if not rating:
        rating = "N/A"
    elif not rating.endswith("/10") and rating != "N/A":
        rating = f"{rating}/10"
        
    raw_genres = movie.get("genres") or movie.get("genre") or "N/A"
    genres = ", ".join(raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
    genres = genres.strip() or "N/A"
    
    raw_langs = movie.get("languages") or []
    langs_str = ", ".join(raw_langs) if isinstance(raw_langs, list) else str(raw_langs)
    langs_str = langs_str.strip() or "N/A"
    
    raw_quals = movie.get("qualities") or []
    quals_str = ", ".join(raw_quals) if isinstance(raw_quals, list) else str(raw_quals)
    quals_str = quals_str.strip() or "N/A"
    
    poster = movie.get("poster")
    photo_url = poster if _is_valid_url(poster) else DEFAULT_POSTER
    
    is_cs = bool(movie.get("coming_soon") or movie.get("status") == "coming_soon" or not movie.get("file_ids"))
    
    # Visual Card Title & Description
    card_title = f"🎬 {title}{year_str}"
    
    desc_parts = []
    if year and year != "N/A":
        desc_parts.append(year)
    if rating and rating != "N/A":
        desc_parts.append(f"⭐ {rating.replace('/10', '')}")
    if raw_langs:
        primary_lang = raw_langs[0] if isinstance(raw_langs, list) else str(raw_langs).split(",")[0]
        desc_parts.append(primary_lang.strip())
    if raw_quals:
        primary_qual = raw_quals[0] if isinstance(raw_quals, list) else str(raw_quals).split(",")[0]
        desc_parts.append(primary_qual.strip())
    card_desc = " • ".join(desc_parts) if desc_parts else "Movie Filter"
    if is_cs:
        card_desc = f"⏳ Coming Soon • {card_desc}"
        
    # Build HTML formatted caption
    caption_html = (
        f"<i>○ <b>Movie:</b> <b>{html.escape(title_clean)}</b>\n"
        f"○ <b>Year:</b> {html.escape(year)}\n"
        f"○ <b>Genres:</b> {html.escape(genres)}\n"
        f"○ <b>Rating:</b> {html.escape(rating)}\n"
        f"○ <b>Quality:</b> {html.escape(quals_str)}\n"
        f"○ <b>Languages:</b> {html.escape(langs_str)}</i>"
    )
    
    # 1-Click Action Button
    start_url = f"https://t.me/{bot_username}?start=movie_{doc_id}"
    if is_cs:
        btn = [[InlineKeyboardButton("⏳ Coming soon!", url=start_url)]]
    else:
        try:
            btn = [[InlineKeyboardButton("📂 Get Movie Files", url=start_url, style="primary")]]
        except TypeError:
            btn = [[InlineKeyboardButton("📂 Get Movie Files", url=start_url)]]
            
    return InlineQueryResultPhoto(
        photo_url=photo_url,
        thumb_url=photo_url,
        title=card_title,
        description=card_desc,
        caption=caption_html,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
    )


def _build_series_inline_result(series: dict, bot_username: str) -> InlineQueryResultPhoto:
    doc_id = str(series.get("_id", ""))
    name = series.get("name") or series.get("title") or "Series"
    name_clean = clean_series_title(name)
    
    year = str(series.get("year", "N/A")).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    
    rating = str(series.get("rating", "N/A")).strip()
    if not rating:
        rating = "N/A"
    elif not rating.endswith("/10") and rating != "N/A":
        rating = f"{rating}/10"
        
    raw_genres = series.get("genre") or series.get("genres") or "N/A"
    genres = ", ".join(raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
    genres = genres.strip() or "N/A"
    
    raw_langs = series.get("languages") or []
    langs_str = ", ".join(raw_langs) if isinstance(raw_langs, list) else str(raw_langs)
    langs_str = langs_str.strip() or "N/A"
    
    raw_seasons = series.get("seasons") or [1]
    if isinstance(raw_seasons, list):
        seasons_count = len(raw_seasons)
        seasons_str = f"{seasons_count} Season(s)" if seasons_count > 1 else "Season 1"
    else:
        seasons_str = f"Season {raw_seasons}"
        
    raw_quals = series.get("qualities") or []
    quals_str = ", ".join(raw_quals) if isinstance(raw_quals, list) else str(raw_quals)
    quals_str = quals_str.strip() or "N/A"
    
    poster = series.get("poster")
    photo_url = poster if _is_valid_url(poster) else DEFAULT_POSTER
    
    is_cs = bool(series.get("coming_soon") or series.get("status") == "coming_soon")
    
    # Visual Card Title & Description
    card_title = f"📺 {name}{year_str}"
    
    desc_parts = []
    if year and year != "N/A":
        desc_parts.append(year)
    if rating and rating != "N/A":
        desc_parts.append(f"⭐ {rating.replace('/10', '')}")
    if raw_langs:
        primary_lang = raw_langs[0] if isinstance(raw_langs, list) else str(raw_langs).split(",")[0]
        desc_parts.append(primary_lang.strip())
    desc_parts.append(seasons_str)
    card_desc = " • ".join(desc_parts) if desc_parts else "Series Filter"
    if is_cs:
        card_desc = f"⏳ Coming Soon • {card_desc}"
        
    # Build HTML formatted caption
    caption_html = (
        f"<i>○ <b>Series:</b> <b>{html.escape(name_clean)}</b>\n"
        f"○ <b>Year:</b> {html.escape(year)}\n"
        f"○ <b>Genres:</b> {html.escape(genres)}\n"
        f"○ <b>Rating:</b> {html.escape(rating)}\n"
        f"○ <b>Seasons:</b> {html.escape(seasons_str)}\n"
        f"○ <b>Languages:</b> {html.escape(langs_str)}</i>"
    )
    
    # 1-Click Action Button
    start_url = f"https://t.me/{bot_username}?start=series_{doc_id}"
    if is_cs:
        btn = [[InlineKeyboardButton("⏳ Coming soon!", url=start_url)]]
    else:
        try:
            btn = [[InlineKeyboardButton("📂 Get Series Files", url=start_url, style="primary")]]
        except TypeError:
            btn = [[InlineKeyboardButton("📂 Get Series Files", url=start_url)]]
            
    return InlineQueryResultPhoto(
        photo_url=photo_url,
        thumb_url=photo_url,
        title=card_title,
        description=card_desc,
        caption=caption_html,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
    )


_INLINE_POSTER_CACHE = {}

async def resolve_normal_group_poster(g: dict) -> str:
    """
    Resolves the actual movie or series poster for a normal filter group.
    1. Check memory cache.
    2. Check if poster already present on group or files.
    3. Check super_movies_col or series_col in DB.
    4. Fetch from IMDb / TMDB via get_poster.
    5. Fallback to DEFAULT_POSTER.
    """
    title = str(g.get("title", "")).strip()
    year = str(g.get("year", "N/A")).strip()
    year_str = year if year and year.upper() != "N/A" else ""
    cache_key = f"{title.lower()}_{year_str}"

    if cache_key in _INLINE_POSTER_CACHE:
        return _INLINE_POSTER_CACHE[cache_key]

    # 1. Existing valid poster on group
    grp_poster = g.get("poster")
    if grp_poster and _is_valid_url(grp_poster):
        _INLINE_POSTER_CACHE[cache_key] = grp_poster
        return grp_poster

    # 2. Check if a Super Movie or Series has this poster in DB
    try:
        from database.series_db import super_movies_col, series_col
        m_doc = await super_movies_col.find_one({
            "$or": [
                {"movie.title": re.compile(rf"^{re.escape(title)}$", re.IGNORECASE)},
                {"title": re.compile(rf"^{re.escape(title)}$", re.IGNORECASE)}
            ]
        })
        if m_doc and m_doc.get("poster") and _is_valid_url(m_doc["poster"]):
            _INLINE_POSTER_CACHE[cache_key] = m_doc["poster"]
            return m_doc["poster"]

        s_doc = await series_col.find_one({
            "name": re.compile(rf"^{re.escape(title)}$", re.IGNORECASE)
        })
        if s_doc and s_doc.get("poster") and _is_valid_url(s_doc["poster"]):
            _INLINE_POSTER_CACHE[cache_key] = s_doc["poster"]
            return s_doc["poster"]
    except Exception:
        pass

    # 3. Fast IMDb / TMDB poster fetch
    try:
        from utils import get_poster
        q = f"{title} {year_str}".strip() if year_str else title
        imdb_res = await asyncio.wait_for(get_poster(q), timeout=2.5)
        if (not imdb_res or not imdb_res.get("poster")) and year_str:
            try:
                imdb_res = await asyncio.wait_for(get_poster(title), timeout=2.0)
            except Exception:
                pass
        if imdb_res and isinstance(imdb_res, dict) and imdb_res.get("poster") and _is_valid_url(imdb_res["poster"]):
            p = imdb_res["poster"]
            _INLINE_POSTER_CACHE[cache_key] = p
            return p
    except Exception:
        pass

    fallback = DEFAULT_POSTER if _is_valid_url(DEFAULT_POSTER) else "https://files.catbox.moe/mp2y81.jpg"
    _INLINE_POSTER_CACHE[cache_key] = fallback
    return fallback


def _build_normal_inline_result(g: dict, bot_username: str, thumb_url: str = None) -> InlineQueryResultPhoto:
    gid = g.get("group_id", "")
    title = g.get("title", "Movie")
    year = str(g.get("year", "N/A")).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    is_series = g.get("is_series", False)
    season = g.get("season", 1) or 1
    files_count = len(g.get("files", []))

    if is_series:
        card_title = f"📺 S{season:02d} {title}{year_str}"
        card_desc = f"Series • {files_count} file(s) available"
        caption_html = (
            f"📺 <b>Series:</b> <b>{html.escape(title)}</b>\n"
            f"📅 <b>Year:</b> {html.escape(year)}\n"
            f"📁 <b>Available Files:</b> {files_count}\n\n"
            f"<i>Tap Download below to get files in Bot!</i>"
        )
    else:
        card_title = f"🎬 {title}{year_str}"
        card_desc = f"Movie • {files_count} file(s) available"
        caption_html = (
            f"🎬 <b>Movie:</b> <b>{html.escape(title)}</b>\n"
            f"📅 <b>Year:</b> {html.escape(year)}\n"
            f"📁 <b>Available Files:</b> {files_count}\n\n"
            f"<i>Tap Download below to get files in Bot!</i>"
        )

    start_url = f"https://t.me/{bot_username}?start=norm_{gid}"
    btn = [[InlineKeyboardButton("📥 Download Files", url=start_url)]]
    photo = thumb_url if _is_valid_url(thumb_url) else (DEFAULT_POSTER if _is_valid_url(DEFAULT_POSTER) else "https://files.catbox.moe/mp2y81.jpg")

    return InlineQueryResultPhoto(
        photo_url=photo,
        thumb_url=photo,
        title=card_title,
        description=card_desc,
        caption=caption_html,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_inline_query()
async def answer(bot: Client, query: InlineQuery):
    """
    Unified Telegram Inline Mode query handler for Movie and Series filters.
    - If Super Filter is ON: displays Super Movies & Series cards.
    - If Super Filter is OFF: displays Normal Filter movies & series cards from ia_filterdb.
    """
    # GDBOT is admin backend only: redirect inline search to Child/Delivery Bot
    if is_gdbot_client(bot):
        del_u = get_delivery_bot_username()
        await query.answer(
            results=[],
            cache_time=5,
            switch_pm_text=f"🔍 Use @{del_u} for Search" if del_u else "⚠️ Search runs on Child Bot",
            switch_pm_parameter="start"
        )
        return

    if not await inline_users(query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text="⚠️ Access Denied",
            switch_pm_parameter="start"
        )
        return

    if AUTH_CHANNEL and not await is_subscribed(bot, query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text="📢 Join Channel to Use Bot",
            switch_pm_parameter="subscribe"
        )
        return

    del_u = get_delivery_bot_username()
    bot_username = getattr(getattr(bot, "me", None), "username", None) or del_u or getattr(temp, "U_NAME", "Bot")
    bot_username = str(bot_username).lstrip("@")

    string = query.query.strip()
    offset_str = query.offset or "0"
    offset = int(offset_str) if offset_str.isdigit() else 0

    results = []

    from database.series_db import is_super_filter_enabled
    super_filter_on = await is_super_filter_enabled()

    if not super_filter_on:
        # ─── NORMAL FILTER INLINE MODE ──────────────────────────────────────────
        from database.ia_filterdb import get_search_results
        from plugins.pm_filter import build_normal_filter_groups
        from database.series_db import get_series_thumbnail

        if not string:
            files, _, total_count = await get_search_results(chat_id=0, query="", max_results=30, offset=offset, filter=True)
            groups = build_normal_filter_groups(files)
            switch_pm_text = f"🔥 Normal Movies & Series ({len(groups)})"
        else:
            files, _, total_count = await get_search_results(chat_id=0, query=string.lower(), max_results=50, offset=offset, filter=True)
            groups = build_normal_filter_groups(files, query_text=string)
            switch_pm_text = f"🔍 Results for '{string}' ({len(groups)})" if groups else f"❌ No results for '{string}'"

        page_groups = groups[:PAGE_SIZE]
        posters = await asyncio.gather(*(resolve_normal_group_poster(g) for g in page_groups), return_exceptions=True)
        for idx, g in enumerate(page_groups):
            p = posters[idx] if (idx < len(posters) and isinstance(posters[idx], str) and _is_valid_url(posters[idx])) else (DEFAULT_POSTER if _is_valid_url(DEFAULT_POSTER) else "https://files.catbox.moe/mp2y81.jpg")
            results.append(_build_normal_inline_result(g, bot_username, p))

        has_more = (offset + len(page_groups)) < total_count
        next_offset = str(offset + len(page_groups)) if has_more else ""
        cache_time = 15

    elif not string:
        # ─── SUPER FILTER CASE 1: NO QUERY -> SHOW LATEST / NEW MOVIES & SERIES ─
        page_items, total_count = await get_latest_filters(limit=PAGE_SIZE, offset=offset)
        
        for item in page_items:
            ftype = item.get("_filter_type") or ("movie" if "file_ids" in item else "series")
            if ftype == "movie":
                results.append(_build_movie_inline_result(item, bot_username))
            else:
                results.append(_build_series_inline_result(item, bot_username))
                
        has_more = (offset + len(page_items)) < total_count
        next_offset = str(offset + len(page_items)) if has_more else ""
        
        switch_pm_text = f"🔥 New Movies & Series ({total_count})"
        cache_time = 10  # Short cache for empty query so newly added filters show up quickly
        
    else:
        # ─── CASE 2: SEARCH QUERY -> SMART SEARCH ──────────────────────────────
        clean_q = clean_series_title(string)
        movies = await search_super_movies(string)
        series_list = await search_series(clean_q if clean_q else string)
        
        # Mark types
        for m in movies:
            m["_filter_type"] = "movie"
        for s in series_list:
            s["_filter_type"] = "series"
            
        # Deduplicate
        seen_ids = set()
        combined = []
        for item in (movies + series_list):
            item_id = str(item.get("_id", ""))
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                combined.append(item)
                
        total_count = len(combined)
        page_items = combined[offset:offset + PAGE_SIZE]
        
        for item in page_items:
            ftype = item.get("_filter_type") or ("movie" if "file_ids" in item else "series")
            if ftype == "movie":
                results.append(_build_movie_inline_result(item, bot_username))
            else:
                results.append(_build_series_inline_result(item, bot_username))
                
        has_more = (offset + len(page_items)) < total_count
        next_offset = str(offset + len(page_items)) if has_more else ""
        
        switch_pm_text = f"🔍 Results for '{string}' ({total_count})" if total_count > 0 else f"❌ No results for '{string}'"
        cache_time = 30

    try:
        await query.answer(
            results=results,
            is_personal=True,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start",
            next_offset=next_offset
        )
    except QueryIdInvalid:
        pass
    except Exception as e:
        logger.warning(f"[INLINE QUERY ERROR] {e}")
