import random
from random import choice

import hikari
import lightbulb

misc_plugin = lightbulb.Plugin("Text")


@misc_plugin.command
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


@misc_plugin.command
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


dice_types = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}


@misc_plugin.command
@lightbulb.option(
    "dice", "The type of dice to roll.", type=str, choices=list(dice_types.keys())
)
@lightbulb.option(
    "number",
    "The number of dice to roll.",
    type=int,
    default=1,
    min_value=1,
    max_value=100,
)
@lightbulb.option("offset", "A number to offset the roll.", type=int, default=0)
@lightbulb.command("roll", "Roll some dice.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def roll_dice(ctx: lightbulb.Context) -> None:
    number = ctx.options.number
    dice = ctx.options.dice
    sides = dice_types[dice]
    offset = ctx.options.offset

    response = [random.randint(1, sides) for _ in range(number)]
    total = sum(response) + offset

    response_str = " + ".join(str(x) for x in response)
    if offset:
        response_str += f" + ({offset})"
    response_str += f" = {total}" if len(response) > 1 else ""

    await ctx.respond(f"Rolling `{number}{dice}`: ```{response_str}```")


@misc_plugin.command
@lightbulb.command("flip", "Flips a coin.", aliases=["toss"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def toss_coin(ctx: lightbulb.Context) -> None:
    responses = ["Heads", "Tails"]
    await ctx.respond(f"Flipping Coin: ```{random.choice(responses)}```")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(misc_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(misc_plugin)
