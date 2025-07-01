from .common_handlers import setup_common_handlers
from .user_handlers import setup_user_handlers
from .admin_handlers import setup_admin_handlers
from .callback_handlers import setup_callback_handlers
from .group_handlers import setup_group_handlers
from .error_handlers import setup_error_handlers

def setup_all_handlers(bot):
    setup_common_handlers(bot)
    setup_user_handlers(bot)
    setup_admin_handlers(bot)
    setup_callback_handlers(bot)
    setup_group_handlers(bot)
    setup_error_handlers(bot)