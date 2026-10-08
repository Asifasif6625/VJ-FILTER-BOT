# Child Bot Plugins Package
import logging

logger = logging.getLogger(__name__)

def register_child_handlers(app):
    """
    Explicitly registers all Child Bot message handlers, command handlers,
    and callback query handlers on the provided ChildBot Pyrogram Client instance.
    This guarantees that ChildBot receives and handles all Normal Filter events
    regardless of Pyrogram's automatic module discovery behavior.
    """
    if not app:
        return

    try:
        from pyrogram import filters
        from pyrogram.handlers import MessageHandler, CallbackQueryHandler
        from info import ADMINS
        from child_plugins.commands import (
            child_start_handler,
            child_about_handler,
            child_help_handler,
            child_pm_broadcast,
            child_broadcast_group
        )
        from child_plugins.normal_filter import (
            child_filter_message_handler,
            child_cb_page,
            child_cb_group,
            child_cb_disc,
            child_cb_getall,
            child_cb_stop,
            child_cb_english_reason,
            child_cb_not_in_db_reason
        )

        # Clear existing group 0 handlers to prevent duplicate accumulation on reload
        if hasattr(app, "dispatcher") and hasattr(app.dispatcher, "groups"):
            app.dispatcher.groups[0] = []

        # Register Command Handlers
        app.add_handler(MessageHandler(child_start_handler, filters.command("start") & filters.incoming), group=0)
        app.add_handler(MessageHandler(child_about_handler, filters.command("about") & filters.incoming), group=0)
        app.add_handler(MessageHandler(child_help_handler, filters.command("help") & filters.incoming), group=0)
        app.add_handler(MessageHandler(child_pm_broadcast, filters.command("broadcast") & filters.user(ADMINS)), group=0)
        app.add_handler(MessageHandler(child_broadcast_group, filters.command("grp_broadcast") & filters.user(ADMINS)), group=0)

        # Register Normal Filter Search Handler
        app.add_handler(
            MessageHandler(
                child_filter_message_handler,
                filters.text & filters.incoming & ~filters.command(["start", "about", "help", "broadcast", "grp_broadcast"])
            ),
            group=0
        )

        # Register Callback Query Handlers
        app.add_handler(CallbackQueryHandler(child_cb_page, filters.regex(r"^norm_page#")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_group, filters.regex(r"^norm_grp#")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_disc, filters.regex(r"^norm_disc")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_getall, filters.regex(r"^norm_getall#")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_stop, filters.regex(r"^norm_stop#")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_english_reason, filters.regex(r"^english_only_reason$")), group=0)
        app.add_handler(CallbackQueryHandler(child_cb_not_in_db_reason, filters.regex(r"^not_in_db_reason$")), group=0)

        logger.info("[CHILD BOT] All Normal Filter handlers explicitly registered successfully!")
    except Exception as e:
        logger.error(f"[CHILD BOT] Error registering handlers: {e}", exc_info=True)
