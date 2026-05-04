import logging
from typing import List
from environs import Env

logger = logging.getLogger(__name__)

# Environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# Konfiguratsiya o'zgaruvchilari
def validate_config() -> None:
    """Konfiguratsiya validatsiyasi"""
    bot_token = env.str("BOT_TOKEN", None)
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    if len(bot_token.split(":")) != 2:
        raise ValueError("Invalid BOT_TOKEN format")
    
    admins = env.list("ADMINS", None)
    if not admins:
        logger.warning("ADMINS list is empty")
    else:
        try:
            admin_ids = list(map(int, admins))
            if not all(admin_ids):
                raise ValueError("Invalid admin ID in ADMINS list")
        except ValueError as e:
            raise ValueError(f"Invalid ADMINS format: {e}")

try:
    validate_config()
    
    BOT_TOKEN: str = env.str("BOT_TOKEN")
    ADMINS: List[int] = list(map(int, env.list("ADMINS")))
    
    logger.info(f"Configuration loaded successfully. Admins: {len(ADMINS)}")
    
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise
