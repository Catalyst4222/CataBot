import asyncio
import time
from functools import wraps, partial
from itertools import chain, islice

import discord
import discord_slash
from discord.ext import commands
from typing import Callable, Coroutine, Any, Union, Optional
from discord_slash.context import InteractionContext
from discord_slash.model import CommandObject
from discord_slash.utils.manage_commands import add_slash_command


async def run_cmd(cmd: str, printout: bool = False, printerr: bool = False):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if printerr or printout:
        print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout and printout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr and printerr:
        print(f'[stderr]\n{stderr.decode()}')

    return stdout, stderr


class Cache:
    def __init__(self, func: Callable):
        self.value = None
        self.func = func

    def __call__(self, *args, **kwargs) -> Any:
        if self.value is None:
            self.value = self.func()
        return self.value


# Currently unknown how to fix
# def coro_to_func(coro: Callable[[..., Any], Coroutine[Any, Any, Any]]) -> Callable:
#     @functools.wraps(coro)
#     def inner(*args, **kwargs):
#         return asyncio.get_running_loop().run_until_complete(coro(*args, **kwargs))
#     return inner


def cmd_to_func(cmd: commands.Command) -> Callable:
    @wraps(cmd.callback)
    def inner(*args, **kwargs):
        return cmd.callback(*args, **kwargs)

    return inner


def slash_to_func(cmd: discord_slash.model.BaseCommandObject) -> Callable:
    @wraps(cmd.func)
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
                raise commands.BadArgument(
                    f'Could not find a channel by ID {argument!r}.'
                )
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(
                        f'Could not find a channel by ID {argument!r}.'
                    )
                return channel


# https://stackoverflow.com/questions/34116942/how-to-cache-asyncio-coroutines modified
class AsyncCache:
    def __init__(self, coro: Callable[[...], Coroutine]):
        self.coro = coro
        self.done = False
        self.result = None
        self.lock = asyncio.Lock()

        wraps(self.coro)(self.__call__.__func__)

    async def __call__(self, *args, **kwargs):
        async with self.lock:
            if self.done:
                return self.result
            self.result = await self.coro(*args, **kwargs)
            self.done = True
            return self.result


async def get_or_make_role(
        ctx: Union[commands.Context, InteractionContext],
        role: Union[str, int]
) -> Optional[discord.Role]:
    try:
        new_role = await commands.RoleConverter().convert(ctx, role)
    except commands.RoleNotFound:
        if type(role) == str:
            new_role = await ctx.guild.create_role(name=role)
        else:
            new_role = None

    return new_role


def all_have_permissions(**perms):
    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError('Invalid permission(s): {}'.format(', '.join(invalid)))

    def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            raise commands.NoPrivateMessage

        user_permissions = ctx.author.guild_permissions
        user_missing = [
            perm for perm, value in perms.items()
            if getattr(user_permissions, perm) != value
        ]

        if user_missing:
            raise commands.MissingPermissions(user_missing)

        self_permissions = ctx.me.guild_permissions
        self_missing = [
            perm for perm, value in perms.items()
            if getattr(self_permissions, perm) != value
        ]

        if self_missing:
            raise commands.BotMissingPermissions(self_missing)

        return True

    return commands.check(predicate)


def run_now(*args, **kwargs):
    def inner(coro):
        asyncio.create_task(coro(*args, **kwargs))
        return promise(coro)

    return inner


def promise(coro):
    def inner(*args, **kwargs):
        return asyncio.create_task(coro(*args, **kwargs))

    return inner


async def register_slash(bot, command: CommandObject):
    for guild in command.allowed_guild_ids:
        await add_slash_command(bot.user.id, bot.TOKEN, guild_id=guild, cmd_name=command.name,
                                description=command.description, options=command.options)


# https://jishaku.readthedocs.io/en/latest/_modules/jishaku/functools.html#executor_function
def sync_to_thread(func: Callable):
    @wraps(func)
    async def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        internal_function = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return inner()


# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries/7205107#7205107
def merge(a, b, path=None):
    """merges b into a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


# https://stackoverflow.com/questions/24527006/split-a-generator-into-chunks-without-pre-walking-it
def chunk(iterable, size=10):
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))


def diff_from_unix(then: int) -> str:
    now = time.time() - then
    minutes, seconds = divmod(int(now), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'


def short_diff_from_unix(then: int) -> str:
    now = time.time() - then
    minutes, seconds = divmod(int(now), 60)
    hours, minutes = divmod(minutes, 60)

    return f'{hours}:{minutes}:{seconds}' if hours else (f'{minutes}:{seconds}' if minutes else seconds)


def diff_from_time(diff: int) -> str:
    minutes, seconds = divmod(int(diff), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'


def short_diff_from_time(diff: int) -> str:
    minutes, seconds = divmod(int(diff), 60)
    hours, minutes = divmod(minutes, 60)

    return f'{hours}:{minutes}:{seconds}' if hours else (f'{minutes}:{seconds}' if minutes else seconds)



def setup(*_, ): pass
