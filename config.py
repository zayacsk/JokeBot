# Telegram Bot Token
BOT_TOKEN = ""

# Admin User IDs
ADMIN_IDS = []

# Firebase Settings
FIREBASE_DATABASE_URL = ""
FIREBASE_CREDENTIALS_FILE = ".json"

# Application Settings
MIN_JOKE_LENGTH = 10

# Random joke settings
RANDOM_JOKE_ENABLED = True
JOKE_INTERVAL = 12 * 60 * 60

# Group settings
GROUP_DB_PATH = "groups"  # Отдельная ветка в Firebase для групп
GROUP_TRIGGER_WORDS = ["анекдот", "шутка", "расскажи смешное"]  # Триггерные слова
GROUP_JOKE_INTERVAL = 12 * 60 * 60

# Thread pool settings
USER_THREAD_POOL_SIZE = 20  # Для обработки пользовательских запросов
SCHEDULER_THREAD_POOL_SIZE = 10  # Для отправки запланированных сообщений

# Network settings
REQUEST_TIMEOUT = 120
LONG_POLLING_TIMEOUT = 100
MAX_NETWORK_RETRIES = 5

