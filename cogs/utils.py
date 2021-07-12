import asyncio
import functools
import discord_slash
from discord.ext import commands
from typing import Callable, Coroutine, Any


async def run_cmd(cmd: str, printout: bool = True, printerr: bool = True):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout and printout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr and printerr:
        print(f'[stderr]\n{stderr.decode()}')


class cache():
    def __init__(self, func: Callable):
        self.value = None
        self.func = func

    def __call__(self, *args, **kwargs) -> Any:
        if self.value is None:
            self.value = self.func()
        return self.value


def coro_to_func(coro: Callable[[..., Any], Coroutine[Any, Any, Any]]) -> Callable:
    @functools.wraps(coro)
    def inner(*args, **kwargs):
        return asyncio.get_running_loop().run_until_complete(coro(*args, **kwargs))
    return inner


def cmd_to_func(cmd: commands.Command) -> Callable:
    @functools.wraps(cmd.callback)
    def inner(*args, **kwargs):
        return cmd.callback(*args, **kwargs)

    return inner


def slash_to_func(cmd: discord_slash.model.BaseCommandObject) -> Callable:
    @functools.wraps(cmd.func)
    async def inner(*args, **kwargs):
        return await cmd.func(*args, **kwargs)

    return inner


# Stolen from the internet
class GlobalChannel(commands.Converter):
    async def convert(self, ctx: commands.Context, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
                return channel


def setup(*_, ): pass
