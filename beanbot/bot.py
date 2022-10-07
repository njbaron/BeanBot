import logging
import time

import aiohttp
import hikari
import lightbulb
from lightbulb import commands, context

from beanbot import __title__, __version__, config

logger = logging.getLogger(__name__)

bot = lightbulb.BotApp(
    token=config.BOT_TOKEN,
    prefix=lightbulb.when_mentioned_or(config.BOT_PREFIX),
    default_enabled_guilds=config.GUILD_IDS,
    banner=str(__title__).lower(),
)


@bot.listen(hikari.StartingEvent)
async def starting_listener(event: hikari.StartingEvent) -> None:
    bot.d.aio_session = aiohttp.ClientSession()
    bot.load_extensions_from("./beanbot/ext/", must_exist=True)


@bot.listen(hikari.StartedEvent)
async def ready_listener(event: hikari.StartedEvent) -> None:
    await bot.update_presence(
        status=hikari.Status.ONLINE,
        activity=hikari.Activity(
            name=f".help | v{__version__}", type=hikari.ActivityType.PLAYING
        ),
    )
    await bot.rest.create_message(
        config.LOG_CHANNEL_ID, f"{__title__} `STARTED` at <t:{int(time.time())}>"
    )
    logging.info(f"{__title__} is online!")


@bot.listen(hikari.StoppingEvent)
async def stopping_listener(event: hikari.StoppingEvent) -> None:
    await bot.d.aio_session.close()

    await bot.rest.create_message(
        config.LOG_CHANNEL_ID, f"{__title__} `STOPPED` at <t:{int(time.time())}>"
    )
    logging.info(f"{__title__} is offline!")


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to load", type=str, required=False)
@lightbulb.command("load", "Loads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def load_ext(ctx: context.Context) -> None:
    ext = ctx.options.ext if ctx.options.ext is not None else None
    if ext is None:
        await ctx.respond(f"No Plugin provided to load!", reply=True)
        return

    try:
        bot.load_extensions(f"beanbot.ext.{ext}")
        await ctx.respond(f"Successfully loaded Plugin {ext}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't load Plugin {ext}. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to unload", type=str, required=False)
@lightbulb.command("unload", "Unloads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def unload_ext(ctx: context.Context) -> None:
    ext = ctx.options.ext if ctx.options.ext is not None else None
    if ext is None:
        await ctx.respond(f"No Plugin provided to unload!", reply=True)
        return

    try:
        bot.unload_extensions(f"beanbot.ext.{ext}")
        await ctx.respond(f"Successfully unloaded Plugin {ext}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't unload Plugin {ext}. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to reload", type=str, required=False)
@lightbulb.command("reload", "Reloads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def reload_ext(ctx: context.Context) -> None:
    ext = ctx.options.ext if ctx.options.ext is not None else None
    if ext is None:
        await ctx.respond(f"No Plugin provided to reload!", reply=True)
        return

    try:
        bot.reload_extensions(f"beanbot.ext.{ext}")
        await ctx.respond(f"Successfully reloaded Plugin {ext}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't reload Plugin {ext}. The Plugin has been reverted back to the previous working state if already loaded. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.command("logout", "Shuts the bot down", aliases=["shutdown"], hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def logout_bot(ctx: context.Context) -> None:
    await ctx.respond(f"Shutting the bot down")
    await bot.close()
