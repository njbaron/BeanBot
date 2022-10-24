import logging
import os
from typing import Any, List

import dotenv

logger = logging.getLogger(__name__)

dotenv.load_dotenv()


def env_to_list(env_val: str, split_car: str = ":") -> List[Any]:
    return [item.strip() for item in env_val.split(split_car)]


BOT_DEV = os.getenv("BOT_DEV")
BOT_PREFIX = os.getenv("BOT_PREFIX")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_IDS = env_to_list(os.getenv("GUILD_IDS"))
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
