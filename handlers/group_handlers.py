import logging
import re
from telebot import types
import config
from firebase import initialize_firebase, get_random_joke, subscribe_group, unsubscribe_group
from utils import log_message, is_group_admin, last_joke_cache
from async_utils import run_async

logger = logging.getLogger(__name__)


def setup_group_handlers(bot):
    # Регистрируем команды для бота (чтобы показывались в подсказках при вводе /)
    bot.set_my_commands([
        types.BotCommand("joke", "Получить случайный анекдот"),
        types.BotCommand("subscribe_group", "Подписать группу на анекдоты"),
        types.BotCommand("unsubscribe_group", "Отписать группу от анекдотов"),
        types.BotCommand("help", "Показать помощь по командам")
    ], scope=types.BotCommandScopeAllGroupChats())

    # Обработчик для команд в группах
    @bot.message_handler(commands=['joke', 'subscribe_group', 'unsubscribe_group', 'help', 'start'],
                         chat_types=['group', 'supergroup'])
    def handle_group_commands(message):
        log_message(logger, message)
        command = message.text.split()[0].lower()
        bot_username = bot.get_me().username.lower()

        # Проверка команды с упоминанием бота
        if command == '/joke' or command == f'/joke@{bot_username}':
            run_async(process_manual_joke_request(bot, message))
        elif command == '/subscribe_group' or command == f'/subscribe_group@{bot_username}':
            run_async(process_subscribe_group(bot, message))
        elif command == '/unsubscribe_group' or command == f'/unsubscribe_group@{bot_username}':
            run_async(process_unsubscribe_group(bot, message))
        elif command == '/help' or command == f'/help@{bot_username}' or \
                command == '/start' or command == f'/start@{bot_username}':
            run_async(process_send_group_help(bot, message))

    # Обработчик для сообщений в группах (триггер по ключевым словам)
    @bot.message_handler(
        func=lambda m: m.chat.type in ['group', 'supergroup'] and
                       any(word in (m.text or '').lower() for word in config.GROUP_TRIGGER_WORDS) and
                       not m.text.startswith('/')  # Игнорируем команды
    )
    def group_trigger(message):
        log_message(logger, message)
        run_async(process_group_trigger(bot, message))


# Асинхронные функции обработки
async def process_group_trigger(bot, message):
    try:
        chat_id = message.chat.id
        root_ref = initialize_firebase()

        # Получаем ID последней шутки для этой группы
        last_joke_id = last_joke_cache.get(chat_id)

        # Получаем случайную шутку, исключая последнюю
        joke = await get_random_joke(root_ref, exclude_joke_id=last_joke_id)

        if not joke:
            bot.reply_to(message, "😢 В базе пока нет анекдотов!")
            return

        # Обновляем кэш
        last_joke_cache[chat_id] = joke['joke_id']

        bot.reply_to(
            message,
            f"📜 *Анекдот #{joke['joke_id']}*\n\n{joke['text']}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in group_trigger: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при получении анекдота")


async def process_manual_joke_request(bot, message):
    try:
        chat_id = message.chat.id
        root_ref = initialize_firebase()

        # Получаем ID последней шутки для этой группы
        last_joke_id = last_joke_cache.get(chat_id)

        # Получаем случайную шутку, исключая последнюю
        joke = await get_random_joke(root_ref, exclude_joke_id=last_joke_id)

        if not joke:
            bot.reply_to(message, "😢 В базе пока нет анекдотов!")
            return

        # Обновляем кэш
        last_joke_cache[chat_id] = joke['joke_id']

        bot.reply_to(
            message,
            f"📜 *Анекдот #{joke['joke_id']}*\n\n{joke['text']}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in manual_joke_request: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при получении анекдота")


async def process_subscribe_group(bot, message):
    try:
        if not is_group_admin(bot, message.chat, message.from_user.id):
            bot.reply_to(message, "❌ Только администраторы группы могут подписывать на анекдоты.")
            return

        root_ref = initialize_firebase()
        group_name = message.chat.title
        if await subscribe_group(root_ref, message.chat.id, group_name):
            bot.reply_to(
                message,
                f"✅ Группа '{group_name}' подписана на случайные анекдоты!\n"
                "Теперь бот будет периодически присылать анекдоты в этот чат.\n\n"
                "Используйте команду /unsubscribe_group чтобы отписаться."
            )
        else:
            bot.reply_to(message, "⚠️ Не удалось подписать группу. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in subscribe_group: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при подписке группы")


async def process_unsubscribe_group(bot, message):
    try:
        if not is_group_admin(bot, message.chat, message.from_user.id):
            bot.reply_to(message, "❌ Только администраторы группы могут отписывать от анекдотов.")
            return

        root_ref = initialize_firebase()
        group_name = message.chat.title
        if await unsubscribe_group(root_ref, message.chat.id):
            bot.reply_to(
                message,
                f"❌ Группа '{group_name}' отписана от случайных анекдотов.\n"
                "Чтобы снова подписаться, используйте команду /subscribe_group."
            )
        else:
            bot.reply_to(message, "⚠️ Не удалось отписать группу. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in unsubscribe_group: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при отписке группы")


async def process_send_group_help(bot, message):
    try:
        text = (
            "🤖 *Помощь для групп*\n\n"
            "Используйте следующие команды:\n\n"
            "*/joke* - получить случайный анекдот\n"
            "*/subscribe_group* - подписать группу на регулярные анекдоты\n"
            "*/unsubscribe_group* - отписать группу от регулярных анекдотов\n"
            "*/help* - показать это сообщение\n\n"
            "Администраторы группы также могут использовать команды:\n"
            "*/subscribe_group* и */unsubscribe_group* для управления подпиской.\n\n"
            "Чтобы увидеть все команды, введите / в поле сообщения."
        )
        bot.send_message(
            message.chat.id,
            text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in send_group_help: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при отправке помощи")