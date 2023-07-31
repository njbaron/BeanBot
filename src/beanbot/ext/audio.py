import asyncio
import datetime
import logging
import re
from http import HTTPStatus
from typing import Any, List
import random

import hikari
import lavalink
import lightbulb
import miru
from aiohttp import ClientSession
from lightbulb import events

from beanbot import checks, config, constants, errors, menus

logger = logging.getLogger(__name__)

audio_plugin = lightbulb.Plugin(name="Audio", description="Allows users to play audio in a voice channel.")
audio_plugin.add_checks(checks.in_guild_voice_match_bot)

RE_URL = re.compile(r"https?://(?:www\.)?.+")

THUMB_MAX_RES_URL = "https://img.youtube.com/vi/{}/maxresdefault.jpg"
THUMB_DEFAULT_RES_URL = "https://img.youtube.com/vi/{}/default.jpg"


async def task_check_and_connect_nodes():
    await asyncio.sleep(10)
    logger.debug("Starting reconnect task.")
    while True:
        lavalink_client = get_lavalink_client(audio_plugin.bot)
        for node in lavalink_client.node_manager.nodes:
            logger.debug(f"checking node {node.name}")
            if not node.available:
                logger.debug(f"attempting reconnecting to node {node.name}")
                node._ws.connect()
            else:
                logger.debug(f"node connected {node.name}")

        await asyncio.sleep(60)


def get_lavalink_client(bot: lightbulb.BotApp) -> lavalink.Client:
    if bot.d.lavalink is None:
        logger.info("Building lavalink client")
        lavalink_client = lavalink.Client(bot.get_me().id, player=AudioPlayer)
        for server in config.LAVALINK_SERVERS:
            lavalink_client.add_node(
                host=server.host,
                port=server.port,
                password=server.password,
                region=server.region,
                name=server.name,
                reconnect_attempts=1,
            )
        bot.d.lavalink = lavalink_client
        asyncio.create_task(task_check_and_connect_nodes())

    bot.d.lavalink.add_event_hook(track_hook)
    return bot.d.lavalink


async def track_hook(event: lavalink.Event) -> bool:
    if isinstance(event, lavalink.TrackStartEvent):
        track: lavalink.AudioTrack = event.track
        player: "AudioPlayer" = event.player
        logger.info(f"Started playing: {track.title}")
        await player.ui_manager.send(track)
    elif isinstance(
        event,
        (
            lavalink.TrackEndEvent,
            lavalink.TrackExceptionEvent,
            lavalink.TrackStuckEvent,
        ),
    ):
        track: lavalink.AudioTrack = event.track
        player: "AudioPlayer" = event.player
        logger.info(f"Stopped playing: {track.title}")
        await player.ui_manager.stop(track)


async def get_thumbnail(idenifier: str) -> str:
    aio_session: ClientSession = audio_plugin.bot.d.aio_session

    async with aio_session.get(THUMB_MAX_RES_URL.format(idenifier)) as response:
        if response.status == HTTPStatus.OK:
            return THUMB_MAX_RES_URL.format(idenifier)

    async with aio_session.get(THUMB_DEFAULT_RES_URL.format(idenifier)) as response:
        if response.status == HTTPStatus.OK:
            return THUMB_DEFAULT_RES_URL.format(idenifier)

    logger.warning(f"could not find a thumbnail for identifier: {idenifier}")

    return None


# class TrackSelect(miru.Select):
#     def __init__(self, *args, **kwargs) -> None:
#         super().__init__(*args, **kwargs)

#     async def callback(self, ctx: miru.Context) -> None:
#         self.view.selected = self.view.find_track_from_id(ctx.interaction.values[0])
#         await self.view.update()


# class TrackSelectView(menus.ResultView):
#     def __init__(
#         self,
#         query,
#         track_results: List[lavalink.AudioTrack],
#         placeholder: str,
#         default_result: Any = None,
#         delete_on_answer: bool = True,
#         *args,
#         **kwargs,
#     ) -> None:
#         super().__init__(default_result, delete_on_answer, *args, **kwargs)

