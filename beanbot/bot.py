import logging

import aiohttp
import hikari
import lightbulb
from lightbulb import commands, context
import miru

from beanbot import __title__, __version__, config

logger = logging.getLogger(__name__)

bot = lightbulb.BotApp(
    token=config.BOT_TOKEN,
    prefix=lightbulb.when_mentioned_or(config.BOT_PREFIX),
    default_enabled_guilds=config.GUILD_IDS,
    banner=str(__title__).lower(),
)
miru.load(bot)


@bot.listen(hikari.StartingEvent)
async def starting_listener(event: hikari.StartingEvent) -> None:
    bot.d.aio_session = aiohttp.ClientSession()
    bot.load_extensions_from("./beanbot/ext/", must_exist=True)


@bot.listen(hikari.StartedEvent)
async def ready_listener(event: hikari.StartedEvent) -> None:
    await bot.update_presence(
        status=hikari.Status.ONLINE,
        activity=hikari.Activity(
            name=f"{config.BOT_PREFIX}help | v{__version__}",
            type=hikari.ActivityType.PLAYING,
        ),
    )
    # await bot.rest.create_message(
    #     config.LOG_CHANNEL_ID, f"{__title__} `STARTED` at <t:{int(time.time())}>"
    # )
    logging.info(f"{__title__} is online!")


@bot.listen(hikari.StoppingEvent)
async def stopping_listener(event: hikari.StoppingEvent) -> None:
    await bot.d.aio_session.close()

    # await bot.rest.create_message(
    #     config.LOG_CHANNEL_ID, f"{__title__} `STOPPED` at <t:{int(time.time())}>"
    # )
    logging.info(f"{__title__} is offline!")


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to load", type=str)
@lightbulb.command("load", "Loads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def load_ext(ctx: context.Context) -> None:
    extension = ctx.options.ext
    try:
        bot.load_extensions(f"beanbot.ext.{extension}")
        await ctx.respond(f"Successfully loaded Plugin {extension}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't load Plugin {extension}. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to unload", type=str)
@lightbulb.command("unload", "Unloads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def unload_ext(ctx: context.Context) -> None:
    extension = ctx.options.ext
    try:
        bot.unload_extensions(f"beanbot.ext.{extension}")
        await ctx.respond(f"Successfully unloaded Plugin {extension}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't unload Plugin {extension}. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option("ext", description="The Plugin to reload", type=str)
@lightbulb.command("reload", "Reloads an extension", hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def reload_ext(ctx: context.Context) -> None:
    extension = ctx.options.ext
    try:
        bot.reload_extensions(f"beanbot.ext.{extension}")
        await ctx.respond(f"Successfully reloaded Plugin {extension}", reply=True)
    except Exception as e:
        await ctx.respond(
            f":warning: Couldn't reload Plugin {extension}. The Plugin has been reverted back to the previous working state if already loaded. The following exception was raised: \n```{e.__cause__ or e}```"
        )


@bot.command
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.command("logout", "Shuts the bot down", aliases=["shutdown"], hidden=True)
@lightbulb.implements(commands.PrefixCommand)
async def logout_bot(ctx: context.Context) -> None:
    await ctx.respond(f"Shutting the bot down")
    await bot.close()
