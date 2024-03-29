import hikari
import lightbulb

mod_plugin = lightbulb.Plugin(name="Mod", description="Moderator tools")


@mod_plugin.command
@lightbulb.add_checks(
    lightbulb.has_guild_permissions(hikari.Permissions.MANAGE_MESSAGES),
    lightbulb.bot_has_guild_permissions(hikari.Permissions.MANAGE_MESSAGES),
)
@lightbulb.option("messages", "The number of messages to purge.", type=int, required=True)
@lightbulb.command("purge", "Purge messages.", aliases=["clear"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def purge_messages(ctx: lightbulb.Context) -> None:
    num_msgs = ctx.options.messages
    channel = ctx.channel_id

    # If the command was invoked using the PrefixCommand, it will create a message
    # before we purge the messages, so you want to delete this message first
    if isinstance(ctx, lightbulb.PrefixContext):
        await ctx.event.message.delete()
    msgs = await ctx.bot.rest.fetch_messages(channel).limit(num_msgs)
    await ctx.bot.rest.delete_messages(channel, msgs)

    await ctx.respond(f"{len(msgs)} messages deleted", delete_after=5)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(mod_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(mod_plugin)
