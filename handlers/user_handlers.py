import logging
from telebot import types
import config
from keyboards import create_main_keyboard, create_cancel_keyboard, create_admin_keyboard
from states import set_user_state, get_user_state, delete_user_state
from utils import log_message, is_admin, last_joke_cache
from async_utils import run_async
from firebase import initialize_firebase, add_joke, get_user_jokes, get_random_joke, get_unapproved_count, subscribe_user, unsubscribe_user

logger = logging.getLogger(__name__)

def setup_user_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == '🎲 Случайная шутка' and m.chat.type == 'private')
    def random_joke(message):
        log_message(logger, message)
        run_async(process_random_joke(bot, message))

    @bot.message_handler(func=lambda m: m.text == '➕ Добавить шутку' and m.chat.type == 'private')
    def add_joke_start(message):
        log_message(logger, message)
        run_async(process_add_joke_start(bot, message))

    @bot.message_handler(func=lambda m: get_user_state(m.from_user.id) and 
                                        get_user_state(m.from_user.id).get('state') == 'adding_joke' and 
                                        m.chat.type == 'private')
    def add_joke_text(message):
        log_message(logger, message)
        run_async(process_add_joke_text(bot, message))

    @bot.message_handler(func=lambda m: m.text == '📜 Мои шутки' and m.chat.type == 'private')
    def show_user_jokes(message):
        log_message(logger, message)
        run_async(process_show_user_jokes(bot, message))

    @bot.message_handler(func=lambda m: m.text == '❌ Удалить шутку' and m.chat.type == 'private')
    def delete_joke_start(message):
        log_message(logger, message)
        run_async(process_delete_joke_start(bot, message))
    
    @bot.message_handler(func=lambda m: m.text == '🔔 Подписаться' and m.chat.type == 'private')
    def subscribe_random_jokes(message):
        log_message(logger, message)
        run_async(process_subscribe(bot, message))

    @bot.message_handler(func=lambda m: m.text == '🔕 Отписаться' and m.chat.type == 'private')
    def unsubscribe_random_jokes(message):
        log_message(logger, message)
        run_async(process_unsubscribe(bot, message))

    @bot.message_handler(func=lambda m: m.text == '🛠 Админ-панель' and 
                                        is_admin(m.from_user.id) and 
                                        m.chat.type == 'private')
    def admin_panel(message):
        log_message(logger, message)
        bot.send_message(
            message.chat.id,
            "⚙️ *Панель администратора*",
            parse_mode='Markdown',
            reply_markup=create_admin_keyboard()
        )

# Асинхронные функции обработки
async def process_random_joke(bot, message):
    try:
        chat_id = message.chat.id
        root_ref = initialize_firebase()
        
        # Получаем ID последней шутки для этого чата
        last_joke_id = last_joke_cache.get(chat_id)
        
        # Получаем случайную шутку, исключая последнюю (если есть)
        joke = await get_random_joke(root_ref, exclude_joke_id=last_joke_id)
        
        if not joke:
            bot.reply_to(message, "😢 В базе пока нет анекдотов!")
            return
        
        # Обновляем кэш последней шутки для этого чата
        last_joke_cache[chat_id] = joke['joke_id']
        
        bot.send_message(
            message.chat.id,
            f"📜 *Анекдот #{joke['joke_id']}*\n\n{joke['text']}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in random_joke: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при получении шутки")

