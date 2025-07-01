import logging

logger = logging.getLogger(__name__)

def setup_error_handlers(bot):
    @bot.callback_query_handler(func=lambda call: True)
    def handle_unmatched_callback(call):
        logger.warning(f"Unmatched callback: {call.data}")
        bot.answer_callback_query(call.id, "⚠️ Действие недоступно")

    @bot.message_handler(func=lambda message: True)
    def handle_unmatched_messages(message):
        logger.warning(f"Unmatched message: {message.text}")
        
        # Пропускаем сообщения в группах - они должны обрабатываться групповыми обработчиками
        if message.chat.type in ['group', 'supergroup']:
            return
        
        if message.text and message.text.startswith('/'):
            bot.reply_to(message, "❌ Неизвестная команда. Используйте /help для справки")
        else:
            bot.reply_to(message, "🤔 Не понимаю ваше сообщение. Используйте кнопки или /help")