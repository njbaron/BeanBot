import difflib
import logging
import traceback

import lightbulb
from lightbulb import events

from beanbot import config, errors

logger = logging.getLogger(__name__)

commands_plugin = lightbulb.Plugin(
    name="Commands",
    description="A extension to log commands and handle command errors.",
)


@commands_plugin.listener(events.CommandInvocationEvent)
async def on_command_invoke(event: events.CommandInvocationEvent):
    logger.info(f"Command invoked: {event.command.name} by {event.context.author}")


@commands_plugin.listener(events.CommandCompletionEvent)
async def on_command_complete(event: events.CommandCompletionEvent):
    logger.info(f"Command completed: {event.command.name}")


@commands_plugin.listener(events.CommandErrorEvent)
async def on_command_error(event: events.CommandErrorEvent) -> None:

    # Unwrap the exception to get the original cause
    exception = event.exception.__cause__ or event.exception

    if isinstance(exception, lightbulb.CommandNotFound):
        all_commands = list(event.bot.prefix_commands.keys())
        bad_command = exception.invoked_with
        possible_command = difflib.get_close_matches(
            bad_command, all_commands, n=1, cutoff=0.1
        )[0]
        return await event.context.respond(
            f":warning: Unknown command `{bad_command}`. Did you mean `{possible_command}`?",
            delete_after=10,
            reply=True,
        )

    logger.warning(
        f"Command error: {event.context.command.name} name {type(event).__name__} -> {type(exception).__name__}"
    )

    if isinstance(exception, lightbulb.NotOwner):
        await event.context.respond(
            ":warning: This feature is restricted to the owner of this bot."
        )
    elif isinstance(exception, lightbulb.CommandIsOnCooldown):
        await event.context.respond(
            f":warning: This command is on cooldown. Retry in `{exception.retry_after:.2f}` seconds.",
            delete_after=10,
            reply=True,
        )
    elif isinstance(exception, lightbulb.NotEnoughArguments):
        missing_option_str = "\n".join(
            [
                f"{option.name}: {option.description}"
                for option in exception.missing_options
            ]
        )
        await event.context.respond(
            f":warning: Missing required argument(s): ```{missing_option_str}```",
            delete_after=10,
            reply=True,
        )
    elif isinstance(exception, lightbulb.CheckFailure):
        await event.context.respond(
            f":warning: Check failed: {exception}", delete_after=10, reply=True
        )
    if isinstance(exception, errors.InvalidArgument):
        await event.context.respond(
            f":warning: Invalid argument passed: {exception}",
            delete_after=10,
            reply=True,
        )
    else:
        owner_ids = await event.context.bot.fetch_owner_ids()
        owner = await event.context.bot.rest.fetch_user(owner_ids[0])
        backtrace = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
        await event.context.respond(
            f":exclamation: Something went wrong during invocation of command `{event.context.command.name}`. "
            f"Please try again or let `{owner}` know something happened.",
            delete_after=10,
            reply=True,
        )
        await event.context.bot.rest.create_message(
            config.LOG_CHANNEL_ID,
            f":exclamation: An error occured!\n"
            f"When calling command {event.context.command.name}\n"
            f"```{backtrace}```",
        )
        logger.error(backtrace)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(commands_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(commands_plugin)
