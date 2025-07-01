from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config

def create_main_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        KeyboardButton("🎲 Случайная шутка"),
        KeyboardButton("➕ Добавить шутку"),
        KeyboardButton("📜 Мои шутки"),
        KeyboardButton("❌ Удалить шутку"),
        KeyboardButton("🔔 Подписаться"),
        KeyboardButton("🔕 Отписаться")
    ]
    if user_id in config.ADMIN_IDS:
        buttons.append(KeyboardButton("🛠 Админ-панель"))
    keyboard.add(*buttons)
    return keyboard

def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("🗑 Удалить по ID"),
        KeyboardButton("📊 Статистика"),
        KeyboardButton("👮 Модерация"),
        KeyboardButton("🔙 Главное меню")
    ]
    keyboard.add(*buttons)
    return keyboard

def create_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

def create_group_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("🎲 Случайный анекдот"),
        KeyboardButton("🔔 Подписать группу"),
        KeyboardButton("🔕 Отписать группу"),
        KeyboardButton("ℹ️ Помощь")
    ]
    keyboard.row(buttons[0])
    keyboard.row(buttons[1], buttons[2])
    keyboard.row(buttons[3])
    return keyboard

def create_moderation_reply_keyboard():
    """Создаёт клавиатуру для модерации с reply-кнопками"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("✅ Одобрить"),
        KeyboardButton("❌ Отклонить"),
        KeyboardButton("➡️ Следующий"),
        KeyboardButton("🚫 Завершить")
    ]
    keyboard.add(*buttons)
    return keyboard