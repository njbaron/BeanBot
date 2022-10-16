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


class FindItemExcpetion(Exception):
    pass


async def track_hook(event: lavalink.Event) -> bool:
    if isinstance(event, lavalink.TrackStartEvent):
        track: lavalink.AudioTrack = event.track
        player: "AudioPlayer" = event.player
        logger.info(f"Started playing {track.identifier}")
        await player.send_embed(track)
    if isinstance(event, lavalink.TrackEndEvent):
        track: lavalink.AudioTrack = event.track
        player: "AudioPlayer" = event.player
        logger.info(f"Stopped playing {track.identifier}")
        await player.remove_embed(track)


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
        lavalink_client.add_event_hook(track_hook)
        bot.d.lavalink = lavalink_client
    return bot.d.lavalink


async def _connect(
    ctx: lightbulb.Context, lavalink_client: lavalink.Client
) -> "AudioPlayer":
    voice_state = ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
    if not voice_state:
        await ctx.respond("Connect to a voice channel first.")
        return None

    channel_id = voice_state.channel_id

    player = lavalink_client.player_manager.create(guild_id=ctx.guild_id)
    await audio_plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)

    return player


async def _disconnect(
    guild_id: hikari.Snowflakeish, lavalink_client: lavalink.Client
) -> None:
    player: AudioPlayer = lavalink_client.player_manager.get(guild_id)

    # None means disconnect
    await audio_plugin.bot.update_voice_state(guild_id, None)
    if player:
        await player.stop()
        await player.destroy()


@audio_plugin.listener(hikari.StartedEvent)
async def start_lavalink(event: hikari.StartedEvent) -> None:
    get_lavalink_client(audio_plugin.bot)


@audio_plugin.listener(hikari.StoppingEvent)
async def stop_lavalink(event: hikari.StoppingEvent) -> None:
    lavalink_client = get_lavalink_client(audio_plugin.bot)
    for player in lavalink_client.player_manager.find_all():
        for idenifier in list(player.embed_uis.keys()):
            await player.embed_uis[idenifier].stop()
            del player.embed_uis[idenifier]


@audio_plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent):
    lavalink_client = get_lavalink_client(audio_plugin.bot)
    if event.old_state:
        channel_state = audio_plugin.bot.cache.get_voice_states_view_for_channel(
            event.guild_id, event.old_state.channel_id
        )
        if (
            len(channel_state) == 1
            and channel_state.get_item_at(0).user_id == audio_plugin.bot.get_me().id
        ):
            await _disconnect(event.guild_id, lavalink_client)


@audio_plugin.listener(hikari.VoiceServerUpdateEvent)
async def voice_server_update(event: hikari.VoiceServerUpdateEvent):
    logger.info(event)


@audio_plugin.listener(hikari.ShardPayloadEvent)
async def shard_payload_update(event: hikari.ShardPayloadEvent):
    if event.name in ["VOICE_STATE_UPDATE", "VOICE_SERVER_UPDATE"]:
        lavalink_client = get_lavalink_client(audio_plugin.bot)
        lavalink_data = {"t": event.name, "d": dict(event.payload)}
        await lavalink_client.voice_update_handler(lavalink_data)


class TrackSelect(miru.Select):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.Context) -> None:
        logger.info(f"Select selected {ctx.interaction.values[0]}")
        self.view.track = self.view.find_track_from_id(ctx.interaction.values[0])
        self.view.stop()


