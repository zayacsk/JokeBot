import telebot
import config
import logging
from utils import setup_logging
from handlers.init import setup_all_handlers
from scheduler import JokeScheduler
from async_utils import loop, run_async
import time
import requests

logger = setup_logging()

bot = telebot.TeleBot(config.BOT_TOKEN)
logger.info("Bot initialized")

setup_all_handlers(bot)

if __name__ == "__main__":
    logger.info("Starting bot...")
    max_restarts = 5
    restart_delay = 30
    
    import threading
    threading.Thread(target=loop.run_forever, daemon=True).start()
    
    try:
        joke_scheduler = JokeScheduler(bot)
        
        if config.RANDOM_JOKE_ENABLED:
            joke_scheduler.start(loop)
            logger.info("Random joke scheduler enabled")
        
        restart_count = 0
        while restart_count < max_restarts:
            try:
                bot.infinity_polling(
                    timeout=config.REQUEST_TIMEOUT,
                    long_polling_timeout=config.LONG_POLLING_TIMEOUT
                )
            except requests.exceptions.ReadTimeout:
                logger.warning("Read timeout occurred, restarting polling...")
                restart_count += 1
                time.sleep(restart_delay)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                restart_count += 1
                time.sleep(restart_delay)
                
        logger.critical("Maximum restart attempts reached, exiting")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
    finally:
        if config.RANDOM_JOKE_ENABLED:
            joke_scheduler.stop()