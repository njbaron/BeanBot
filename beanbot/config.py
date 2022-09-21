import logging
import os

import dotenv

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")


def print_env(name: str, val: str):
    logger.info(f"loaded env {name} -> {val}")


def print():
    print_env("BOT_TOKEN", BOT_TOKEN)
    print_env("GUILD_ID", GUILD_ID)
    print_env("LOG_CHANNEL_ID", LOG_CHANNEL_ID)