async def process_add_joke_start(bot, message):
    try:
        user_id = message.from_user.id
        set_user_state(user_id, {'state': 'adding_joke'})
        bot.send_message(
            message.chat.id,
            "✍️ Напишите текст анекдота (минимум 10 символов):",
            reply_markup=create_cancel_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in add_joke_start: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при начале добавления шутки")

async def process_add_joke_text(bot, message):
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        if text == "❌ Отмена":
            bot.send_message(
                message.chat.id, 
                "❌ Операция отменена", 
                reply_markup=create_main_keyboard(user_id)
            )
            delete_user_state(user_id)
            return
        
        if len(text) < config.MIN_JOKE_LENGTH:
            bot.send_message(
                message.chat.id,
                f"⚠️ Текст слишком короткий! Минимум {config.MIN_JOKE_LENGTH} символов."
            )
            return
        
        # Проверка на существующий анекдот
        root_ref = initialize_firebase()
        jokes_ref = root_ref.child('jokes')
        all_jokes = jokes_ref.get() or {}
        
        # Нормализация текста для сравнения (приведение к нижнему регистру и удаление лишних пробелов)
        normalized_text = " ".join(text.lower().split())
        
        for joke in all_jokes.values():
            # Нормализация существующего текста
            existing_text = " ".join(joke.get('text', '').lower().split())
            if existing_text == normalized_text:
                bot.send_message(
                    message.chat.id,
                    "❌ Такой анекдот уже существует в базе!"
                )
                return
        
        # Добавляем анекдот с флагом approved=False
        joke_key = await add_joke(root_ref, text, user_id)
        if not joke_key:
            bot.send_message(message.chat.id, "❌ Ошибка при добавлении, попробуйте позже")
            return
        
        delete_user_state(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ Анекдот успешно добавлен и отправлен на модерацию!",
            reply_markup=create_main_keyboard(user_id)
        )
        
        # Отправляем уведомление администраторам
        await notify_admins_new_joke(bot, joke_key, text)
        
    except Exception as e:
        logger.error(f"Error in add_joke_text: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при добавлении шутки")

async def notify_admins_new_joke(bot, joke_key, text):
    """Отправляет уведомление администраторам о новом анекдоте на модерации"""
    try:
        root_ref = initialize_firebase()
        # Получаем количество анекдотов на модерации
        unapproved_count = await get_unapproved_count(root_ref)
        
        # Формируем сообщение
        message_text = (
            f"⚠️ *Новый анекдот на модерации!*\n\n"
            f"📊 Всего на модерации: {unapproved_count}\n\n"
        )
        
        # Отправляем всем админам
        for admin_id in config.ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=types.InlineKeyboardMarkup().row(
                        types.InlineKeyboardButton(
                            "👮 Перейти к модерации",
                            callback_data=f"moderate:{joke_key}"
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in notify_admins_new_joke: {e}")

async def process_show_user_jokes(bot, message):
    try:
        user_id = message.from_user.id
        root_ref = initialize_firebase()
        user_jokes = await get_user_jokes(root_ref, user_id, only_approved=True)
        
        if not user_jokes:
            bot.send_message(message.chat.id, "📭 У вас пока нет одобренных анекдотов")
            return
        
        response = "📚 *Ваши одобренные анекдоты:*\n\n"
        for key, joke in user_jokes.items():
            preview = joke['text'][:50] + '...' if len(joke['text']) > 50 else joke['text']
            response += f"🔹 *#{joke['joke_id']}*\n{preview}\n\n"
        
        bot.send_message(
            message.chat.id,
            response,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_user_jokes: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при получении ваших шуток")

async def process_delete_joke_start(bot, message):
    try:
        user_id = message.from_user.id
        root_ref = initialize_firebase()
        user_jokes = await get_user_jokes(root_ref, user_id, only_approved=True)
        
        if not user_jokes:
            bot.send_message(message.chat.id, "📭 У вас нет одобренных анекдотов для удаления")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        for key, joke in user_jokes.items():
            keyboard.add(types.InlineKeyboardButton(
                text=f"❌ #{joke['joke_id']}", 
                callback_data=f"delete:{key}"
            ))
        
        set_user_state(user_id, {'state': 'deleting_joke', 'jokes': user_jokes})
        bot.send_message(
            message.chat.id,
            "🗑 Выберите анекдот для удаления:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in delete_joke_start: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при получении списка шуток")

async def process_subscribe(bot, message):
    try:
        user_id = message.from_user.id
        root_ref = initialize_firebase()
        
        if await subscribe_user(root_ref, user_id):
            bot.reply_to(
                message,
                "✅ Вы подписаны на случайные анекдоты!\n"
                "Вы будете получать анекдоты в случайное время дня.",
                reply_markup=create_main_keyboard(user_id)
            )
        else:
            bot.reply_to(
                message,
                "⚠️ Не удалось выполнить подписку. Попробуйте позже.",
                reply_markup=create_main_keyboard(user_id)
            )
    except Exception as e:
        logger.error(f"Error in subscribe: {e}")
        bot.reply_to(
            message,
            "⚠️ Произошла ошибка при подписке.",
            reply_markup=create_main_keyboard(user_id)
        )

async def process_unsubscribe(bot, message):
    try:
        user_id = message.from_user.id
        root_ref = initialize_firebase()
        
        if await unsubscribe_user(root_ref, user_id):
            bot.reply_to(
                message,
                "❌ Вы отписаны от случайных анекдотов.\n"
                "Чтобы снова подписаться, нажмите кнопку 🔔 Подписаться.",
                reply_markup=create_main_keyboard(user_id)
            )
        else:
            bot.reply_to(
                message,
                "⚠️ Не удалось выполнить отписку. Попробуйте позже.",
                reply_markup=create_main_keyboard(user_id)
            )
    except Exception as e:
        logger.error(f"Error in unsubscribe: {e}")
        bot.reply_to(
            message,
            "⚠️ Произошла ошибка при отписке.",
            reply_markup=create_main_keyboard(user_id)
        )