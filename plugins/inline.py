# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import html
import logging
from pyrogram import Client, emoji
from pyrogram.errors import QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultPhoto,
    InlineQuery
)
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
    title_clean = html.escape(clean_series_title(title))
    
    year = str(movie.get("year", "N/A")).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    
    rating = str(movie.get("rating", "N/A")).strip()
    if not rating:
        rating = "N/A"
    elif not rating.endswith("/10") and rating != "N/A":
        rating = f"{rating}/10"
        
    raw_genres = movie.get("genres") or movie.get("genre") or "N/A"
    genres = ", ".join(raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
    genres = html.escape(genres.strip() or "N/A")
    
    raw_langs = movie.get("languages") or []
    langs_str = ", ".join(raw_langs) if isinstance(raw_langs, list) else str(raw_langs)
    langs_str = html.escape(langs_str.strip() or "N/A")
    
    raw_quals = movie.get("qualities") or []
    quals_str = ", ".join(raw_quals) if isinstance(raw_quals, list) else str(raw_quals)
    quals_str = html.escape(quals_str.strip() or "N/A")
    
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
        
    # Sent Message Caption
    caption = (
        f"<i>○ <b>Movie:</b> <b>{title_clean}</b>\n"
        f"○ <b>Year:</b> {year}\n"
        f"○ <b>Genres:</b> {genres}\n"
        f"○ <b>Rating:</b> {rating}\n"
        f"○ <b>Quality:</b> {quals_str}\n"
        f"○ <b>Languages:</b> {langs_str}</i>"
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
        caption=caption,
        reply_markup=InlineKeyboardMarkup(btn)
    )


def _build_series_inline_result(series: dict, bot_username: str) -> InlineQueryResultPhoto:
    doc_id = str(series.get("_id", ""))
    name = series.get("name") or series.get("title") or "Series"
    name_clean = html.escape(clean_series_title(name))
    
    year = str(series.get("year", "N/A")).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    
    rating = str(series.get("rating", "N/A")).strip()
    if not rating:
        rating = "N/A"
    elif not rating.endswith("/10") and rating != "N/A":
        rating = f"{rating}/10"
        
    raw_genres = series.get("genre") or series.get("genres") or "N/A"
    genres = ", ".join(raw_genres) if isinstance(raw_genres, list) else str(raw_genres)
    genres = html.escape(genres.strip() or "N/A")
    
    raw_langs = series.get("languages") or []
    langs_str = ", ".join(raw_langs) if isinstance(raw_langs, list) else str(raw_langs)
    langs_str = html.escape(langs_str.strip() or "N/A")
    
    raw_seasons = series.get("seasons") or [1]
    if isinstance(raw_seasons, list):
        seasons_count = len(raw_seasons)
        seasons_str = f"{seasons_count} Season(s)" if seasons_count > 1 else "Season 1"
    else:
        seasons_str = f"Season {raw_seasons}"
        
    raw_quals = series.get("qualities") or []
    quals_str = ", ".join(raw_quals) if isinstance(raw_quals, list) else str(raw_quals)
    quals_str = html.escape(quals_str.strip() or "N/A")
    
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
        
    # Sent Message Caption
    caption = (
        f"<i>○ <b>Series:</b> <b>{name_clean}</b>\n"
        f"○ <b>Year:</b> {year}\n"
        f"○ <b>Genres:</b> {genres}\n"
        f"○ <b>Rating:</b> {rating}\n"
        f"○ <b>Seasons:</b> {seasons_str}\n"
        f"○ <b>Languages:</b> {langs_str}</i>"
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
        caption=caption,
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
