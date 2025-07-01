import logging
from telebot import types
from firebase import approve_joke, delete_joke, find_joke_by_key, initialize_firebase
from keyboards import create_admin_keyboard, create_moderation_reply_keyboard
from states import get_user_state, set_user_state, delete_user_state
from utils import log_message
from async_utils import run_async
import config

logger = logging.getLogger(__name__)

def setup_callback_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete:'))
    def handle_joke_delete(call):
        run_async(process_joke_delete(bot, call))
        
    @bot.callback_query_handler(func=lambda call: call.data in ['approve', 'reject', 'skip', 'cancel_mod'])
    def handle_moderation_actions(call):
        # Этот обработчик теперь не нужен, но оставим для совместимости
        bot.answer_callback_query(call.id, "⚠️ Действие устарело, используйте новую модерацию")
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith('moderate:'))
    def handle_moderate_callback(call):
        run_async(process_moderate_callback(bot, call))

# Асинхронные функции обработки
async def process_joke_delete(bot, call):
    try:
        user_id = call.from_user.id
        joke_key = call.data.split(':')[1]
        
        user_state = get_user_state(user_id)
        if not user_state or 'jokes' not in user_state:
            bot.answer_callback_query(call.id, "❌ Сессия устарела")
            return
        
        if joke_key not in user_state['jokes']:
            bot.answer_callback_query(call.id, "❌ Анекдот не найден")
            return
        
        root_ref = initialize_firebase()
        try:
            jokes_ref = root_ref.child('jokes')
            jokes_ref.child(joke_key).delete()
            logger.info(f"User {user_id} deleted joke {joke_key}")
        except Exception as e:
            logger.error(f"Error deleting joke: {e}")
            bot.answer_callback_query(call.id, "❌ Ошибка при удалении")
            return
        
        delete_user_state(user_id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ Анекдот успешно удален!"
        )
    except Exception as e:
        logger.error(f"Error in handle_joke_delete: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка")

async def process_moderate_callback(bot, call):
    try:
        joke_key = call.data.split(':')[1]
        user_id = call.from_user.id
        
        if user_id not in config.ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Только администраторы могут модерировать анекдоты")
            return
        
        root_ref = initialize_firebase()
        joke = await find_joke_by_key(root_ref, joke_key)
        
        if not joke:
            bot.answer_callback_query(call.id, "❌ Анекдот не найден или уже промодерирован")
            return
        
        # Сохраняем состояние модерации
        set_user_state(user_id, {
            'state': 'moderation',
            'current_joke_key': joke_key,
            'joke_id': joke.get('joke_id', 'N/A')
        })
        
        # Редактируем сообщение с уведомлением
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📜 *Анекдот на модерации (ID будет назначен после одобрения):*\n\n{joke['text']}",
            parse_mode='Markdown',
            reply_markup=None  # Убираем inline-кнопки
        )
        
        # Отправляем новое сообщение с reply-клавиатурой
        bot.send_message(
            call.message.chat.id,
            "Выберите действие для этого анекдота:",
            reply_markup=create_moderation_reply_keyboard()
        )
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in process_moderate_callback: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка")