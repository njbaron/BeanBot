import hikari
import lightbulb

from beanbot.constants import MessageConsts

nutella_plugin = lightbulb.Plugin(
    name="Nutella", description="Do you think that you need nutella?"
)


@nutella_plugin.command
# Only Katie command?
@lightbulb.command("nutella", "Is it nutella time?")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def nutella_quesionaire(ctx: lightbulb.Context) -> None:
    # https://developer.yummly.com/documentation.html

    ########### SOUL ###########
    # What is your soul texture today?
    # Take a list of different textures and try to match against it.
    # The smoother the texture the softer the food?
    # The rougher the texture the harder the food?

    # What is your soul color today?
    # The warmer the color the more it suggests hot nutella dishes
    # The cooler the color the colder the suggested nutella recipe
    
    # What shape is your soul?
    # Does something.
    
    ########### Nutella ###########
    # Do you have nutella near you?
    # No: suggest cheapest bargin? Call nick to get some?
    # yes Good for you!

    ########### How has your dey been? ###########
    # How long have you been awake today?
    # 1:4 Hmm seems like you have not been up that long, breakfast nutella item?
    # 4:12 Taking this into consideration...
    # 24+: How are you living right now?! Get some nutella immediately and god to bed!

    # What have you eaten today?
    # Anything else: Hmm the odds are in your favor that it is nutella time. =]
    # Nutalla: Look like you have already spent your rations for today. Maybe some <Insert Katie Desert item here> peanutbutter and chololate chips would be better?
    # 1-100 chance to say, "I cannot decide. Maybe you should see if Nick will bring you some?"
    await ctx.respond(f"WIP", delete_after=MessageConsts.DELETE_AFTER)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(nutella_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(nutella_plugin)
