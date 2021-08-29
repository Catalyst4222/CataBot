# from ApplicationCog import ApplicationCog
# from ButtonCog import ButtonCog
# from EventCog import EventCog
# from FunCog import FunCog
# from OwnerCog import OwnerCog
# from RoleCog import RoleCog
# from UtilsCog import UtilsCog
import traceback
from os import listdir
from discord.ext.commands import command, is_owner, CommandRegistrationError

# cogs = [
#     ApplicationCog,
#     ButtonCog,
#     EventCog,
#     FunCog,
#     OwnerCog,
#     RoleCog,
#     UtilsCog
# ]


@command(name='load', hidden=True)
@is_owner()
async def load(ctx, *, cog: str):
    """Command which Loads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    try:
        ctx.bot.load_extension(cog)
    except Exception as e:
        print(traceback.format_exc())
        await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')

    else:
        await ctx.send('**`SUCCESS`**')


@command(name='unload', hidden=True)
@is_owner()
async def unload(ctx, *, cog: str):
    """Command which Unloads a Module.
    Remember to use dot path. e.g: cogs.owner"""

    try:
        ctx.bot.unload_extension(cog)
    except Exception as e:
        await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
    else:
        await ctx.send('**`SUCCESS`**')


@command(name='reload', hidden=True)
@is_owner()
async def reload(ctx, *, cog: str):
    """Command which Reloads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    try:
        ctx.bot.unload_extension(cog)
        ctx.bot.load_extension(cog)
    except Exception as e:
        await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
    else:
        await ctx.send('**`SUCCESS`**')


def setup(bot):
    # [bot.add_cog(cog(bot)) for cog in cogs]
    for cog in listdir('./cogs'):
        if cog.endswith('Cog.py'):
            bot.load_extension('cogs.' + cog[:-3])
            print(f'{cog} loaded!')

    try:
        bot.add_command(load)
        bot.add_command(unload)
        bot.add_command(reload)
    except CommandRegistrationError:
        pass


def teardown(bot):
    [bot.remove_cog(cog) for cog in list(bot.cogs)]

    # bot.remove_command(load)
    # bot.remove_command(unload)
    # bot.remove_command(reload)
