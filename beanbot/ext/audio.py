import asyncio
import datetime
import logging
import re
from typing import List, Optional, Union

import hikari
import lavalink
import lightbulb
import miru

logger = logging.getLogger(__name__)

audio_plugin = lightbulb.Plugin(
    name="Audio", description="Allows users to play audio in a voice channel."
)
audio_plugin.add_checks(lightbulb.checks.guild_only)

url_rx = re.compile(r"https?://(?:www\.)?.+")

#################################################
################# BASE COMMANDS #################
#################################################

@audio_plugin.command
@lightbulb.option(
    "query",
    "The search or url to play in the voice channel.",
    type=str,
    required=False,
    modifier=lightbulb.commands.OptionModifier.CONSUME_REST,
)
@lightbulb.command("play", "Plays audio")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:
    pass


@audio_plugin.command
@lightbulb.option(
    "leave", "Forces leaving the voice channel.", type=bool, required=False
)
@lightbulb.command("stop", "Stops all audio tells the bot to leave the voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    pass


@audio_plugin.command
@lightbulb.command("pause", "Pauses the current playing track.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    pass


@audio_plugin.command
@lightbulb.command("next", "Skips to the next track.", aliases=["skip"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def next(ctx: lightbulb.Context) -> None:
    pass


@audio_plugin.command
@lightbulb.option(
    "time",
    "The time to seek to.",
    type=str,
    required=False,
)
@lightbulb.command(
    "seek",
    "Seek to a position in the currently playing audio.",
)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def seek(ctx: lightbulb.Context) -> None:
    pass

##################################################
################# COMMAND GROUPS #################
##################################################


################# AUDIO GROUP #################
@audio_plugin.command
@lightbulb.command("audio", "Show and change the audio settings.")
@lightbulb.implements(lightbulb.SlashCommandGroup, lightbulb.PrefixCommandGroup)
async def audio_group(ctx: lightbulb.Context) -> None:
    pass

@audio_group.child
@lightbulb.command("show", "Show the current paramters of the audio.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def show_audio_subcommand(ctx: lightbulb.Context) -> None:
    pass

@audio_group.child
@lightbulb.option("level", "Percent to set the volume to.", type=int, max_value=100, min_value=0, required=False)
@lightbulb.command("volume", "Change the volume.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def volume_subcommand(ctx: lightbulb.Context) -> None:
    pass

@audio_group.child
@lightbulb.option("reset", "Resets eq to default values", type=bool, required=False)
@lightbulb.command("eq", "Change the eq.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def eq_subcommand(ctx: lightbulb.Context) -> None:
    pass

# @audio_group.child
# @lightbulb.command("filter", "Change the filter.")
# @lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
# async def filter_subcommand(ctx: lightbulb.Context) -> None:
#     pass

# @audio_group.child
# @lightbulb.command("gain", "Change the gain.")
# @lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
# async def gain_subcommand(ctx: lightbulb.Context) -> None:
#     pass

################# PLAYLIST GROUP #################
@audio_plugin.command
@lightbulb.command("playlist", "Show and change the playlist.")
@lightbulb.implements(lightbulb.SlashCommandGroup, lightbulb.PrefixCommandGroup)
async def playlist_group(ctx: lightbulb.Context) -> None:
    pass

@playlist_group.child
@lightbulb.command("show", "Show the current playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def show_playlist_subcommand(ctx: lightbulb.Context) -> None:
    pass

@playlist_group.child
@lightbulb.command("shuffle", "Shuffle all not played audio tracks.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def shuffle_subcommand(ctx: lightbulb.Context) -> None:
    pass

@playlist_group.child
@lightbulb.option("mode", "The loop mode to set.", choices=["0","1","2"], required=False)
@lightbulb.command("loop", "Change the loop mode of the audio.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def loop_subcommand(ctx: lightbulb.Context) -> None:
    pass

@playlist_group.child
@lightbulb.option("track", "The number of tracks to remove", type=int, required=False)
@lightbulb.command("remove", "Remove a track from the playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def remove_subcommand(ctx: lightbulb.Context) -> None:
    pass



def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(audio_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(audio_plugin)
