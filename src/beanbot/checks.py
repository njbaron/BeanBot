import lightbulb

from beanbot import errors


def _in_guild_voice(ctx: lightbulb.Context) -> bool:
    if ctx.guild_id is None:
        raise lightbulb.OnlyInGuild("This command can only be used in a guild")

    voice_state = ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
    if not voice_state:
        raise errors.NotInVoiceChannel("Please connect to voice channel to use this")

    bot_voice_state = ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.bot.get_me().id)
    if bot_voice_state and bot_voice_state.channel_id != voice_state.channel_id:
        raise errors.NotSameVoiceChannel("You must be in the same voice channel as the bot to control it")
    return True


in_guild_voice = lightbulb.Check(_in_guild_voice)


def _in_guild_voice_match_bot(ctx: lightbulb.Context) -> bool:
    if ctx.guild_id is None:
        raise lightbulb.OnlyInGuild("This command can only be used in a guild")

    voice_state = ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
    if not voice_state:
        raise errors.NotInVoiceChannel("Connect to voice channel to use this")

    bot_voice_state = ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.bot.get_me().id)
    if bot_voice_state and bot_voice_state.channel_id != voice_state.channel_id:
        raise errors.NotSameVoiceChannel("You must be in the same voice channel as the bot")
    return True


in_guild_voice_match_bot = lightbulb.Check(_in_guild_voice_match_bot)
