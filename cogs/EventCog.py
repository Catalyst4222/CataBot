import sys
import traceback
from discord.ext import commands
import discord
import discord_slash
from discord_slash.context import InteractionContext
from typing import Union

listen = commands.Cog.listener


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @listen()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """
        if hasattr(ctx.command, 'on_error'):
            return

        cog = ctx.cog
        # noinspection PyProtectedMember
        if cog and cog._get_overridden_method(cog.cog_command_error) is not None:
            return

        await self.error_checker(ctx, error)

    @listen()
    async def on_slash_command_error(self, ctx, err):
        await self.interaction_checker(ctx, err)

    @listen()
    async def on_component_callback_error(self, ctx, err):
        await self.interaction_checker(ctx, err)

    async def interaction_checker(self, ctx: InteractionContext, err):
        ctx.send = ctx.channel.send
        await self.error_checker(ctx, err)

    @staticmethod
    async def error_checker(ctx: Union[InteractionContext, commands.Context], error):
        ignored = (commands.CommandNotFound,)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(
                    f'{ctx.command} can not be used in Private Messages.'
                )
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.BadArgument):
            await ctx.send('A converter failed to convert')

        elif isinstance(error, commands.NotOwner):
            await ctx.send('Only the owner can run this command')

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "The bot is missing the following permissions:\n"
                + '\n'.join(error.missing_perms)
            )

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "You're missing the following permissions:\n"
                + '\n'.join(error.missing_perms)
            )

        elif isinstance(error, commands.UserInputError) or \
                issubclass(type(error), commands.UserInputError):
            await ctx.send('Bad command options were received')

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f'That command is currently on cooldown. Try again in {error.cooldown} seconds'
            )

        elif (
                isinstance(error, discord_slash.error.CheckFailure)
                or isinstance(error, commands.CheckFailure)
                or issubclass(type(error), (discord_slash.error.CheckFailure, commands.CheckFailure))
        ):
            await ctx.send('A check failed when preparing the command')

        else:
            await ctx.send(f'An unhandled error occurred')
            if hasattr(ctx, 'command'):
                print('Ignoring exception in command {}:'.format(ctx.command),
                      file=sys.stderr, )
            elif hasattr(ctx, 'custom_id'):
                print('Ignoring exception in callback with id {}:'.format(ctx.custom_id),
                      file=sys.stderr, )
            else:
                print('Ignoring exception', file=sys.stderr)

            try:
                print(f'Channel: {ctx.channel.id}')
                print(f'Author: {ctx.author.id}')
                ctx.bot.logger.error(''.join(
                    [f'\nChannel: {ctx.channel.id}\n'
                     f'Author: {ctx.author.id}\n'] +
                    traceback.format_exception(
                        type(error), error, error.__traceback__
                    )
                ))
            except:
                pass

            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
            try:
                await ctx.send(f'`{type(error).__name__}: {error}`')
            except Exception as e:
                raise e from error


def setup(bot):
    bot.add_cog(Events(bot))
