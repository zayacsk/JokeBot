import requests
import time
import logging

logger = logging.getLogger(__name__)

class RobustSession(requests.Session):
    """Сессия с повторными попытками и обработкой сетевых сбоев"""
    
    def request(self, method, url, max_retries=5, retry_delay=2, **kwargs):
        """Выполняет запрос с повторными попытками при сбоях"""
        attempt = 0
        while attempt < max_retries:
            try:
                response = super().request(method, url, **kwargs)
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Request failed with status {response.status_code}, retrying...")
            except (requests.ConnectionError, requests.Timeout) as e:
                logger.warning(f"Network error: {str(e)}, retrying...")
            except Exception as e:
                logger.error(f"Unexpected request error: {str(e)}")
                raise
            
            attempt += 1
            if attempt < max_retries:
                time.sleep(retry_delay)
        
        raise ConnectionError(f"Failed after {max_retries} attempts")