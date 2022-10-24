from enum import IntEnum


class AudioConsts(IntEnum):
    MAX_VOLUME = 200
    DEFAULT_VOLUME = 50
    DELTA_VOLUME = 5


class MessageConsts(IntEnum):
    DELETE_AFTER = 10


class EmbedConsts(IntEnum):
    MAX_FIELD_CHARS = 1024
