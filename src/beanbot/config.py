import logging
import os
from pathlib import Path

import dotenv
import yaml

from beanbot.errors import ConfigException

logger = logging.getLogger(__name__)

dotenv.load_dotenv()


BOT_DEV = bool(os.getenv("BOT_DEV"))

_DEFAULT_CONFIG_FILE = Path("./configs/application.yaml")
CONFIG_FILE = _DEFAULT_CONFIG_FILE if _DEFAULT_CONFIG_FILE.exists() else Path(os.getenv("BOT_CONFIG_FILE"))

with CONFIG_FILE.open("r") as reader:
    _config = yaml.safe_load(reader)


BOT_TOKEN = _config.get("dev_token") if BOT_DEV else _config.get("token")
BOT_PREFIX = _config.get("prefix")
LOG_CHANNEL_ID = _config.get("log_channel_id")
GUILD_IDS = _config.get("guild_ids", [])


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
