import asyncio
import random
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from firebase import initialize_firebase, get_random_joke, get_subscribers, get_subscribed_groups
import config
from utils import last_joke_cache

logger = logging.getLogger(__name__)

class JokeScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.root_ref = initialize_firebase()
        self.loop = None
        self.thread_pool = ThreadPoolExecutor(max_workers=10)

    def start(self, loop):
        if self.running:
            return
            
        self.running = True
        self.loop = loop
        # Запускаем независимые задачи для пользователей и групп
        asyncio.run_coroutine_threadsafe(self._user_joke_loop(), loop)
        asyncio.run_coroutine_threadsafe(self._group_joke_loop(), loop)
        logger.info("Random joke scheduler started")

    def stop(self):
        self.running = False
        self.thread_pool.shutdown(wait=False)
        logger.info("Random joke scheduler stopped")

    async def _user_joke_loop(self):
        """Независимый цикл для отправки шуток всем пользователям"""
        while self.running:
            try:
                user_interval = config.JOKE_INTERVAL
                logger.info(f"Next user jokes batch in {user_interval} seconds")
                await asyncio.sleep(user_interval)
                if not self.running:
                    break
                await self._send_jokes_to_all_users()
            except Exception as e:
                logger.error(f"User joke loop error: {e}")
                await asyncio.sleep(10)  # Пауза при ошибке

    async def _group_joke_loop(self):
        """Независимый цикл для отправки шуток всем группам"""
        while self.running:
            try:
                group_interval = config.GROUP_JOKE_INTERVAL
                logger.info(f"Next group jokes batch in {group_interval} seconds")
                await asyncio.sleep(group_interval)
                if not self.running:
                    break
                await self._send_jokes_to_all_groups()
            except Exception as e:
                logger.error(f"Group joke loop error: {e}")
                await asyncio.sleep(10)  # Пауза при ошибке

    async def _send_jokes_to_all_users(self):
        """Отправка случайных шуток всем подписанным пользователям"""
        try:
            subscribers = await get_subscribers(self.root_ref)
            if not subscribers:
                logger.info("No subscribers for random jokes")
                return
                
            logger.info(f"Sending jokes to {len(subscribers)} users")
            
            for user_id in subscribers:
                try:
                    chat_id = user_id
                    # Получаем ID последней шутки для этого пользователя
                    last_joke_id = last_joke_cache.get(chat_id)
                    
                    # Получаем случайную шутку, исключая последнюю и только approved
                    joke = await get_random_joke(
                        self.root_ref, 
                        exclude_joke_id=last_joke_id
                    )
                    if not joke:
                        logger.warning("No jokes available for sending")
                        continue
                    
                    # Обновляем кэш для этого пользователя
                    last_joke_cache[chat_id] = joke['joke_id']
                    
                    self.thread_pool.submit(
                        self._sync_send_message,
                        user_id,
                        f"🎲 *Случайный анекдот дня!*\n\n"
                        f"📜 Анекдот #{joke['joke_id']}\n\n"
                        f"{joke['text']}"
                    )
                except Exception as e:
                    logger.error(f"Error sending joke to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error in sending jokes to users: {e}")

    async def _send_jokes_to_all_groups(self):
        """Отправка случайных шуток всем подписанным группам"""
        try:
            groups = await get_subscribed_groups(self.root_ref)
            if not groups:
                logger.info("No groups subscribed for random jokes")
                return
                
            current_time = time.time()
            logger.info(f"Sending jokes to {len(groups)} groups")
            
            for group_id, group_data in groups.items():
                try:
                    # Проверяем, не слишком ли рано отправлять в эту группу
                    last_joke_time = group_data.get('last_joke_time', 0)
                    if current_time - last_joke_time < config.GROUP_JOKE_INTERVAL:
                        logger.debug(f"Skipping group {group_id} - too soon")
                        continue
                    
                    # Получаем ID последней шутки для этой группы
                    last_joke_id = last_joke_cache.get(group_id)
                    
                    # Получаем случайную шутку, исключая последнюю и только approved
                    joke = await get_random_joke(
                        self.root_ref, 
                        exclude_joke_id=last_joke_id
                    )
                    if not joke:
                        logger.warning("No jokes available for sending")
                        continue
                    
                    # Обновляем кэш для этой группы
                    last_joke_cache[group_id] = joke['joke_id']
                    
                    # Отправляем шутку
                    self.thread_pool.submit(
                        self._send_to_group_and_update_time,
                        group_id,
                        joke,
                        current_time
                    )
                except Exception as e:
                    logger.error(f"Error sending joke to group {group_id}: {e}")
        except Exception as e:
            logger.error(f"Error in sending jokes to groups: {e}")

    def _send_to_group_and_update_time(self, group_id, joke, current_time):
        """Отправляет шутку в группу и обновляет время последней отправки"""
        text = f"🎲 *Случайный анекдот!*\n\n" \
               f"📜 Анекдот #{joke['joke_id']}\n\n" \
               f"{joke['text']}"
        
        # Пытаемся отправить сообщение
        if self._sync_send_message(group_id, text):
            # Если отправка успешна, обновляем время
            try:
                groups_ref = self.root_ref.child(config.GROUP_DB_PATH)
                groups_ref.child(str(group_id)).update({'last_joke_time': current_time})
            except Exception as e:
                logger.error(f"Error updating last joke time for group {group_id}: {e}")

    def _sync_send_message(self, chat_id, text, max_retries=3, retry_delay=2):
        """Синхронная отправка сообщения с повторными попытками"""
        attempt = 0
        while attempt < max_retries:
            try:
                self.bot.send_message(
                    chat_id,
                    text,
                    parse_mode='Markdown'
                )
                logger.debug(f"Message sent to {chat_id}")
                return True
            except requests.exceptions.ReadTimeout:
                logger.warning(f"Read timeout for {chat_id}, retrying...")
                attempt += 1
                time.sleep(retry_delay)
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {chat_id}, retrying...")
                attempt += 1
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error sending to {chat_id} (attempt {attempt}/{max_retries}): {e}")
                attempt += 1
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    
        logger.error(f"Failed to send message to {chat_id} after {max_retries} attempts")
        return False