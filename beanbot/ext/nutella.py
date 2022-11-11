import json
from pathlib import Path

import lightbulb

from beanbot.constants import MessageConsts
from beanbot.menus import QuestionSelect, QuestionView, YesNoView

nutella_plugin = lightbulb.Plugin(
    name="Nutella", description="Do you think that you need nutella?"
)

TEXTURE_FILE = Path("assets/textures.txt")
COLOR_FILE = Path("assets/colors.txt")
SHAPE_FILE = Path("assets/shapes.txt")
MEALS_FILE = Path("assets/meals.txt")
DAY_FILE = Path("assets/day.txt")


@nutella_plugin.command
@lightbulb.command("nutella", "Is it nutella time?")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def nutella_quesionaire(ctx: lightbulb.Context) -> None:
    # https://developer.yummly.com/documentation.html

    ########### Nutella ###########
    # Do you have nutella near you?
    # No: suggest cheapest bargin? Call nick to get some?
    # yes Good for you!

    have_view = YesNoView()
    await have_view.send(ctx, "Do you have nutella near you now?")
    if not have_view.result:
        return await ctx.respond(
            f"Looks like you need to get some before you can have some!"
        )

    ########### SOUL ###########
    # What is your soul texture today?
    # Take a list of different textures and try to match against it.
    # The smoother the texture the softer the food?
    # The rougher the texture the harder the food?

    soul_question_selects = []

    with TEXTURE_FILE.open("r") as reader:
        textures = [line.strip() for line in reader.readlines()]
    soul_question_selects.append(
        QuestionSelect("What is the texture of your soul?", textures)
    )

    # What is your soul color today?
    # The warmer the color the more it suggests hot nutella dishes
    # The cooler the color the colder the suggested nutella recipe

    with COLOR_FILE.open("r") as reader:
        colors = [line.strip() for line in reader.readlines()]
    soul_question_selects.append(
        QuestionSelect("What is the color of your soul?", colors)
    )

    # What shape is your soul?
    # Does something.

    with SHAPE_FILE.open("r") as reader:
        shapes = [line.strip() for line in reader.readlines()]
    soul_question_selects.append(
        QuestionSelect("What is the shape of your soul?", shapes)
    )

    soul_view = QuestionView(soul_question_selects)
    await soul_view.send(ctx, "How do you describe your soul in general terms atm?")
    if not soul_view.result:
        return

    await ctx.respond(
        f"Were these your answers? {json.dumps(soul_view.answers, indent=4)}"
    )

    ########### How has your day been? ###########

    day_selects = []

    # How many hours have you been awake so far?
    # 1:4 Hmm seems like you have not been up that long, breakfast nutella item?
    # 4:12 Taking this into consideration...
    # 12+: How are you living right now?! Get some nutella immediately and god to bed!
    hours_ranges = ["0-3", "4-7", "8-11", "12+"]
    day_selects.append(
        QuestionSelect("How many hours have you been awake so far?", hours_ranges)
    )

    # How is your day going on a scale of 1-10?
    with DAY_FILE.open("r") as reader:
        day_ajd = [line.strip() for line in reader.readlines()]
    day_selects.append(QuestionSelect("How is you day going?", day_ajd))

    # What have you eaten today?
    # Anything else: Hmm the odds are in your favor that it is nutella time. =]
    # Nutalla: Look like you have already spent your rations for today. Maybe some <Insert Katie Desert item here> peanutbutter and chololate chips would be better?
    # 1-100 chance to say, "I cannot decide. Maybe you should see if Nick will bring you some?"
    with MEALS_FILE.open("r") as reader:
        meals = [line.strip() for line in reader.readlines()]
    day_selects.append(
        QuestionSelect("What meals have you eaten today?", meals, max_values=len(meals))
    )

    day_view = QuestionView(day_selects)
    await day_view.send(ctx, "How would you descibe your day?")
    if not day_view.result:
        return

    await ctx.respond(
        f"Were these your answers? {json.dumps(day_view.answers, indent=4)}"
    )

    await ctx.respond(f"WIP", delete_after=MessageConsts.DELETE_AFTER)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(nutella_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(nutella_plugin)
