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
from utils import is_subscribed, temp
from info import AUTH_USERS, AUTH_CHANNEL, PICS
from database.series_db import (
    get_latest_filters,
    search_super_movies,
    search_series,
    clean_series_title
)

logger = logging.getLogger(__name__)

DEFAULT_POSTER = PICS[0] if PICS else "https://files.catbox.moe/zck4ym.jpg"
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
    🔴 Movie: {title}
    🔴 Year: {year}
    🔴 Genres: {genres}
    🔴 Rating: {rating}
    🔴 Quality: {quals}
    🔴 Languages: {langs}
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
    emoji_str = "🔴"
    emoji_utf16_len = _utf16_len(emoji_str)
    
    for idx, (label, val, is_val_bold) in enumerate(lines_meta):
        line_text = f"{emoji_str} {label} {val}"
        line_utf16_len = _utf16_len(line_text)
        
        # 1. Custom Emoji entity for 🔴
        entities.append(
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=current_utf16_offset,
                length=emoji_utf16_len,
                custom_emoji_id=CUSTOM_EMOJI_ID
            )
        )
        
        # 2. Bold entity for label (e.g. "Movie:")
        label_offset = current_utf16_offset + _utf16_len(f"{emoji_str} ")
        label_len = _utf16_len(label)
        entities.append(
            MessageEntity(
                type=MessageEntityType.BOLD,
                offset=label_offset,
                length=label_len
            )
        )
        
        # 3. Bold entity for movie title
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
    
    # 4. Italic entity covering the whole metadata block
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
    🔴 Series: {name}
    🔴 Year: {year}
    🔴 Genres: {genres}
    🔴 Rating: {rating}
    🔴 Seasons: {seasons}
    🔴 Languages: {langs}
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
    emoji_str = "🔴"
    emoji_utf16_len = _utf16_len(emoji_str)
    
    for idx, (label, val, is_val_bold) in enumerate(lines_meta):
        line_text = f"{emoji_str} {label} {val}"
        line_utf16_len = _utf16_len(line_text)
        
        # 1. Custom Emoji entity for 🔴
        entities.append(
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=current_utf16_offset,
                length=emoji_utf16_len,
                custom_emoji_id=CUSTOM_EMOJI_ID
            )
        )
        
        # 2. Bold entity for label (e.g. "Series:")
        label_offset = current_utf16_offset + _utf16_len(f"{emoji_str} ")
        label_len = _utf16_len(label)
        entities.append(
            MessageEntity(
                type=MessageEntityType.BOLD,
                offset=label_offset,
                length=label_len
            )
        )
        
        # 3. Bold entity for series name
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
    
    # 4. Italic entity covering the whole metadata block
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
        
    # Build plain text and exact caption_entities
    caption_text, caption_entities = build_movie_caption_and_entities(
        title=title_clean,
        year=year,
        genres=genres,
        rating=rating,
        quals=quals_str,
        langs=langs_str
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
        caption=caption_text,
        caption_entities=caption_entities,
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
        
    # Build plain text and exact caption_entities
    caption_text, caption_entities = build_series_caption_and_entities(
        name=name_clean,
        year=year,
        genres=genres,
        rating=rating,
        seasons=seasons_str,
        langs=langs_str
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
        caption=caption_text,
        caption_entities=caption_entities,
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_inline_query()
async def answer(bot: Client, query: InlineQuery):
    """
    Unified Telegram Inline Mode query handler for Movie and Series filters.
    - No query: Shows newest/latest added movie & series poster gallery.
    - Search query: Runs Smart Search (exact -> normalized -> alias -> fuzzy) and returns matching posters.
    """
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

    bot_username = getattr(temp, "U_NAME", None) or getattr(getattr(bot, "me", None), "username", None) or "Bot"
    bot_username = str(bot_username).lstrip("@")

    string = query.query.strip()
    offset_str = query.offset or "0"
    offset = int(offset_str) if offset_str.isdigit() else 0

    results = []
    
    if not string:
        # ─── CASE 1: NO QUERY -> SHOW LATEST / NEW MOVIES & SERIES ─────────────
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
