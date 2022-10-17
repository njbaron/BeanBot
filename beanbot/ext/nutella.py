import hikari
import lightbulb

nutella_plugin = lightbulb.Plugin(
    name="Nutella", description="Do you think that you need nutella?"
)


@nutella_plugin.command
# Only Katie command?
@lightbulb.command("nutella", "Is it nutella time?")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def nutella_quesionaire(ctx: lightbulb.Context) -> None:
    # https://developer.yummly.com/documentation.html

    # What is your soul texture today?
    # Take a list of diffent textures and try to match against it.
    # The smoother the texture the softer the food?
    # The rougher the texture the harder the food?
    # What is your soul color today?
    # The warmer the color the more it suggests hot nutella dishes
    # The cooler the color the colder the suggested nutella recepie

    # How long have you been awake today?
    # 1:4 Hmm seems like you have not been up that long, maybe some <Breakfast item> instead?
    # 4:12 Taking this into consideration...
    # 24+: How are you living right now?! Get some nutella immediatly and god to bed!
    # What have you eaten today?
    # Anything else: Hmm the odds are in your favor that it is nutella time. =]
    # Nutalla: Look like you have already spent your rations for today. Maybe some <Insert Katie Desert item here> peanutbutter and chololate chips would be better?
    # 1-100 chance to say, "I cannot decide. Maybe you should see if Nick will bring you some?"
    await ctx.respond(f"WIP", delete_after=5)
    raise KeyError


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(nutella_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(nutella_plugin)