#         self.query = query
#         self.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
#         self.selected = None

#         self.track_results = track_results
#         select_options = [
#             miru.SelectOption(
#                 track.title,
#                 track.identifier,
#                 description=track.uri,
#                 is_default=(index == 0),
#             )
#             for index, track in enumerate(track_results)
#         ]
#         select_component = TrackSelect(options=select_options, placeholder=placeholder)
#         self.add_item(select_component)

#     async def get_embed(self):
#         embed = hikari.Embed(
#             title="Choose a track!",
#             description=f"Query: `{self.query}`",
#             timestamp=self.timestamp,
#         )
#         selected = "Nothing yet."
#         if self.selected:
#             selected = f"[{self.selected.title}]({self.selected.uri})"
#         embed.add_field(
#             name="Selected",
#             value=selected,
#             inline=True,
#         )
#         if self.selected and "youtube.com" in self.selected.uri:
#             embed.set_image(await get_thumbnail(self.selected.identifier))
#         else:
#             embed.set_image(audio_plugin.bot.get_me().avatar_url)

#         embed.set_thumbnail(audio_plugin.bot.get_me().avatar_url)
#         return embed

#     async def send(self, ctx: lightbulb.Context) -> lavalink.AudioTrack:
#         embed = await self.get_embed()
#         return await super().send(ctx, embed=embed)

#     async def update(self):
#         embed = await self.get_embed()
#         await self.message.edit(embed=embed)

#     def find_track_from_id(self, track_id: str) -> lavalink.AudioTrack:
#         for track in self.track_results:
#             if track.identifier == track_id:
#                 return track
#         return None

#     @miru.button(label="Accept", style=hikari.ButtonStyle.SUCCESS)
#     async def accept_button(self, button: miru.Button, ctx: miru.Context) -> None:
#         self.result = self.selected
#         self.stop()

#     @miru.button(label="Cancel", style=hikari.ButtonStyle.DANGER)
#     async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
#         self.stop()


LOOP_ICONS = {0: "⏺", 1: "🔂", 2: "🔁"}


