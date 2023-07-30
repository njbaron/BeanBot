# BeanBot: a Discord Hikari - Lightbulb Bot

A test of the hikari - Lightbulb discord bot api in preparation for discord.py obsolescence.

## Running the bot

Create an `application.yaml` file at the project root with the following contents filled in.

```shell
token: <token>

prefix: <prefix character(s)> 
log_channel_id: <guild channel id>
guild_ids:
  - <guild id>
  - <guild id>
```

Run the bot

```shell
python -m beanbot
```