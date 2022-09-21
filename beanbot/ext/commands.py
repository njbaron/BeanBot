import difflib
import logging

import lightbulb
from lightbulb import events

from beanbot import config

logger = logging.getLogger(__name__)

commands_plugin = lightbulb.Plugin("Commands")


@commands_plugin.listener(events.CommandInvocationEvent)
async def on_command_invoke(event: events.CommandInvocationEvent):
    logger.info(f"Command invoked: {event.command.name} by {event.context.author}")


@commands_plugin.listener(events.CommandCompletionEvent)
async def on_command_complete(event: events.CommandCompletionEvent):
    logger.info(f"Command completed: {event.command.name}")


@commands_plugin.listener(events.CommandErrorEvent)
async def on_command_error(event: events.CommandErrorEvent) -> None:
    if isinstance(event.exception, lightbulb.CommandInvocationError):
        await event.context.respond(
            f"Something went wrong during invocation of command `{event.context.command.name}`."
        )
        raise event.exception

    # Unwrap the exception to get the original cause
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lightbulb.NotOwner):
        await event.context.respond(
            "This feature is restricted to the owner of this bot."
        )
    elif isinstance(exception, lightbulb.CommandIsOnCooldown):
        await event.context.respond(
            f"This command is on cooldown. Retry in `{exception.retry_after:.2f}` seconds."
        )
    elif isinstance(exception, lightbulb.CommandNotFound):
        all_commands = list(event.bot.prefix_commands.keys())
        all_commands.extend(list(event.bot.slash_commands.keys()))
        bad_command = exception.invoked_with
        possible_command = difflib.get_close_matches(
            bad_command, all_commands, n=1, cutoff=0.1
        )[0]
        await event.context.respond(
            f"Unknown command `{bad_command}`. Did you mean `{possible_command}`?",
            delete_after=5,
        )
    else:
        logger.exception(exception)
        await event.context.bot.rest.create_message(
            config.LOG_CHANNEL_ID, f"*An error occured!* \n{exception}"
        )
        raise exception


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(commands_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(commands_plugin)
