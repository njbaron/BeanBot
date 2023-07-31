import os

from beanbot.bot import bot


def main():
    if os.name != "nt":
        import uvloop

        uvloop.install()

    bot.run()