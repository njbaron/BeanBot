import logging
from datetime import datetime
from random import randint
from time import time

import hikari
import lightbulb
import psutil
from hikari import __version__ as hikari_version
from lightbulb import __version__ as lightbulb_version
from lightbulb import commands, context

from beanbot.__about__ import __title__, __version__

logger = logging.getLogger(__name__)

info_plugin = lightbulb.Plugin(
    name="Info",
    description="Commands the provide info about the bot, it's users and other things.",
)


@info_plugin.command
@lightbulb.option("target", "The member to get information about.", hikari.User, required=False)
@lightbulb.command("userinfo", "Get info on a server member.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def userinfo(ctx: lightbulb.Context) -> None:
    target = ctx.get_guild().get_member(ctx.options.target or ctx.user)
    logger.info(f"{target}")

    if not target:
        await ctx.respond("That user is not in the server.")
        return

    created_at = int(target.created_at.timestamp())
    joined_at = int(target.joined_at.timestamp())
    roles = (await target.fetch_roles())[1:]  # All but @everyone

    embed = (
        hikari.Embed(
            title=f"User Info - {target.display_name}",
            description=f"ID: `{target.id}`",
            colour=0x3B9DFF,
            timestamp=datetime.now().astimezone(),
        )
        .set_footer(
            text=f"Requested by {ctx.member.display_name}",
            icon=ctx.member.avatar_url or ctx.member.default_avatar_url,
        )
        .set_thumbnail(target.avatar_url or target.default_avatar_url)
        .add_field(
            "Bot?",
            str(target.is_bot),
            inline=True,
        )
        .add_field(
            "Created account on",
            f"<t:{created_at}:d>\n(<t:{created_at}:R>)",
            inline=True,
        )
        .add_field(
            "Joined server on",
            f"<t:{joined_at}:d>\n(<t:{joined_at}:R>)",
            inline=True,
        )
        .add_field(
            "Roles",
            ", ".join(r.mention for r in roles),
            inline=False,
        )
    )
    await ctx.respond(embed)


@info_plugin.command
@lightbulb.command("ping", description="Check the bot's latency")
@lightbulb.implements(commands.PrefixCommand, commands.SlashCommand)
async def ping(ctx: context.Context) -> None:
    start = time()
    msg = await ctx.respond(
        embed=hikari.Embed(title="Ping", description="Pong!", color=randint(0, 0xFFFFFF)),
        reply=True,
    )
    end = time()

    await msg.edit(
        embed=hikari.Embed(
            title="Ping",
            description=f"**Heartbeat**: {ctx.app.heartbeat_latency * 1000:,.0f} ms "
            f"\n**Latency** : {(end - start) * 1000:,.0f} ms",
            color=randint(0, 0xFFFFFF),
            timestamp=datetime.now().astimezone(),
        )
    )


@info_plugin.command
@lightbulb.command("about", description="Tells you info about the bot.")
@lightbulb.implements(commands.PrefixCommand, commands.SlashCommand)
async def about_bot(ctx: context.Context) -> None:
    memper = format(psutil.Process().memory_percent(), ".2f")
    about_embed = (
        hikari.Embed(
            title=f"About {__title__}",
            description=f"{__title__} is a custom coded and open source bot made by me for you. "
            "It is written in Python and uses [Hikari](https://github.com/hikari-py/hikari) API wrapper "
            f"and [Lightbulb](https://github.com/tandemdude/hikari-lightbulb) Command Wrapper. {__title__} "
            "can't be invited to your server.",
            colour=randint(0, 0xFFFFFF),
            timestamp=datetime.now().astimezone(),
        )
        .add_field(
            name=f"Contribute to {__title__}!",
            value=f"{__title__} is an Open Source bot with it's source code available "
            "[here](https://gitlab.com/uploads/-/system/project/avatar/32717895/TGBot_New_Logo_v4.1.png?width=64). "
            "You are free to contribute to it!",
            inline=False,
        )
        .add_field("Ping", f"{ctx.app.heartbeat_latency * 1000:,.0f} ms", inline=True)
        .add_field("CPU Usage", f"{psutil.cpu_percent()}%", inline=True)
        .add_field("Memory Usage", f"{memper}%", inline=True)
        .set_author(name=ctx.author.username, icon=ctx.author.avatar_url)
        .set_thumbnail("https://gitlab.com/uploads/-/system/project/avatar/32717895/TGBot_New_Logo_v4.1.png")
        .set_footer(text=f"{__title__} v{__version__} | hikari v{hikari_version} | lightbulb v{lightbulb_version}")
    )
    row = ctx.app.rest.build_action_row()
    row.add_button(hikari.ButtonStyle.LINK, "https://gitlab.com/teamgreenbean/beanbot-lightbulb").set_label(
        f"{__title__} Repository"
    ).add_to_container()

    await ctx.respond(embed=about_embed, component=row, reply=True)


@info_plugin.command
@lightbulb.option("target", description="User to fetch avatar of", type=hikari.User, required=False)
@lightbulb.command(
    "avatar",
    description="Fetch Avatar of yourself or the specified user.",
    aliases=["av", "pfp"],
    auto_defer=True,
)
@lightbulb.implements(commands.PrefixCommand, commands.SlashCommand)
async def avatar_cmd(ctx: context.Context) -> None:
    target = ctx.options.target if ctx.options.target is not None else ctx.author

    embed = (
        hikari.Embed(title=f"Avatar of {target.username}", color=randint(0, 0xFFFFFF))
        .set_image(target.avatar_url)
        .set_footer(text=f"Requested by {ctx.author.username}", icon=ctx.author.avatar_url)
        .set_author(name=f"{ctx.app.get_me().username}", icon=ctx.app.get_me().avatar_url)
    )

    await ctx.respond(embed=embed, reply=True)


@info_plugin.set_error_handler()
@info_plugin.listener(lightbulb.CommandErrorEvent)
async def on_plugin_command_error(event: lightbulb.CommandErrorEvent) -> bool:
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lightbulb.NotOwner):
        await event.context.respond(
            "I am currently in testing, hence I only respond to commands triggered by my owner."
        )
        return True
    else:
        return False


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(info_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(info_plugin)