class TrackUi(miru.View):
    def __init__(self, player: "AudioPlayer", track: lavalink.AudioTrack) -> None:
        self.player = player
        self.track = track
        self.task = None

        timeout = datetime.timedelta(hours=4)
        super().__init__(timeout=timeout.total_seconds())

    async def view_check(self, ctx: miru.Context) -> bool:
        voice_state = audio_plugin.bot.cache.get_voice_states_view_for_channel(
            self.player.guild_id, self.player.channel_id
        )
        voice_channel_members = [item.user_id for item in voice_state.values()]
        return ctx.user.id in voice_channel_members

    async def get_embed(self):
        requester = await audio_plugin.bot.rest.fetch_user(self.track.requester)

        total_duration = datetime.timedelta(milliseconds=self.player.current.duration)
        shuffle_icon = "⏺" if not self.player.shuffle else "🔀"
        play_icon = "▶" if not self.player.paused else "⏸"
        loop_icon = LOOP_ICONS[self.player.loop]
        volume_percent = int((self.player.volume / constants.AudioConsts.MAX_VOLUME) * 100)

        if volume_percent <= 0:
            volume_icon = "🔇"
        elif volume_percent < 50:
            volume_icon = "🔉"
        else:
            volume_icon = "🔊"

        description = f"{total_duration} - {play_icon} {loop_icon} {shuffle_icon} - {volume_icon}: {volume_percent} %"

        embed = hikari.Embed(
            title=self.track.title,
            description=description,
            url=self.track.uri,
            timestamp=self.track.extra["request_time"],
            color=requester.accent_color,
        )
        upcoming = self.player.queue[0].title if len(self.player.queue) > 0 else "Nothing!"
        embed.add_field(
            name="Next up:",
            value=f"*{upcoming}*",
            inline=True,
        )
        logger.info(self.track.uri)
        if "youtube.com" in self.track.uri:
            embed.set_image(await get_thumbnail(self.track.identifier))
        else:
            embed.set_image(requester.avatar_url)

        embed.set_thumbnail(audio_plugin.bot.get_me().avatar_url)
        embed.set_footer(text=f"Requested by {requester.username}", icon=requester.avatar_url)
        return embed

    async def send(self) -> bool:
        if self.task:
            return

        channel: hikari.GuildTextChannel = await audio_plugin.bot.rest.fetch_channel(self.track.extra.get("channel_id"))
        embed = await self.get_embed()
        message = await channel.send(embed=embed, components=self.build())
        await self.start(message)
        self.task = asyncio.create_task(self.wait())

    async def update(self):
        if not self.task:
            return

        embed = await self.get_embed()
        await self.message.edit(embed=embed)

    async def stop(self):
        if not self.task:
            return
        super().stop()
        await self.message.delete()
        self.task.cancel()
        self.task = None

    @miru.button(label="⏯", style=hikari.ButtonStyle.SUCCESS)
    async def play_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await self.player.set_pause(not self.player.paused)
        await self.update()

    @miru.button(label="⏭", style=hikari.ButtonStyle.PRIMARY)
    async def next_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await self.player.skip()

    @miru.button(label="🔁", style=hikari.ButtonStyle.PRIMARY)
    async def repeat_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.player.set_loop((self.player.loop + 1) % 3)
        await self.update()

    @miru.button(label="🔀", style=hikari.ButtonStyle.PRIMARY)
    async def shuffle_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.player.set_shuffle(not self.player.shuffle)
        await self.update()

    @miru.button(label="⏹", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await self.player.stop()

    @miru.button(label="🔉", style=hikari.ButtonStyle.PRIMARY, row=2)
    async def vol_down_button(self, button: miru.Button, ctx: miru.Context) -> None:
        volume_delta = int((constants.AudioConsts.DELTA_VOLUME / 100) * constants.AudioConsts.MAX_VOLUME)
        new_volume = self.player.volume - volume_delta
        if new_volume < 0:
            await self.player.set_volume(0)
        else:
            await self.player.set_volume(self.player.volume - volume_delta)
        await self.update()

    @miru.button(label="🔊", style=hikari.ButtonStyle.PRIMARY, row=2)
    async def vol_up_button(self, button: miru.Button, ctx: miru.Context) -> None:
        volume_delta = int((constants.AudioConsts.DELTA_VOLUME / 100) * constants.AudioConsts.MAX_VOLUME)
        new_volume = self.player.volume + volume_delta
        if new_volume > constants.AudioConsts.MAX_VOLUME:
            await self.player.set_volume(constants.AudioConsts.MAX_VOLUME)
        else:
            await self.player.set_volume(self.player.volume + volume_delta)
        await self.update()

    @miru.button(label="🔇", style=hikari.ButtonStyle.PRIMARY, row=2)
    async def vol_mute_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if self.player.volume > 0:
            await self.player.set_volume(0)
        else:
            await self.player.set_volume(self.player.last_volume)
        await self.update()


class UiManager:
    def __init__(self, player: "AudioPlayer") -> None:
        self.player = player
        self._track_ui_dict = {}

    async def send(self, track: lavalink.AudioTrack) -> hikari.Message:
        track_ui = self._track_ui_dict.get(track.identifier)
        if track_ui:
            return

        track_ui = TrackUi(self.player, track)
        await track_ui.send()
        self._track_ui_dict[track.identifier] = track_ui

    async def update(self):
        for _, track_ui in self._track_ui_dict.items():
            await track_ui.update()

    async def stop(self, track: lavalink.AudioTrack):
        track_ui = self._track_ui_dict.get(track.identifier)
        if not track_ui:
            return

        await track_ui.stop()
        del self._track_ui_dict[track.identifier]

    async def destroy(self):
        for _, track_ui in self._track_ui_dict.items():
            await track_ui.stop()
        self._track_ui_dict = {}


class AudioPlayer(lavalink.DefaultPlayer):
    def __init__(self, guild_id, node):
        super().__init__(guild_id, node)
        self.ui_manager = UiManager(self)
        self.last_volume = constants.AudioConsts.DEFAULT_VOLUME

    async def connect(self, voice_channel_id: int) -> None:
        if not self.is_connected:
            await self.set_volume(constants.AudioConsts.DEFAULT_VOLUME)

        if self.channel_id != voice_channel_id:
            await audio_plugin.bot.update_voice_state(self.guild_id, voice_channel_id, self_deaf=True)

    async def disconnect(self) -> None:
        await audio_plugin.bot.update_voice_state(self.guild_id, None)
        await self.destroy()

    async def destroy(self):
        await self.ui_manager.destroy()
        return await super().destroy()

    async def set_volume(self, vol: int):
        self.last_volume = self.volume
        return await super().set_volume(vol)

    async def add_tracks_from_results(self, ctx: lightbulb.Context, query: str, results: lavalink.LoadResult) -> bool:
        queue_len = len(self.queue)

        request_time = datetime.datetime.now(tz=datetime.timezone.utc)
        for track in results.tracks:
            track.extra["channel_id"] = ctx.channel_id
            track.extra["request_time"] = request_time

        if not results or results.load_type in [
            lavalink.LoadType.LOAD_FAILED,
            lavalink.LoadType.NO_MATCHES,
        ]:
            await ctx.respond(
                f"No tracks found for `{ctx.options.query}`",
                reply=True,
                delete_after=constants.MessageConsts.DELETE_AFTER,
            )

        elif results.load_type in [lavalink.LoadType.PLAYLIST]:
            for track in results.tracks:
                self.add(track, requester=ctx.author.id)
            await ctx.respond(
                f"Added playlist with `{len(results.tracks)}` track(s) to the queue.",
                reply=True,
                delete_after=constants.MessageConsts.DELETE_AFTER,
            )

        elif results.load_type in [lavalink.LoadType.TRACK]:
            track = results.tracks[0]
            self.add(track, requester=ctx.author.id)
            await ctx.respond(
                f"Added `{track.title}` to the queue.",
                reply=True,
                delete_after=constants.MessageConsts.DELETE_AFTER,
            )

        elif results.load_type in [lavalink.LoadType.SEARCH]:
            placeholder = "Pick a track to play!"
            track = results.tracks[0]
            # track = await TrackSelectView(query, results.tracks, placeholder).send(ctx)
            if track:
                self.add(track, requester=ctx.author.id)
                await ctx.respond(
                    f"Added `{track.title}` to the queue.",
                    reply=True,
                    delete_after=constants.MessageConsts.DELETE_AFTER,
                )
            else:
                await ctx.respond(
                    "No track selected from search.",
                    reply=True,
                    delete_after=constants.MessageConsts.DELETE_AFTER,
                )

        else:
            raise errors.FindItemExcpetion(f"Unable to handle the result {results.load_type}")

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
        await player.ui_manager.destroy()


@audio_plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent):
    if event.old_state:
        channel_state = audio_plugin.bot.cache.get_voice_states_view_for_channel(
            event.guild_id, event.old_state.channel_id
        )
        if len(channel_state) == 1 and channel_state.get_item_at(0).user_id == audio_plugin.bot.get_me().id:
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


