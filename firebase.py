import firebase_admin
from firebase_admin import credentials, db
import random
import logging
import os
import config
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Глобальная ссылка на корень базы данных
root_ref = None

def initialize_firebase():
    global root_ref
    if root_ref is not None:
        return root_ref
        
    # Проверяем наличие файла с учетными данными
    if not os.path.exists(config.FIREBASE_CREDENTIALS_FILE):
        logger.error(f"Firebase credentials file not found: {config.FIREBASE_CREDENTIALS_FILE}")
        raise FileNotFoundError(f"Firebase credentials file not found: {config.FIREBASE_CREDENTIALS_FILE}")
    
    try:
        cred = credentials.Certificate(config.FIREBASE_CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred, {'databaseURL': config.FIREBASE_DATABASE_URL})
        root_ref = db.reference('/')
        logger.info("Firebase initialized successfully")
        return root_ref
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        raise

async def get_next_approved_id(root_ref):
    """Получает следующий ID для одобренного анекдота"""
    try:
        counter_ref = root_ref.child('approved_counter')
        current_value = counter_ref.get() or 0
        new_value = current_value + 1
        counter_ref.set(new_value)
        return new_value
    except Exception as e:
        logger.error(f"Error updating approved joke counter: {e}")
        return None

async def get_approved_jokes_count(root_ref):
    """Получает количество одобренных анекдотов"""
    try:
        counter = root_ref.child('approved_counter').get()
        return counter or 0
    except Exception as e:
        logger.error(f"Error getting approved jokes count: {e}")
        return 0

async def get_total_jokes_count(root_ref):
    """Получает общее количество анекдотов (включая неодобренные)"""
    try:
        jokes = root_ref.child('jokes').get()
        return len(jokes) if jokes else 0
    except Exception as e:
        logger.error(f"Error getting total jokes count: {e}")
        return 0

async def get_user_jokes(root_ref, user_id, only_approved=True):
    try:
        jokes_ref = root_ref.child('jokes')
        all_jokes = jokes_ref.get() or {}
        
        # Фильтрация по пользователю и approved
        user_jokes = {}
        for key, joke in all_jokes.items():
            if joke.get('user_id') == user_id:
                if not only_approved or joke.get('approved', False):
                    user_jokes[key] = joke
        return user_jokes
    except Exception as e:
        logger.error(f"Error getting user jokes: {e}")
        return {}

async def find_joke_by_key(root_ref, joke_key):
    """Находит анекдот по ключу в базе данных"""
    try:
        joke_ref = root_ref.child(f'jokes/{joke_key}')
        joke = joke_ref.get()
        return joke if joke else None
    except Exception as e:
        logger.error(f"Error finding joke by key: {e}")
        return None

async def find_joke_by_id(root_ref, joke_id):
    """Находит анекдот по ID (только для одобренных)"""
    try:
        jokes_ref = root_ref.child('jokes')
        jokes = jokes_ref.get() or {}
        
        for key, joke in jokes.items():
            if joke.get('joke_id') == joke_id:
                return key, joke
        return None, None
    except Exception as e:
        logger.error(f"Error finding joke by ID: {e}")
        return None, None

async def get_random_joke(root_ref, exclude_joke_id=None):
    try:
        jokes_ref = root_ref.child('jokes')
        jokes = jokes_ref.get()
        if not jokes:
            return None

        # Фильтрация по approved
        approved_jokes = {k: v for k, v in jokes.items() if v.get('approved', False)}
            
        # Если указан exclude_joke_id, отфильтруем шутки
        if exclude_joke_id is not None:
            # Создаем новый словарь без шутки с указанным ID
            filtered_jokes = {key: joke for key, joke in approved_jokes.items() 
                             if joke.get('joke_id') != exclude_joke_id}
            # Если после фильтрации остались шутки, используем их
            if filtered_jokes:
                approved_jokes = filtered_jokes
            else:
                logger.warning(f"No jokes available after excluding joke {exclude_joke_id}. Returning random from all.")
        
        # Выбираем случайную шутку
        if not approved_jokes:
            return None
        _, joke = random.choice(list(approved_jokes.items()))
        return joke
    except Exception as e:
        logger.error(f"Error getting random joke: {e}")
        return None

