import logging
import os

LOG_LEVELS = {
    'development': logging.INFO,
    'production': logging.WARNING,
    'testing': logging.DEBUG
}

def get_log_level(environment=None):
    """Получить уровень логирования для текущего окружения"""
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    return LOG_LEVELS.get(environment, logging.WARNING)

def setup_logger(name, environment=None):
    """Настроить и вернуть логгер с правильным уровнем"""
    log_level = get_log_level(environment)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger