import logging
import os
from pathlib import Path
from typing import Any

import dotenv
import yaml

from beanbot.errors import ConfigException

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

_DEFAULT_CONFIG_FILE = Path("./configs/application.yaml")

BOT_DEV = bool(os.getenv("BOT_DEV"))
CONFIG_FILE = _DEFAULT_CONFIG_FILE if _DEFAULT_CONFIG_FILE.exists() else Path(os.getenv("BOT_CONFIG_FILE"))

_config = yaml.safe_load(CONFIG_FILE.read_text())


def get_key(config: dict, key: str, default: Any = None) -> Any:
    if BOT_DEV:
        dev_key = f"dev_{key}"
        logger.info(f"Loading dev config {dev_key}")
        if dev_key in config.keys():
            return config.get(dev_key)
        logger.warning(f"Failed to load dev key {dev_key}")

    return config.get(key, default)


BOT_TOKEN = get_key(_config, "token")
BOT_PREFIX = get_key(_config, "prefix")
LOG_CHANNEL_ID = get_key(_config, "log_channel_id")
GUILD_IDS = get_key(_config, "guild_ids")


class LavalinkServer:
    def __init__(self, config_dict: dict) -> None:
        try:
            self.name = config_dict["name"]
            self.host = config_dict["host"]
            self.port = config_dict["port"]
            self.password = config_dict["password"]
            self.region = config_dict["region"]
        except KeyError as ex:
            raise ConfigException(f"LavalinkServer failed to find {ex} key in {CONFIG_FILE}:{config_dict}")


LAVALINK_SERVERS = [LavalinkServer(item) for item in _config.get("lavalink", [])]
