import logging
from telebot import types
from keyboards import create_main_keyboard, create_group_keyboard
from states import delete_user_state
from utils import is_admin, log_message

logger = logging.getLogger(__name__)

import logging
from telebot import types
from keyboards import create_main_keyboard, create_group_keyboard
from utils import is_admin, log_message

logger = logging.getLogger(__name__)

def setup_common_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        log_message(logger, message)
        user_id = message.from_user.id
        
        if message.chat.type in ['group', 'supergroup']:
            # Помощь для групп
            text = (
                "🤖 *Помощь для групп*\n\n"
                "Вы можете использовать кнопки или команды:\n\n"
                "🎲 *Случайный анекдот* - получить случайный анекдот\n"
                "🔔 *Подписать группу* - подписать группу на регулярные анекдоты\n"
                "🔕 *Отписать группу* - отписать группу от регулярных анекдотов\n"
                "ℹ️ *Помощь* - показать это сообщение\n\n"
                "Или команды:\n"
                "/joke - случайный анекдот\n"
                "/subscribe_group - подписать группу\n"
                "/unsubscribe_group - отписать группу\n"
                "/help - помощь"
            )
            bot.send_message(
                message.chat.id, 
                text, 
                parse_mode='Markdown',
                reply_markup=create_group_keyboard()
            )
        else:
            # Помощь для личных сообщений
            text = (
                "🤖 *Добро пожаловать в Бот-Анекдот!*\n\n"
                "Используйте кнопки для управления:\n"
                "🎲 Случайная шутка - получить случайный анекдот\n"
                "➕ Добавить шутку - добавить новый анекдот\n"
                "📜 Мои шутки - просмотреть ваши анекдоты\n"
                "❌ Удалить шутку - удалить ваш анекдот\n"
                "🔔 Подписаться - получать анекдоты автоматически\n"
                "🔕 Отписаться - отменить автоматическую рассылку"
            )
            if is_admin(user_id):
                text += "\n\n🛠 *Режим администратора:*\n"
                text += "🛠 Админ-панель - управление ботом\n"
                text += "🗑 Удалить по ID - удалить любой анекдот\n"
                text += "📊 Статистика - статистика бота"
            
            bot.send_message(
                message.chat.id, 
                text, 
                parse_mode='Markdown',
                reply_markup=create_main_keyboard(user_id)
            )

    @bot.message_handler(func=lambda m: m.text == '❌ Отмена' and m.chat.type == 'private')
    def cancel_operation(message):
        log_message(logger, message)
        user_id = message.from_user.id
        # Очищаем состояние пользователя
        delete_user_state(user_id)
        bot.send_message(
            message.chat.id, 
            "❌ Операция отменена", 
            reply_markup=create_main_keyboard(user_id)
        )

    @bot.message_handler(func=lambda m: m.text == '🔙 Главное меню' and m.chat.type == 'private')
    def back_to_main(message):
        log_message(logger, message)
        user_id = message.from_user.id
        bot.send_message(
            message.chat.id,
            "🏠 Возвращаемся в главное меню",
            reply_markup=create_main_keyboard(user_id)
        )

    @bot.message_handler(func=lambda m: m.text == '❌ Отмена')
    def cancel_operation(message):
        log_message(logger, message)
        user_id = message.from_user.id
        bot.send_message(
            message.chat.id, 
            "❌ Операция отменена", 
            reply_markup=create_main_keyboard(user_id)
        )

    @bot.message_handler(func=lambda m: m.text == '🔙 Главное меню')
    def back_to_main(message):
        log_message(logger, message)
        user_id = message.from_user.id
        bot.send_message(
            message.chat.id,
            "🏠 Возвращаемся в главное меню",
            reply_markup=create_main_keyboard(user_id)
        )