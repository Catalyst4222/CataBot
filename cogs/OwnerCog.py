import discord
from discord.ext import commands
import io, textwrap, traceback, asyncio, inspect
from typing import Union, Optional
from contextlib import redirect_stdout
from copy import copy
from discord_slash.model import CommandObject
from discord_slash.utils.manage_commands import add_slash_command

from . import utils


class OwnerCog(commands.Cog, command_attrs=dict(hidden=True)):
    """Please don't mess with these, largely meant for the owner"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._last_result = None
        self.sessions = set()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    class Utils:
        setup = r"""
            Common setup tools:

            import asyncio, discord, discord_slash
            from discord.ext import commands
            loop = asyncio.get_running_loop()
            """

        def __init__(self, bot: commands.Bot):
            self.bot = bot

        def now(self, *args, **kwargs):
            def inner(coro):
                asyncio.create_task(coro(*args, **kwargs))
                return self.promise(coro)

            return inner

        @staticmethod
        def promise(coro):
            def inner(*args, **kwargs):
                return asyncio.create_task(coro(*args, **kwargs))
            return inner

        async def register_slash(self, command: CommandObject):
            for guild in command.allowed_guild_ids:
                await add_slash_command(self.bot.user.id, self.bot.TOKEN, guild_id=guild, cmd_name=command.name,
                                        description=command.description, options=command.options)


    # Entering internet zone
    # Nobody knows how this works
    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @staticmethod
    def get_syntax_error(e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.command(name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code
        WTF is happening I stole this from the internet"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result,
            'utils': self.Utils(self.bot),  # I made this!
            'slash': self.bot.slash,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except discord.DiscordException:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command()
    async def repl(self, ctx):
        """Launches an interactive REPL session."""
        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author,
            '_': None,
            'utils': self.Utils(self.bot),  # I made this!
            'slash': self.bot.slash,
        }

        if ctx.channel.id in self.sessions:
            await ctx.send(
                'Already running a REPL session in this channel. Exit it with `quit`.'
            )
            return

        self.sessions.add(ctx.channel.id)
        await ctx.send('Enter code to execute or evaluate. `exit()` or `quit` to exit.')

        def check(m):
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and m.content.startswith('`')
            )

        while True:
            try:
                response = await self.bot.wait_for(
                    'message', check=check, timeout=10.0 * 60.0
                )
            except asyncio.TimeoutError:
                await ctx.send('Exiting REPL session.')
                self.sessions.remove(ctx.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await ctx.send('Exiting.')
                self.sessions.remove(ctx.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await ctx.send(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = f'```py\n{value}{traceback.format_exc()}\n```'
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = f'```py\n{value}{result}\n```'
                    variables['_'] = result
                elif value:
                    fmt = f'```py\n{value}\n```'

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await ctx.send('Content too big to be printed.')
                    else:
                        await ctx.send(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send(f'Unexpected error: `{e}`')

    @commands.command()
    @commands.is_owner()
    async def sudo(
        self,
        ctx,
        channel: Optional[utils.GlobalChannel],
        who: Union[discord.Member, discord.User],
        *, command: str,
    ):
        '''Run a command as another user optionally in another channel.'''
        msg = copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)

    @commands.command()
    @commands.is_owner()
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = ctx._db

        for i in range(times):
            await new_ctx.reinvoke()


def setup(bot):
    bot.add_cog(OwnerCog(bot))
