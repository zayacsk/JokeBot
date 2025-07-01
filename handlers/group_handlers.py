import re
import logging
from telebot import types
import config
from firebase import initialize_firebase, get_random_joke, subscribe_group, unsubscribe_group
from keyboards import create_group_keyboard
from utils import log_message, is_group_admin, last_joke_cache
from async_utils import run_async

logger = logging.getLogger(__name__)

def setup_group_handlers(bot):
    # Функция для извлечения чистой команды
    def extract_command(text):
        if not text:
            return ""
        text = text.strip().lower()
        text = re.sub(r'[^\w\s/@]', '', text)
        parts = re.split(r'[@\s]', text)
        command = parts[0] if parts else ""
        
        if command.startswith('/'):
            command = command[1:]
        
        return command
    
    # Функция для нормализации команд
    def normalize_command(cmd):
        cmd = cmd.lower().replace("_", "").replace(" ", "")
        aliases = {
            "subscribegroup": "subscribe_group",
            "unsubscribegroup": "unsubscribe_group",
            "joke": "joke",
            "help": "help",
            "случайныйанекдот": "joke",
            "подписатьгруппу": "subscribe_group",
            "отписатьгруппу": "unsubscribe_group",
            "помощь": "help"
        }
        return aliases.get(cmd, cmd)
    
    # Обработчик красивых кнопок для групп
    @bot.message_handler(
        func=lambda m: m.chat.type in ['group', 'supergroup'] and 
        m.text in ["🎲 Случайный анекдот", "🔔 Подписать группу", "🔕 Отписать группу", "ℹ️ Помощь"]
    )
    def handle_group_buttons(message):
        log_message(logger, message)
        text = message.text
        
        if text == "🎲 Случайный анекдот":
            run_async(process_manual_joke_request(bot, message))
        elif text == "🔔 Подписать группу":
            run_async(process_subscribe_group(bot, message))
        elif text == "🔕 Отписать группу":
            run_async(process_unsubscribe_group(bot, message))
        elif text == "ℹ️ Помощь":
            run_async(process_send_group_help(bot, message))

    # Обработчик для сообщений в группах (триггер по ключевым словам)
    @bot.message_handler(
        func=lambda m: m.chat.type in ['group', 'supergroup'] and 
        any(word in (m.text or '').lower() for word in config.GROUP_TRIGGER_WORDS)
    )
    def group_trigger(message):
        log_message(logger, message)
        run_async(process_group_trigger(bot, message))

    # Универсальный обработчик команд для групп
    @bot.message_handler(
        func=lambda m: m.chat.type in ['group', 'supergroup'] and 
        extract_command(m.text) in ['subscribe_group', 'unsubscribe_group', 'joke', 'help',
                                    'subscribegroup', 'unsubscribegroup',
                                    'случайныйанекдот', 'подписатьгруппу', 'отписатьгруппу', 'помощь']
    )
    def handle_group_commands(message):
        log_message(logger, message)
        cmd = extract_command(message.text)
        normalized_cmd = normalize_command(cmd)
        
        if normalized_cmd == "subscribe_group":
            run_async(process_subscribe_group(bot, message))
        elif normalized_cmd == "unsubscribe_group":
            run_async(process_unsubscribe_group(bot, message))
        elif normalized_cmd == "joke":
            run_async(process_manual_joke_request(bot, message))
        elif normalized_cmd == "help":
            run_async(process_send_group_help(bot, message))

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
                "Теперь бот будет периодически присылать анекдоты в этот чат.",
                reply_markup=create_group_keyboard()
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
                "Чтобы снова подписаться, используйте команду /subscribe_group или кнопку 🔔 Подписать группу."
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
    except Exception as e:
        logger.error(f"Error in send_group_help: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при отправке помощи")