import lightbulb


class NotInVoiceChannel(lightbulb.CheckFailure):
    pass


class NotSameVoiceChannel(lightbulb.CheckFailure):
    pass


class FindItemExcpetion(Exception):
    pass


class InvalidArgument(Exception):
    pass
