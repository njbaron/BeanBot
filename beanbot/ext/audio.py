import datetime
import logging
import re
from typing import List

import hikari
import lavalink
import lightbulb

from beanbot import checks, errors, constants, menus

logger = logging.getLogger(__name__)

audio_plugin = lightbulb.Plugin(
    name="Audio", description="Allows users to play audio in a voice channel."
)
audio_plugin.add_checks(checks.in_guild_voice_match_bot)

url_rx = re.compile(r"https?://(?:www\.)?.+")


def get_lavalink_client(bot: lightbulb.BotApp) -> lavalink.Client:
    if bot.d.lavalink is None:
        logger.info("Building lavalink client")
        lavalink_client = lavalink.Client(bot.get_me().id, player=AudioPlayer)
        lavalink_client.add_node(
            "127.0.0.1", 2333, "youshallnotpass", "us_west", "local-node"
        )
        lavalink_client.add_node(
            "lavalink-server", 2333, "youshallnotpass", "us_west", "docker-node"
        )
        # lavalink_client.add_event_hook(track_hook)
        bot.d.lavalink = lavalink_client
    return bot.d.lavalink


class AudioPlayer(lavalink.DefaultPlayer):
    def __init__(self, guild_id, node):
        super().__init__(guild_id, node)

    async def connect(self, voice_channel_id: int) -> None:
        await audio_plugin.bot.update_voice_state(
            self.guild_id, voice_channel_id, self_deaf=True
        )

    async def disconnect(self) -> None:
        await audio_plugin.bot.update_voice_state(self.guild_id, None)
        await self.destroy()

    async def add_tracks_from_results(
        self, ctx: lightbulb.Context, results: lavalink.LoadResult
    ) -> bool:

        queue_len = len(self.queue)
        if not results or results.load_type in [
            lavalink.LoadType.LOAD_FAILED,
            lavalink.LoadType.NO_MATCHES,
        ]:
            await ctx.respond(
                f"No tracks found for `{ctx.options.query}`", reply=True
            )

        elif results.load_type in [lavalink.LoadType.PLAYLIST]:
            for track in results.tracks:
                self.add(track, requester=ctx.author.id)
            await ctx.respond(
                f"Added playlist with `{len(results.tracks)}` track(s) to the queue.",
                reply=True,
            )

        elif results.load_type in [lavalink.LoadType.TRACK]:
            track = results.tracks[0]
            self.add(track, requester=ctx.author.id)
            await ctx.respond(f"Added `{track.title}` to the queue.", reply=True)

        elif results.load_type in [lavalink.LoadType.SEARCH]:
            question = "What track would you like to add to the queue?"
            placeholder = "Pick a track to play!"
            track = await menus.TrackSelectView(results.tracks, placeholder).send(
                ctx, question
            )
            if track:
                self.add(track, requester=ctx.author.id)
                await ctx.respond(f"Added `{track.title}` to the queue.", reply=True)
            else:
                await ctx.respond(f"No track selected from search.", reply=True)

        else:
            raise errors.FindItemExcpetion(
                f"Unable to handle the result {results.load_type}"
            )
        
        return queue_len != len(self.queue)


#########################################################
################# Hikari Event Handlers #################
#########################################################
@audio_plugin.listener(hikari.StartedEvent)
async def start_lavalink(event: hikari.StartedEvent) -> None:
    get_lavalink_client(audio_plugin.bot)


@audio_plugin.listener(hikari.StoppingEvent)
async def stop_lavalink(event: hikari.StoppingEvent) -> None:
    lavalink_client = get_lavalink_client(audio_plugin.bot)
    for player in lavalink_client.player_manager.find_all():
        # TODO: Close all open ui
        pass


@audio_plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent):
    if event.old_state:
        channel_state = audio_plugin.bot.cache.get_voice_states_view_for_channel(
            event.guild_id, event.old_state.channel_id
        )
        if (
            len(channel_state) == 1
            and channel_state.get_item_at(0).user_id == audio_plugin.bot.get_me().id
        ):
            lavalink_client = get_lavalink_client(audio_plugin.bot)
            player: AudioPlayer = lavalink_client.player_manager.get(event.guild_id)
            if player:
                await player.disconnect()