@audio_plugin.set_error_handler
async def audio_plugin_error_handler(event: events.CommandErrorEvent) -> None:
    # Unwrap the exception to get the original cause
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lavalink.errors.NodeError):
        return await event.context.respond(
            ":warning: No player nodes are connected, audio commands maybe not be available. Please try again later.",
            delete_after=constants.MessageConsts.DELETE_AFTER,
            reply=True,
        )


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
    await player.connect(ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id).channel_id)

    if ctx.options.query:
        query = ctx.options.query.strip("<>")
        if not RE_URL.match(query):
            query = f"ytsearch:{query}"
        elif "watch?v=" in query:
            query = query.split("&list=")[0]

        results: lavalink.LoadResult = await player.node.get_tracks(query)
        if not await player.add_tracks_from_results(ctx, ctx.options.query, results):
            return
        await player.ui_manager.update()

    if not (ctx.options.query and player.paused):
        if not player.is_playing:
            await player.play()
            await ctx.respond(
                "Playing audio!",
                reply=True,
                delete_after=constants.MessageConsts.DELETE_AFTER,
            )
        elif player.paused:
            await player.set_pause(False)
            await player.ui_manager.update()
            await ctx.respond(
                "Resuming audio!",
                reply=True,
                delete_after=constants.MessageConsts.DELETE_AFTER,
            )


