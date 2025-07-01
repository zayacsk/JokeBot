import logging
from telebot import types
import config

def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    return logging.getLogger(__name__)

def log_message(logger, message):
    user = message.from_user
    logger.info(f"User [{user.id}] @{user.username}: {message.text}")

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def is_group_admin(bot, chat, user_id):
    try:
        admins = bot.get_chat_administrators(chat.id)
        admin_ids = [admin.user.id for admin in admins]
        return user_id in admin_ids
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error checking admin status: {e}")
        return False

# Глобальный словарь для хранения состояний пользователей
user_states = {}

# Глобальный словарь для хранения последних отправленных шуток по chat_id
last_joke_cache = {}

def set_user_state(user_id, state):
    user_states[user_id] = state

def get_user_state(user_id):
    return user_states.get(user_id)

def delete_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]