@audio_plugin.listener(hikari.ShardPayloadEvent)
async def shard_payload_update(event: hikari.ShardPayloadEvent):
    if event.name in ["VOICE_STATE_UPDATE", "VOICE_SERVER_UPDATE"]:
        lavalink_client = get_lavalink_client(audio_plugin.bot)
        lavalink_data = {"t": event.name, "d": dict(event.payload)}
        await lavalink_client.voice_update_handler(lavalink_data)


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
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.create(guild_id=ctx.guild_id)
    await player.connect(
        ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id).channel_id
    )

    if ctx.options.query:
        query = ctx.options.query.strip("<>")
        if not url_rx.match(query):
            query = f"ytsearch:{query}"
        elif "watch?v=" in query:
            query = query.split("&list=")[0]

        results: lavalink.LoadResult = await player.node.get_tracks(query)
        if not await player.add_tracks_from_results(ctx, results):
            return

    if not (ctx.options.query and player.paused):
        if not player.is_playing:
            await player.play()
            await ctx.respond("Playing audio!", reply=True)
        elif player.paused:
            await player.set_pause(False)
            await ctx.respond("Resuming audio!", reply=True)


@audio_plugin.command
@lightbulb.command("stop", "Stops all audio tells the bot to leave the voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player:
        return await ctx.respond("Not connected.", reply=True)

    if player.is_playing:
        await player.stop()
        await ctx.respond("Audio stopped!", reply=True)

    if not player.queue:
        await player.disconnect()
        return await ctx.respond("Disconnected.", reply=True)

    if await menus.YesNoView(False, True).send(ctx, f"Clear the queue and disconnect?"):
        await player.disconnect()
        return await ctx.respond("Disconnected.", reply=True)


@audio_plugin.command
@lightbulb.command("pause", "Pauses the current playing track.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.is_playing:
        return await ctx.respond("Nothing is playing.", reply=True)

    await player.set_pause(True)
    await ctx.respond("Audio paused!", reply=True)


@audio_plugin.command
@lightbulb.command("next", "Skips to the next track.", aliases=["skip"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def next(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.is_playing:
        return await ctx.respond("Nothing is playing.", reply=True)

    current = player.current
    await player.skip()
    await ctx.respond(f"Skipped `{current.title}` <{current.uri}>.", reply=True)


def string_to_timedelta(string: str) -> int:
    try:
        results = [int(x or 0) for x in string.split(":")]
    except ValueError:
        raise errors.InvalidArgument(f'Time argument must be numbers seperated by ":"')

    if len(results) > 3:
        raise errors.InvalidArgument(
            "Time argument must be of form HH:MM:SS, MM:SS or SS"
        )

    time = datetime.timedelta()
    for index, result in enumerate(results[::-1]):
        time += datetime.timedelta(seconds=result * (60**index))

    return time


@audio_plugin.command
@lightbulb.option(
    "time",
    "The time to seek to. Must be of form HH:MM:SS, MM:SS or SS",
    type=str,
    required=False,
)
@lightbulb.command(
    "seek",
    "Seek to a position in the currently playing audio.",
)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def seek(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.is_playing:
        return await ctx.respond("Nothing is playing.", reply=True)

    if not ctx.options.time:
        current_position = datetime.timedelta(milliseconds=player.position)
        total_duration = datetime.timedelta(milliseconds=player.current.duration)
        return await ctx.respond(
            f"**Seek info**\nTrack: `{player.current.title}`\nCurrent time: `{current_position}`\nDuration: `{total_duration}`",
            reply=True
        )

    time = string_to_timedelta(ctx.options.time)
    await player.seek(time.total_seconds() * 1000)
    await ctx.respond(f"Seeking to `{time}`", reply=True)


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
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player:
        return await ctx.respond("Nothing is playing.", reply=True)

    await ctx.respond(f"Volume is currently: `{player.volume // 10}%`")

MAX_VOLUME = 200

@audio_group.child
@lightbulb.option(
    "level",
    "Percent to set the volume to.",
    type=int,
    max_value=100,
    min_value=0,
    required=False,
)
@lightbulb.command("volume", "Change the volume.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def volume_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player:
        return await ctx.respond("Nothing is playing.", reply=True)

    if not ctx.options.level:
        return await ctx.respond(f"Volume is currently: `{int((player.volume / MAX_VOLUME) * 100)}%`", reply=True)

    if ctx.options.level < 0 or ctx.options.level > 100:
        raise errors.InvalidArgument(f"Volume must be between 0 and 100!")

    volume = int((ctx.options.level / 100) * MAX_VOLUME)
    await player.set_volume(volume)
    await ctx.respond(f"Set volume to: `{ctx.options.level}%`", reply=True)


@audio_group.child
@lightbulb.option("reset", "Resets eq to default values", type=bool, required=False)
@lightbulb.command("eq", "Change the eq.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def eq_subcommand(ctx: lightbulb.Context) -> None:
    await ctx.respond(f"Not implemented yet.", reply=True)


################# PLAYLIST GROUP #################
@audio_plugin.command
@lightbulb.command("playlist", "Show and change the playlist.")
@lightbulb.implements(lightbulb.SlashCommandGroup, lightbulb.PrefixCommandGroup)
async def playlist_group(ctx: lightbulb.Context) -> None:
    pass


def enumerate_playlist(playlist: List[lavalink.AudioTrack]):
    for index, track in enumerate(playlist):
        yield f"{index}. [{track.title}]({track.uri})"


@playlist_group.child
@lightbulb.command("show", "Show the current playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def show_playlist_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond("Nothing in the queue.", reply=True)

    embed = hikari.Embed(
        title=f"Playlist:",
        description=f"Total queue: {len(player.queue)}\nTotal duration: `{datetime.timedelta(milliseconds=sum(track.duration for track in player.queue))}`",
        url=player.queue[0].uri,
        color=ctx.author.accent_color,
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    embed.set_thumbnail(audio_plugin.bot.get_me().avatar_url)
    if "youtube.com" in player.queue[0].uri:
        embed.set_image(
            f"https://img.youtube.com/vi/{player.queue[0].identifier}/maxresdefault.jpg"
        )

    page_values = []
    page = 0
    total_length = 0
    for line in enumerate_playlist(player.queue):
        if total_length + len(line) > constants.embeds.MAX_FIELD_CHARS:
            embed.add_field(
                name=f"Next Up:" if page == 0 else "-",
                value="\n".join(page_values),
                inline=True,
            )
            page_values.clear()
            page += 1
            total_length = 0
            if page > 1:
                break
        page_values.append(line)
        total_length += len(line)

    embed.set_footer(
        text=f"Requested by {ctx.author.username}", icon=ctx.author.avatar_url
    )

    await ctx.respond(embed=embed, reply=True)


@playlist_group.child
@lightbulb.option("track", "The number of tracks to remove", type=int, required=True)
@lightbulb.command("remove", "Remove a track from the playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def remove_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond("Nothing in the queue.", reply=True)

    track_index = ctx.options.track
    if 0 > track_index > len(player.queue):
        raise errors.InvalidArgument(
            f"Track value must be between {0} and {len(player.queue)}"
        )

    track = player.queue[track_index]
    track_str = f"`{track_index}. '{track.title}'` <{track.uri}>"

    question = f"Do you want to remove this from the queue?\n{track_str}"
    if not await menus.YesNoView(False, True).send(ctx, question):
        return await ctx.respond("Removed nothing.", reply=True)

    player.queue.pop(track_index)
    await ctx.respond(f"Removed from the queue!\n{track_str}", reply=True)


@playlist_group.child
@lightbulb.command("clear", "Remove a track from the playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def clear_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond("Nothing in the queue.", reply=True)

    question = "Do you want to clear the queue?"
    if not await menus.YesNoView(False, True).send(ctx, question):
        return await ctx.respond("Did nothing!", reply=True)

    player.queue.clear()
    await ctx.respond(f"Cleared the queue.", reply=True)


@playlist_group.child
@lightbulb.command("shuffle", "Shuffle all not played audio tracks.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def shuffle_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond("Nothing in the queue.", reply=True)

    player.set_shuffle(not player.shuffle)
    await ctx.respond(f"Set shuffle to `{player.shuffle}`", reply=True)


@playlist_group.child
@lightbulb.option(
    "loop",
    "The loop mode to set. 0 = No shuffle, 1 = Single Song, 2 = Whole Queue",
    choices=[0, 1, 2],
    type=int,
    required=False,
)
@lightbulb.command("repeat", "Change the loop mode of the audio.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def repeat_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player:
        return await ctx.respond("Nothing is playing.", reply=True)

    if not ctx.options.loop:
        return await ctx.respond(f"Current loop mode is: `{player.loop}`", reply=True)

    try:
        player.set_loop(ctx.options.loop)
    except ValueError as ex:
        raise errors.InvalidArgument(str(ex))
    await ctx.respond(f"Set loop mode to: `{player.loop}`", reply=True)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(audio_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(audio_plugin)