@audio_plugin.command
@lightbulb.command("stop", "Stops all audio tells the bot to leave the voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player:
        return await ctx.respond(
            "Not connected.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if player.is_playing:
        await player.stop()
        await ctx.respond(
            "Audio stopped!",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if not player.queue:
        await player.disconnect()
        return await ctx.respond(
            "Disconnected.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if await menus.YesNoView(False, True).send(ctx, "Clear the queue and disconnect?"):
        await player.disconnect()
        return await ctx.respond(
            "Disconnected.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )


@audio_plugin.command
@lightbulb.command("pause", "Pauses the current playing track.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.is_playing:
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    await player.set_pause(True)
    await player.ui_manager.update()
    await ctx.respond("Audio paused!", reply=True, delete_after=constants.MessageConsts.DELETE_AFTER)


@audio_plugin.command
@lightbulb.command("next", "Skips to the next track.", aliases=["skip"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def next(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.is_playing:
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    current = player.current
    await player.skip()
    await ctx.respond(
        f"Skipped `{current.title}` <{current.uri}>.",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


def string_to_timedelta(string: str) -> int:
    try:
        results = [int(x or 0) for x in string.split(":")]
    except ValueError:
        raise errors.InvalidArgument('Time argument must be numbers seperated by ":"')

    if len(results) > 3:
        raise errors.InvalidArgument("Time argument must be of form HH:MM:SS, MM:SS or SS")

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
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if not ctx.options.time:
        current_position = datetime.timedelta(milliseconds=player.position)
        total_duration = datetime.timedelta(milliseconds=player.current.duration)
        return await ctx.respond(
            f"**Seek info**\nTrack: `{player.current.title}`\nCurrent time: `{current_position}`\nDuration: `{total_duration}`",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    time = string_to_timedelta(ctx.options.time)
    await player.seek(time.total_seconds() * 1000)
    await ctx.respond(
        f"Seeking to `{time}`",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


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
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    await ctx.respond(
        f"Volume is currently: `{int((player.volume / constants.AudioConsts.MAX_VOLUME) * 100)}%`",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


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
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if not ctx.options.level:
        return await ctx.respond(
            f"Volume is currently: `{int((player.volume / constants.AudioConsts.MAX_VOLUME) * 100)}%`",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if ctx.options.level < 0 or ctx.options.level > 100:
        raise errors.InvalidArgument("Volume must be between 0 and 100!")

    volume = int((ctx.options.level / 100) * constants.AudioConsts.MAX_VOLUME)
    await player.set_volume(volume)
    await player.ui_manager.update()
    await ctx.respond(
        f"Set volume to: `{ctx.options.level}%`",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


@audio_group.child
@lightbulb.option("reset", "Resets eq to default values", type=bool, required=False)
@lightbulb.command("eq", "Change the eq.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def eq_subcommand(ctx: lightbulb.Context) -> None:
    await ctx.respond(
        "Not implemented yet.",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


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
        return await ctx.respond(
            "Nothing in the queue.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    embed = hikari.Embed(
        title="Playlist:",
        description=f"Total queue: {len(player.queue)}\nTotal duration: `{datetime.timedelta(milliseconds=sum(track.duration for track in player.queue))}`",
        url=player.queue[0].uri,
        color=ctx.author.accent_color,
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    embed.set_thumbnail(audio_plugin.bot.get_me().avatar_url)
    if "youtube.com" in player.queue[0].uri:
        embed.set_image(f"https://img.youtube.com/vi/{player.queue[0].identifier}/maxresdefault.jpg")

    page_values = []
    page = 0
    total_length = 0
    for line in enumerate_playlist(player.queue):
        if total_length + len(line) > constants.EmbedConsts.MAX_FIELD_CHARS:
            embed.add_field(
                name="Next Up:" if page == 0 else "-",
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

    embed.set_footer(text=f"Requested by {ctx.author.username}", icon=ctx.author.avatar_url)

    await ctx.respond(embed=embed, reply=True, delete_after=constants.MessageConsts.DELETE_AFTER)


@playlist_group.child
@lightbulb.option("track", "The number of tracks to remove", type=int, required=True)
@lightbulb.command("remove", "Remove a track from the playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def remove_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond(
            "Nothing in the queue.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    track_index = ctx.options.track
    if 0 > track_index > len(player.queue):
        raise errors.InvalidArgument(f"Track value must be between {0} and {len(player.queue)}")

    track = player.queue[track_index]
    track_str = f"`{track_index}. '{track.title}'` <{track.uri}>"

    question = f"Do you want to remove this from the queue?\n{track_str}"
    if not await menus.YesNoView(False, True).send(ctx, question):
        return await ctx.respond(
            "Removed nothing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    player.queue.pop(track_index)
    await player.ui_manager.update()
    await ctx.respond(
        f"Removed from the queue!\n{track_str}",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


@playlist_group.child
@lightbulb.command("clear", "Remove a track from the playlist.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def clear_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond(
            "Nothing in the queue.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    question = "Do you want to clear the queue?"
    if not await menus.YesNoView(False, True).send(ctx, question):
        return await ctx.respond(
            "Did nothing!",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    player.queue.clear()
    await player.ui_manager.update()
    await ctx.respond(
        "Cleared the queue.",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


@playlist_group.child
@lightbulb.command("shuffle", "Shuffle all not played audio tracks.")
@lightbulb.implements(lightbulb.SlashSubCommand, lightbulb.PrefixSubCommand)
async def shuffle_subcommand(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if not player or not player.queue:
        return await ctx.respond(
            "Nothing in the queue.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    player.set_shuffle(not player.shuffle)
    await player.ui_manager.update()
    await ctx.respond(
        f"Set shuffle to `{player.shuffle}`",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


@playlist_group.child
@lightbulb.option(
    "loop",
    "The loop mode to set. 0 = No Loop, 1 = Single Song, 2 = Whole Queue",
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
        return await ctx.respond(
            "Nothing is playing.",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    if not ctx.options.loop:
        return await ctx.respond(
            f"Current loop mode is: `{player.loop}`",
            reply=True,
            delete_after=constants.MessageConsts.DELETE_AFTER,
        )

    try:
        player.set_loop(ctx.options.loop)
    except ValueError as ex:
        raise errors.InvalidArgument(str(ex))
    await player.ui_manager.update()
    await ctx.respond(
        f"Set loop mode to: `{player.loop}`",
        reply=True,
        delete_after=constants.MessageConsts.DELETE_AFTER,
    )


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(audio_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    lavalink_client = get_lavalink_client(bot)
    lavalink_client._event_hooks.clear()
    bot.remove_plugin(audio_plugin)
