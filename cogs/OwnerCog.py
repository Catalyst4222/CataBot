import discord
from discord.ext import commands
import io, textwrap, traceback, asyncio, inspect
from typing import Union, Optional
from contextlib import redirect_stdout
from copy import copy
from discord_slash.model import CommandObject
from discord_slash.utils.manage_commands import add_slash_command

from . import utils
from .utils.jsk_repl import codeblock_converter, AsyncCodeExecutor, AsyncSender, Scope, jsk_python_result_handling


class OwnerThings(commands.Cog, command_attrs=dict(hidden=True)):
    """Please don't mess with these, largely meant for the owner"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._last_result = None
        self.sessions = set()

        self.scope = Scope()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

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
            'utils': utils,  # I made this!
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
            'utils': utils,  # I made this!
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

    # https://github.com/Gorialis/jishaku/blob/d1d64857aef6926307cd4a883e107586419ce1e2/jishaku/features/python.py#L130
    @commands.command(aliases=['jsk_repl'])
    async def jsk_py(self, ctx: commands.Context,):
        """
        Direct evaluation of Python code.
        Adapted largely from Jishaku, with help from the other REPL function
        I AM A GENIUS
        """

        # arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict = {'ctx': ctx, 'bot': self.bot, 'message': ctx.message, 'guild': ctx.guild, 'channel': ctx.channel,
                    'author': ctx.author, 'utils': utils, 'slash': self.bot.slash, "_": self._last_result}

        scope = self.scope

        def check(m):
            return (
                    m.author.id == ctx.author.id
                    and m.channel.id == ctx.channel.id
                    and m.content.startswith('`')
            )

        self.sessions.add(ctx.channel.id)
        await ctx.send('Entering JSK REPL')

        while True:
            try:
                message = codeblock_converter(
                    (await self.bot.wait_for(
                        'message', check=check, timeout=10.0 * 60.0
                    )).content
                )
            except asyncio.TimeoutError:
                await ctx.send('Exiting REPL session.')
                self.sessions.remove(ctx.channel.id)
                break


            stdout = io.StringIO()
            # eval_ish = None
            try:
                with redirect_stdout(stdout):
                    executor = AsyncCodeExecutor(message.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):
                        # if eval_ish is None:
                        #     eval_ish = True
                        # elif eval_ish:
                        #     eval_ish = False

                        if result is None:
                            continue

                        self._last_result = result

                        # # Can't do this yet:
                        # await jsk_python_result_handling(ctx, result)
                        # send(codeblock_converter(
                        #         (await self.bot.wait_for(
                        #             'message', check=check, timeout=10.0 * 60.0
                        #         )).content
                        #     ).content)
                        # # Has to be:
                        send(None)
                        if inspect.isawaitable(result):
                            result = await result
                        await jsk_python_result_handling(ctx, result)


            except Exception as e:
                value = stdout.getvalue()
                val_fmt = f'`stdout`:\n```py\n{value}\n```'
                exc_fmt = f'Traceback:\n```py\n{traceback.format_exc()}\n```'
                try:
                    if val_fmt is not None:
                        if len(val_fmt) > 2000:
                            await ctx.send('Content too big to be printed.')
                        else:
                            await ctx.send(val_fmt)
                    if exc_fmt is not None:
                        if len(exc_fmt) > 2000:
                            await ctx.send('Content too big to be printed.')
                        else:
                            await ctx.send(exc_fmt)

                except discord.Forbidden:
                    pass
                except discord.HTTPException as e:
                    await ctx.send(f'Unexpected error: `{e}`')
            else:

                # Trying a modified jsk way
                value = stdout.getvalue().strip(' \n')
                if value:
                    await jsk_python_result_handling(ctx, value)


            #     value = stdout.getvalue()
            #     # if not eval_ish:
            #     #     result = ''
            #
            #     if result is not None:
            #         fmt = f'```py\n{value}{result}\n```'
            #         arg_dict['_'] = result
            #     elif value:
            #         fmt = f'```py\n{value}\n```'
            #     else:
            #         fmt = None
            #
            # try:
            #     if fmt is not None:
            #         if len(fmt) > 2000:
            #             await ctx.send('Content too big to be printed.')
            #         else:
            #             await ctx.send(fmt)
            # except discord.Forbidden:
            #     pass
            # except discord.HTTPException as e:
            #     await ctx.send(f'Unexpected error: `{e}`')



def setup(bot):
    bot.add_cog(OwnerThings(bot))
