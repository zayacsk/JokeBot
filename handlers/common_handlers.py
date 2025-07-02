import logging
from telebot import types
from keyboards import create_main_keyboard
from states import delete_user_state
from utils import is_admin, log_message
from async_utils import run_async

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
                "Используйте следующие команды:\n\n"
                "*/joke* - получить случайный анекдот\n"
                "*/subscribe_group* - подписать группу на регулярные анекдоты\n"
                "*/unsubscribe_group* - отписать группу от регулярных анекдотов\n"
                "*/help* - показать справку\n\n"
                "Чтобы увидеть все команды, введите / в поле сообщения."
            )
            bot.send_message(
                message.chat.id,
                text,
                parse_mode='Markdown'
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