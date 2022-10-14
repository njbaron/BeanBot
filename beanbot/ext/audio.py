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


def get_lavalink_client(bot: lightbulb.BotApp) -> lavalink.Client:
    if bot.d.lavalink is None:
        logger.info("Building lavalink client")
        lavalink_client = lavalink.Client(bot.get_me().id)
        lavalink_client.add_node(
            "127.0.0.1", 2333, "youshallnotpass", "us_west", "local-node"
        )
        lavalink_client.add_node(
            "lavalink-server", 2333, "youshallnotpass", "us_west", "docker-node"
        )
        bot.d.lavalink = lavalink_client
    return bot.d.lavalink


async def _connect(
    ctx: lightbulb.Context, lavalink_client: lavalink.Client
) -> lavalink.DefaultPlayer:
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
    player = lavalink_client.player_manager.get(guild_id)

    # None means disconnect
    await audio_plugin.bot.update_voice_state(guild_id, None)
    if player:
        await player.destroy()


@audio_plugin.listener(hikari.StartedEvent)
async def start_lavalink(event: hikari.StartedEvent) -> None:
    get_lavalink_client(audio_plugin.bot)


# @audio_plugin.listener(hikari.StoppingEvent)
# async def stop_lavalink(event: hikari.StoppingEvent) -> None:
#     lavalink_client = get_lavalink_client(audio_plugin.bot)
#     for player in lavalink_client.player_manager.find_all():
#         await player.destroy()

#     for node in lavalink_client.node_manager.nodes:
#         logger.info(f"destroying node {node}")
#         await node.destroy()


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
        self.view.response = ctx.interaction.values[0]
        self.view.stop()


async def track_select_menu(
    ctx: lightbulb.Context, result_tracks: List[lavalink.AudioTrack]
) -> Optional[lavalink.AudioTrack]:

    select_view = miru.View()
    select_options = [
        miru.SelectOption(track.title, track.identifier, description=track.uri)
        for track in result_tracks
    ]
    select_component = TrackSelect(
        options=select_options, placeholder="Pick a track to play!"
    )
    select_view.add_item(select_component)

    res = await ctx.respond(
        f"Add audio for your search!", components=select_view.build()
    )
    message = await res.message()
    select_view.start(message)  # Start listening for interactions
    await select_view.wait()

    if hasattr(select_view, "response"):  # Check if there is an answer
        await message.delete()
        identifier = select_view.response
        for track in result_tracks:
            if track.identifier == identifier:
                return track
        raise FindItemExcpetion(f"Unable to find the track with the id: {identifier}")
    else:
        await message.edit("No response.", components=[])
        return None


async def add_tracks(
    ctx: lightbulb.Context, player: lavalink.DefaultPlayer, results: lavalink.LoadResult
) -> List[Union[lavalink.AudioTrack, lavalink.DeferredAudioTrack]]:
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


@audio_plugin.command
@lightbulb.option(
    "query", "The search or url to play in the voice channel.", type=str, required=False
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

    if not player.is_playing:
        await player.play()


@audio_plugin.command
@lightbulb.option(
    "leave", "Forces leaving the voice channel.", type=bool, required=False
)
@lightbulb.command("stop", "Stops all audio tells the bot to leave the voice channel.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    lavalink_client = get_lavalink_client(ctx.bot)
    await _disconnect(ctx.guild_id, lavalink_client)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(audio_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(audio_plugin)