async def subscribe_user(root_ref, user_id):
    try:
        ref = root_ref.child('subscribers').child(str(user_id))
        ref.set(True)
        return True
    except Exception as e:
        logger.error(f"Error subscribing user: {e}")
        return False

async def unsubscribe_user(root_ref, user_id):
    try:
        ref = root_ref.child('subscribers').child(str(user_id))
        ref.delete()
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing user: {e}")
        return False

async def get_subscribers(root_ref):
    try:
        ref = root_ref.child('subscribers')
        subscribers = ref.get() or {}
        return list(subscribers.keys())
    except Exception as e:
        logger.error(f"Error getting subscribers: {e}")
        return []

async def subscribe_group(root_ref, chat_id, group_name=None):
    try:
        groups_ref = root_ref.child(config.GROUP_DB_PATH)
        group_data = {
            'subscribed': True,
            'name': group_name or f"Group {chat_id}",
            'last_joke_time': None
        }
        groups_ref.child(str(chat_id)).set(group_data)
        return True
    except Exception as e:
        logger.error(f"Error subscribing group: {e}")
        return False

async def unsubscribe_group(root_ref, chat_id):
    try:
        groups_ref = root_ref.child(config.GROUP_DB_PATH)
        groups_ref.child(str(chat_id)).delete()
        return True
    except Exception as e:
        logger.error(f"Error unsubscribing group: {e}")
        return False

async def get_subscribed_groups(root_ref):
    try:
        groups_ref = root_ref.child(config.GROUP_DB_PATH)
        groups = groups_ref.get() or {}
        return {int(gid): data for gid, data in groups.items() if data.get('subscribed')}
    except Exception as e:
        logger.error(f"Error getting group subscribers: {e}")
        return {}

async def add_joke(root_ref, text, user_id):
    """Добавляет новый анекдот без ID (до модерации)"""
    try:
        jokes_ref = root_ref.child('jokes')
        new_joke_ref = jokes_ref.push({
            'text': text,
            'user_id': user_id,
            'approved': False,
            'created_at': datetime.now().isoformat(),
            'joke_id': None  # Будет установлен после модерации
        })
        return new_joke_ref.key
    except Exception as e:
        logger.error(f"Error adding joke: {e}")
        return None

async def get_unapproved_joke(root_ref):
    """Получает один неодобренный анекдот"""
    try:
        jokes_ref = root_ref.child('jokes')
        jokes = jokes_ref.get() or {}
        
        for key, joke in jokes.items():
            if not joke.get('approved', False):
                return key, joke
        return None, None
    except Exception as e:
        logger.error(f"Error getting unapproved joke: {e}")
        return None, None

async def get_unapproved_count(root_ref):
    """Получает количество неодобренных анекдотов"""
    try:
        jokes_ref = root_ref.child('jokes')
        jokes = jokes_ref.get() or {}
        
        count = 0
        for joke in jokes.values():
            if not joke.get('approved', False):
                count += 1
        return count
    except Exception as e:
        logger.error(f"Error getting unapproved count: {e}")
        return 0

async def approve_joke(root_ref, joke_key):
    """Одобряет анекдот и назначает ему ID"""
    try:
        # Получаем следующий ID для одобренных анекдотов
        joke_id = await get_next_approved_id(root_ref)
        if joke_id is None:
            return False
            
        jokes_ref = root_ref.child('jokes')
        update_data = {
            'approved': True,
            'joke_id': joke_id,
            'approved_at': datetime.now().isoformat()
        }
        jokes_ref.child(joke_key).update(update_data)
        return True
    except Exception as e:
        logger.error(f"Error approving joke: {e}")
        return False

async def delete_joke(root_ref, joke_key):
    """Удаляет анекдот"""
    try:
        jokes_ref = root_ref.child('jokes')
        jokes_ref.child(joke_key).delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting joke: {e}")
        return False