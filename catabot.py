import contextlib
from os import getenv, listdir
from discord_slash import SlashCommand
from discord_slash.context import *
from discord_slash.utils.manage_components import *
from dotenv import load_dotenv
from pretty_help import PrettyHelp, DefaultMenu
from pprint import pprint as pp


menu = DefaultMenu(active_time=60)
bot = commands.Bot(command_prefix='#', case_insensitive=True, help_command=PrettyHelp(menu=menu))
slash = SlashCommand(bot,
                     # sync_commands=True
                     )

load_dotenv()
bot.TOKEN = getenv('MAIN_TOKEN')

for cog in listdir('./cogs'):
    if cog.endswith('.py'):
        bot.load_extension('cogs.' + cog[:-3])


@bot.command()
async def ping(ctx):
    """pong!"""
    await ctx.send('Pong!')


@bot.command(name='reload', hidden=True)
@commands.is_owner()
async def reload(ctx, *, cog: str):
    """Command which Reloads a Module.
    Remember to use dot path. e.g: cogs.owner"""
    try:
        with contextlib.suppress(commands.errors.ExtensionNotLoaded):
            bot.unload_extension(cog)
        bot.load_extension(cog)
    except Exception as e:
        await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
    else:
        await ctx.send('**`SUCCESS`**')


@bot.command(name='exit', aliases=['panic', 'shutdown'])
async def exit(ctx):
    with open('log.log', 'a+') as f:
        f.write(f'{ctx.author} has called the shutdown command from channel {ctx.channel.name} in {ctx.guild.name}\n')

    cogs = bot.cogs.copy()
    for cog in cogs:
        bot.remove_cog(cog)

    await ctx.send('This incident will be reported')

@bot.event
async def on_ready():
    print('Ready!')


guild_ids = [740302616713756878, 775035228309422120, 783740572824895498, 730606260948303882, 817958268097789972]






print('Starting bot')
bot.run(bot.TOKEN)
