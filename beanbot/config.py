from dataclasses import dataclass
import logging
import os
import secrets
from typing import Any, List

import dotenv

logger = logging.getLogger(__name__)

dotenv.load_dotenv()


def env_to_list(env_val: str, split_car: str = ":") -> List[Any]:
    return [item.strip() for item in env_val.split(split_car)]


BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX")
GUILD_IDS = env_to_list(os.getenv("GUILD_IDS"))
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
