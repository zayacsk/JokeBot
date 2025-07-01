import asyncio

# Глобальная переменная для цикла событий
loop = asyncio.new_event_loop()

def run_async(coro):
    """Запускает асинхронную корутину в глобальном цикле событий"""
    asyncio.run_coroutine_threadsafe(coro, loop)