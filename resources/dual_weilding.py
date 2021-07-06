import typing
from discord.ext import commands
import functools
import discord_slash


def cmd_to_func(cmd: commands.Command):
    @functools.wraps(cmd.callback)
    def inner(*args, **kwargs):
        return cmd.callback(*args, **kwargs)

    return inner


def slash_to_func(cmd: discord_slash.model.BaseCommandObject):
    @functools.wraps(cmd.func)
    async def inner(*args, **kwargs):
        return await cmd.func(*args, **kwargs)

    return inner


def both_to_func(cmd: typing.Union[commands.Command, discord_slash.model.BaseCommandObject]):
    func = cmd.callback if type(cmd) == commands.Command else cmd.func

    @functools.wraps(func)
    async def inner(*args, **kwargs):
        return await func(*args, **kwargs)

    return inner


def dual_command(
        bot: commands.Bot, bot_kwargs: dict,
        slash: discord_slash.SlashCommand, slash_kwargs: dict
):
    def wrapper(func) -> tuple[commands.Command, discord_slash.model.BaseCommandObject]:
        cmd = bot.command(**bot_kwargs)(func)
        slash_cmd = slash.slash(**slash_kwargs)(func)
        return cmd, slash_cmd

    return wrapper


@dual_command(bot=bot, bot_kwargs={}, slash=slash, slash_kwargs=dict(guild_ids=guild_ids))
async def dual_ping(ctx):
    """Ping for both d.py and discord_slash at once!"""
    await ctx.send('Pong!')
