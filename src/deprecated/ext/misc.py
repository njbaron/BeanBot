import logging
import random
from random import choice
import asyncio
import re

import hikari
import lightbulb

HELLO_STRINGS = [
    "hola",
    "hi",
    "hello",
    "hi-ya",
    "howdy",
    "greetings",
    "bonjour",
    "whats up",
    "wazzup",
    "yo",
    "sup",
    "morning",
]
GOODBYE_STRINGS = [
    "bye",
    "goodbye",
    "farewell",
    "peace",
    "deuces",
    "chiao",
    "adios",
    "aurevoir",
    "adieu",
    "so long",
    "hasta la vista",
    "night",
    "good night",
]


text_plugin = lightbulb.Plugin(
    name="Text",
    description="Commands the modify things that the users type to the bot.",
)

logger = logging.getLogger(__name__)


@text_plugin.command
@lightbulb.option("message", "The message to uwu.", type=str, required=True)
@lightbulb.command("uwu", "Makes a message uwu.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def uwu_message(ctx: lightbulb.Context) -> None:
    message = ctx.options.message

    greetings = [
        "*hewwo...* ",
        "*Heh-hewwo...* ",
        "*Huohhh* ",
        "*OwO* ",
        "*Haiii!!!* ",
        "*UwU* ",
    ]
    faces = ["`(ᵘʷᵘ)`", " **UWU**", "`ಇ( ꈍᴗꈍ)ಇ`", "`*˚*(ꈍ ω ꈍ).₊̣̇.`", "`★⌒ヽ(˘꒳˘ *)`"]

    message = message.replace("L", "W")
    message = message.replace("R", "W")
    message = message.replace("l", "w")
    message = message.replace("r", "w")
    message = message.replace("th", "d")
    message = message.replace("ect", "ekht")
    message = message.replace("so", "sow")
    message = message.replace("ove", "uv")
    message = message.replace("ou", "ew")
    message = message.replace("no", "nyo")
    message = message.replace("mo", "myo")
    message = message.replace("No", "Nyo")
    message = message.replace("Mo", "Myo")
    message = message.replace("na", "nya")
    message = message.replace("ni", "nyi")
    message = message.replace("nu", "nyu")
    message = message.replace("ne", "nye")
    message = message.replace("anye", "ane")
    message = message.replace("inye", "ine")
    message = message.replace("onye", "one")
    message = message.replace("unye", "une")

    resp = await ctx.respond(message, tts=True)
    await resp.edit(f"{choice(greetings)} {message} {choice(faces)}")


@text_plugin.command
@lightbulb.option("question", "The question to ask the 8ball.", type=str, required=True)
@lightbulb.command("8ball", "Ask me a question.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def magic_8ball(ctx: lightbulb.Context) -> None:
    question = ctx.options.question
    responses = [
        "It is certain",
        "Without a doubt",
        "You may rely on it",
        "Yes definitely",
        "It is decidedly so",
        "As I see it, yes",
        "Most likely",
        "Yes",
        "Outlook good",
        "Signs point to yes",
        "Reply hazy try again",
        "Better not tell you now",
        "Ask again later",
        "Cannot predict now",
        "Concentrate and ask again",
        "Don’t count on it",
        "Outlook not so good",
        "My sources say no",
        "Very doubtful",
        "My reply is no",
    ]
    await ctx.respond(f"Question: {question}\n`Answer: {choice(responses)}`")


dice_regex = r"(\d*)([dD]\d+)([+-]\d+)?"


@text_plugin.command
@lightbulb.option("dice_in", "A number to offset the roll.", type=str)
@lightbulb.option("name", "Name of the roll.", type=str, required=False)
@lightbulb.command("dice", "Roll some dice.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def roll_dice(ctx: lightbulb.Context) -> None:
    dice_in = ctx.options.dice_in
    name = ctx.options.name

    dice_match = re.findall(dice_regex, dice_in)
    if not dice_match:
        return await ctx.respond("unable to find the dice. Please use the format 5d10+4")

    number, dice, modifier = dice_match[0]
    number = int(number if number else 1)
    sides = int(dice[1:])
    modifier = int(modifier if modifier else 0)

    title = f"`{name}`" if name else f"`{dice_in}`"

    response = [random.randint(1, sides) for _ in range(number)]
    total = sum(response) + modifier

    response_str = " + ".join(str(x) for x in response)
    if modifier:
        response_str += f" + ({modifier})"
    if modifier or (len(response) > 1):
        response_str += f" = {total}"

    await ctx.respond(f"Rolling {title}: ```{response_str}```")


@text_plugin.command
@lightbulb.command("coin", "Flips a coin.", aliases=["toss"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def toss_coin(ctx: lightbulb.Context) -> None:
    responses = ["Heads", "Tails"]
    await ctx.respond(f"Flipping Coin: ```{random.choice(responses)}```")


def greeting_in_message(message: str, greeting_list: list) -> bool:
    """Determines if a greeting in the greeting list is in the message.
    Item must occur once at the beginning of the message.

    Args:
        message (str): Message being evaluated.
        greeting_list (list): Greetings list being checked for.

    Returns:
        bool: True if found. False if not.
    """
    for item in greeting_list:
        if item in message:
            message_split = [i.strip() for i in message.split(item)]
            logger.debug(message_split)
            if len(message_split) == 2 and len(message_split[0]) == 0 and len(message_split[1]) == 0:
                return True
            else:
                break
    return False


@text_plugin.listener(hikari.MessageCreateEvent)
async def on_message_invoke(event: hikari.MessageCreateEvent):
    logger.debug(f"Received message event: {event}")
    if not event.is_human:
        return

    if not event.message.content:
        return

    message_content = event.message.content.lower()

    # Check for someone saying hello or goodbye to the bot.
    if "bot" in message_content:
        message_split = message_content.split("bot")[0]
        channel_id = event.message.channel_id
        if greeting_in_message(message_split, HELLO_STRINGS):
            await asyncio.sleep(0.2)
            await text_plugin.bot.rest.create_message(channel_id, f"Hello {event.message.author.mention}!")
        elif greeting_in_message(message_split, GOODBYE_STRINGS):
            await asyncio.sleep(0.2)
            await text_plugin.bot.rest.create_message(channel_id, f"Goodbye {event.message.author.mention}!")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(text_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(text_plugin)