class TrackSelectView(miru.View):

    track = None

    def __init__(
        self, track_results: List[lavalink.AudioTrack], *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.track_results = track_results
        select_options = [
            miru.SelectOption(
                track.title,
                track.identifier,
                description=track.uri,
                is_default=(index == 0),
            )
            for index, track in enumerate(track_results)
        ]
        select_component = TrackSelect(
            options=select_options, placeholder="Pick a track to play!"
        )
        self.add_item(select_component)

    def find_track_from_id(self, track_id: str) -> lavalink.AudioTrack:
        for track in self.track_results:
            if track.identifier == track_id:
                return track
        return None

    @miru.button(label="Cancel", style=hikari.ButtonStyle.DANGER)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.stop()


async def track_select_menu(
    ctx: lightbulb.Context, result_tracks: List[lavalink.AudioTrack]
) -> Optional[lavalink.AudioTrack]:

    select_view = TrackSelectView(result_tracks)

    res = await ctx.respond(
        f"Add audio for your search!", components=select_view.build()
    )
    message = await res.message()
    select_view.start(message)  # Start listening for interactions
    await select_view.wait()

    track = select_view.track
    if not track:
        await message.edit("No response.", components=[])
        return None
    await message.delete()
    return track


async def add_tracks(
    ctx: lightbulb.Context, player: "AudioPlayer", results: lavalink.LoadResult
) -> List[Union[lavalink.AudioTrack, lavalink.DeferredAudioTrack]]:

    for track in results.tracks:
        track.extra["channel_id"] = ctx.channel_id

    if not results or results.load_type in [
        lavalink.LoadType.LOAD_FAILED,
        lavalink.LoadType.NO_MATCHES,
    ]:
        return await ctx.respond(
            f"No tracks found for `{ctx.options.query}`", reply=True
        )
    elif results.load_type in [lavalink.LoadType.PLAYLIST]:
        for track in results.tracks:
            player.add(track, requester=ctx.author.id)
        await ctx.respond(
            f"Added playlist with `{len(results.tracks)}` track(s) to the queue.",
            reply=True,
        )
    elif results.load_type in [lavalink.LoadType.TRACK]:
        track = results.tracks[0]
        player.add(track, requester=ctx.author.id)
        await ctx.respond(f"Added `{track.title}` to the queue.", reply=True)
    elif results.load_type in [lavalink.LoadType.SEARCH]:
        track = await track_select_menu(ctx, results.tracks)
        if not track:
            return None
        player.add(track, requester=ctx.author.id)
        await ctx.respond(f"Added `{track.title}` to the queue.", reply=True)
    else:
        logger.error(f"Unhandled load type {results.load_type}")
        raise FindItemExcpetion(f"Unable to handle the result {results.load_type}")


class PlayerUIView(miru.View):
    def __init__(self, player: "AudioPlayer", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.player = player

    @miru.button(label="⏯", style=hikari.ButtonStyle.PRIMARY)
    async def play_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if self.player.paused:
            await self.player.set_pause(False)
        else:
            await self.player.set_pause(True)

    @miru.button(label="⏭", style=hikari.ButtonStyle.PRIMARY)
    async def next_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await self.player.skip()

    @miru.button(label="⏹", style=hikari.ButtonStyle.PRIMARY)
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await self.player.stop()


class EmbedUI:
    def __init__(self, message, ui_view, view_task):
        self.message = message
        self.ui_view = ui_view
        self.view_task = view_task

    async def stop(self):
        self.ui_view.stop()
        await self.message.delete()
        self.view_task.cancel()


class AudioPlayer(lavalink.DefaultPlayer):

    embed_uis = {}

    async def get_embed(self, track: lavalink.AudioTrack):
        requester = await audio_plugin.bot.rest.fetch_user(track.requester)

        embed = hikari.Embed(
            title="Now Playing",
            description=track.title,
            url=track.uri,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
            color=requester.accent_color,
        )
        embed.set_thumbnail(audio_plugin.bot.get_me().avatar_url)
        logger.info(track.uri)
        if "youtube.com" in track.uri:
            embed.set_image(
                f"https://img.youtube.com/vi/{track.identifier}/maxresdefault.jpg"
            )
        else:
            embed.set_image(requester.avatar_url)
        upcoming = self.queue[0].title if len(self.queue) > 0 else "Nothing!"
        embed.add_field(
            name=(
                f"__**{'Paused' if self.paused else 'Playing'}**__  -  "
                f"**Volume**: {self.volume}%  -  **Repeat**: {self.repeat}"
            ),
            value=f"Next Up: *{upcoming}*",
            inline=True,
        )

        embed.set_footer(
            text=f"Requested by {requester.username}", icon=requester.avatar_url
        )
        return embed

    async def send_embed(self, track: lavalink.AudioTrack):
        logger.info(f"{track.extra}")
        if not track.extra.get("embed_ui"):
            logger.info(f"Start embed ui for {track.identifier}")
            channel: hikari.GuildTextChannel = (
                await audio_plugin.bot.rest.fetch_channel(track.extra.get("channel_id"))
            )
            embed = await self.get_embed(track)
            ui_view = PlayerUIView(self)
            message = await channel.send(embed=embed, components=ui_view.build())
            ui_view.start(message)
            view_task = asyncio.create_task(ui_view.wait())
            logger.info(f"{track.extra}")
            self.embed_uis[track.identifier] = EmbedUI(message, ui_view, view_task)

    async def update_embed(self, track: lavalink.AudioTrack):
        logger.info(f"{track.extra}")
        if self.embed_uis.get(track.identifier):
            logger.info(f"Update embed ui for {track.identifier}")
            embed_ui: EmbedUI = self.embed_uis.get(track.identifier)
            embed = await self.get_embed(track)
            await embed_ui.message.edit(embed=embed)

    async def remove_embed(self, track: lavalink.AudioTrack):
        logger.info(f"{track.extra}")
        if self.embed_uis.get(track.identifier):
            logger.info(f"Remove embed ui for {track.identifier}")
            embed_ui: EmbedUI = self.embed_uis.get(track.identifier)
            await embed_ui.stop()
            del self.embed_uis[track.identifier]


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
    player = await _connect(ctx, lavalink_client)

    if not player:
        return

    if ctx.options.query:
        query = ctx.options.query
        if not url_rx.match(query):
            query = f"ytsearch:{query}"

        results: lavalink.LoadResult = await player.node.get_tracks(query)
        await add_tracks(ctx, player, results)

    if not (ctx.options.query and player.paused):
        if not player.is_playing:
            await player.play()
        elif player.paused:
            await player.set_pause(False)


class YesNoView(miru.View):
    def __init__(self, default_result: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.result = default_result

    @miru.button(label="Yes", style=hikari.ButtonStyle.SUCCESS)
    async def yes_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = True
        self.stop()

    @miru.button(label="No", style=hikari.ButtonStyle.DANGER)
    async def no_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = False
        self.stop()


@audio_plugin.command
@lightbulb.option(
    "leave", "Forces leaving the voice channel.", type=bool, required=False
)
@lightbulb.command("stop", "Stops all audio tells the bot to leave the voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if player.is_playing:
        await player.set_pause(True)
        await ctx.respond("Audio stopped!", reply=True)
    else:
        await _disconnect(ctx.guild_id, lavalink_client)
        return await ctx.respond(f"Disconnected!", reply=True)

    if ctx.options.force:
        await _disconnect(ctx.guild_id, lavalink_client)
        return await ctx.respond(f"Disconnected!", reply=True)
    else:
        yes_no_view = YesNoView(default_result=True, timeout=30)
        resp = await ctx.respond(
            "Do you want me to clear the queue and leave the channel? (Default = Yes)",
            components=yes_no_view.build(),
        )
        msg = await resp.message()
        yes_no_view.start(msg)
        await yes_no_view.wait()
        await msg.delete()
        if yes_no_view.result:
            await player.stop()
            await _disconnect(ctx.guild_id, lavalink_client)
            await ctx.respond(f"Disconnected!", reply=True)


@audio_plugin.command
@lightbulb.command("pause", "Pauses the current playing track.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if player.is_playing:
        await player.set_pause(True)
        await ctx.respond("Audio paused!", reply=True)


@audio_plugin.command
@lightbulb.command("next", "Skips to the next track.", aliases=["skip"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def next(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    player: AudioPlayer = lavalink_client.player_manager.get(ctx.guild_id)

    if player.is_playing:
        await player.skip()
        await ctx.respond("Skipping track", reply=True)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(audio_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    lavalink_client = get_lavalink_client(bot)
    lavalink_client._event_hooks.clear()
    bot.remove_plugin(audio_plugin)
