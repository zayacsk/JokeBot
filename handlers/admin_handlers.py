import logging
from telebot import types
from firebase import (
    initialize_firebase,
    get_approved_jokes_count,
    get_total_jokes_count,
    find_joke_by_id,
    get_unapproved_joke,
    approve_joke,
    delete_joke,
    find_joke_by_key
)
from keyboards import create_admin_keyboard, create_cancel_keyboard, create_moderation_reply_keyboard
from states import set_user_state, get_user_state, delete_user_state
from utils import is_admin, log_message
import config
from async_utils import run_async

logger = logging.getLogger(__name__)

def setup_admin_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == '🗑 Удалить по ID' and 
                                        is_admin(m.from_user.id) and 
                                        m.chat.type == 'private')
    def admin_delete_start(message):
        log_message(logger, message)
        run_async(process_admin_delete_start(bot, message))

    @bot.message_handler(func=lambda m: get_user_state(m.from_user.id) and 
                                        get_user_state(m.from_user.id).get('state') == 'admin_deleting' and 
                                        m.chat.type == 'private')
    def admin_delete_joke(message):
        log_message(logger, message)
        run_async(process_admin_delete_joke(bot, message))

    @bot.message_handler(func=lambda m: m.text == '📊 Статистика' and 
                                        is_admin(m.from_user.id) and 
                                        m.chat.type == 'private')
    def show_stats(message):
        log_message(logger, message)
        run_async(process_show_stats(bot, message))
        
    @bot.message_handler(func=lambda m: m.text == '👮 Модерация' and 
                                        is_admin(m.from_user.id) and 
                                        m.chat.type == 'private')
    def moderation_start(message):
        log_message(logger, message)
        run_async(process_moderation_start(bot, message))

    @bot.message_handler(func=lambda m: get_user_state(m.from_user.id) and 
                                        get_user_state(m.from_user.id).get('state') == 'moderation' and 
                                        m.chat.type == 'private')
    def handle_moderation_action(message):
        log_message(logger, message)
        run_async(process_moderation_action(bot, message))

# Асинхронные функции обработки
async def process_admin_delete_start(bot, message):
    try:
        user_id = message.from_user.id
        set_user_state(user_id, {'state': 'admin_deleting'})
        bot.send_message(
            message.chat.id,
            "🔢 Введите ID анекдота для удаления:",
            reply_markup=create_cancel_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in admin_delete_start: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при начале удаления")

async def process_admin_delete_joke(bot, message):
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        if text == "❌ Отмена":
            bot.send_message(
                message.chat.id, 
                "❌ Операция отменена", 
                reply_markup=create_admin_keyboard()
            )
            delete_user_state(user_id)
            return
        
        try:
            joke_id = int(text)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Некорректный ID. Введите число:")
            return
        
        root_ref = initialize_firebase()
        key, joke = await find_joke_by_id(root_ref, joke_id)
        if not joke:
            bot.send_message(message.chat.id, "🔍 Анекдот с таким ID не найден")
            return
        
        try:
            # Используем функцию delete_joke вместо fb_delete_joke
            await delete_joke(root_ref, key)
            logger.info(f"Admin {user_id} deleted joke {joke_id} (key: {key})")
        except Exception as e:
            logger.error(f"Admin delete error: {e}")
            bot.send_message(message.chat.id, "❌ Ошибка при удалении")
            return
        
        delete_user_state(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ Анекдот #{joke_id} успешно удален!",
            reply_markup=create_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in admin_delete_joke: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при удалении анекдота")

async def process_show_stats(bot, message):
    try:
        root_ref = initialize_firebase()
        approved_count = await get_approved_jokes_count(root_ref)
        total_count = await get_total_jokes_count(root_ref)
        last_id = root_ref.child('approved_counter').get() or 0

        bot.send_message(
            message.chat.id,
            f"📈 *Статистика бота:*\n\n"
            f"• Одобрено анекдотов: *{approved_count}*\n"
            f"• Последний ID одобренного: *{last_id}*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        bot.reply_to(message, "⚠️ Ошибка при получении статистики")

async def process_moderation_start(bot, message):
    try:
        user_id = message.from_user.id
        root_ref = initialize_firebase()
        
        # Получаем первый неодобренный анекдот
        key, joke = await get_unapproved_joke(root_ref)
        
        if not joke:
            bot.send_message(
                message.chat.id,
                "🎉 Все анекдоты прошли модерацию! Нет новых для проверки.",
                reply_markup=create_admin_keyboard()
            )
            return
        
        # Сохраняем состояние модерации
        set_user_state(user_id, {
            'state': 'moderation',
            'current_joke_key': key,
            'joke_id': joke.get('joke_id', 'N/A')
        })
        
        # Отправляем анекдот на модерацию
        bot.send_message(
            message.chat.id,
            f"📜 *Новый анекдот на модерации (ID будет назначен после одобрения):*\n\n"
            f"{joke['text']}\n\n"
            f"Выберите действие:",
            parse_mode='Markdown',
            reply_markup=create_moderation_reply_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in moderation_start: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при запуске модерации")

async def process_moderation_action(bot, message):
    try:
        user_id = message.from_user.id
        user_state = get_user_state(user_id)
        
        if not user_state or user_state.get('state') != 'moderation':
            bot.send_message(
                message.chat.id, 
                "❌ Сессия модерации устарела",
                reply_markup=create_admin_keyboard()
            )
            return
        
        action = message.text
        root_ref = initialize_firebase()
        joke_key = user_state['current_joke_key']
        
        if action == "✅ Одобрить":
            if await approve_joke(root_ref, joke_key):
                joke = await find_joke_by_key(root_ref, joke_key)
                response = f"✅ Анекдот #{joke['joke_id']} одобрен!"
            else:
                response = "❌ Ошибка при одобрении анекдота"
                
        elif action == "❌ Отклонить":
            if await delete_joke(root_ref, joke_key):
                response = f"❌ Анекдот отклонен и удален!"
            else:
                response = "❌ Ошибка при удалении анекдота"
                
        elif action == "➡️ Следующий":
            response = f"➡️ Переходим к следующему анекдоту"
            
        elif action == "🚫 Завершить":
            delete_user_state(user_id)
            bot.send_message(
                message.chat.id,
                "🚫 Модерация завершена",
                reply_markup=create_admin_keyboard()
            )
            return
        else:
            bot.reply_to(message, "❌ Неизвестное действие, используйте кнопки")
            return
        
        # Получаем следующий анекдот для модерации
        next_key, next_joke = await get_unapproved_joke(root_ref)
        
        if next_joke:
            # Обновляем состояние для следующего анекдота
            set_user_state(user_id, {
                'state': 'moderation',
                'current_joke_key': next_key,
                'joke_id': next_joke.get('joke_id', 'N/A')
            })
            
            # Отправляем результат действия и следующий анекдот
            bot.send_message(
                message.chat.id,
                f"{response}\n\n"
                f"📜 *Следующий анекдот на модерации:*\n\n"
                f"{next_joke['text']}",
                parse_mode='Markdown',
                reply_markup=create_moderation_reply_keyboard()
            )
        else:
            # Нет больше анекдотов для модерации
            delete_user_state(user_id)
            bot.send_message(
                message.chat.id,
                f"{response}\n\n🎉 Все анекдоты прошли модерацию!",
                reply_markup=create_admin_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in moderation_action: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка при обработке действия",
            reply_markup=create_admin_keyboard()
        )