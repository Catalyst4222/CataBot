import contextlib
import sys
from os import getenv, listdir
from discord_slash import SlashCommand
from discord_slash.context import *
from discord_slash.utils.manage_components import *
from dotenv import load_dotenv
from pretty_help import PrettyHelp, DefaultMenu
from pprint import pprint as pp
from discord.ext import commands
import json
import logging


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] [%(name)s]: %(message)s', '%H:%M:%S')

file_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w+')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


menu = DefaultMenu(active_time=60)
bot = commands.Bot(command_prefix=commands.when_mentioned_or('#'), case_insensitive=True,
                   help_command=PrettyHelp(menu=menu, show_index=False))
slash = SlashCommand(bot,
                     sync_commands=True
                     )

load_dotenv()
bot.TOKEN = getenv('MAIN_TOKEN')

with open('settings.json') as f:
    try:
        bot.settings = json.load(f)
    except json.JSONDecodeError:
        bot.settings = {}

for cog in listdir('./cogs'):
    if cog.endswith('Cog.py'):
        bot.load_extension('cogs.' + cog[:-3])




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
    logger.warning(f'{ctx.author.name + ctx.author.discriminator} has used exit!')

    cogs = bot.cogs.copy()
    for cog in cogs:
        bot.remove_cog(cog)

    await ctx.send('This incident will be reported')


@bot.event
async def on_ready():
    print('Ready!')


guild_ids = [740302616713756878, 775035228309422120, 783740572824895498, 730606260948303882, 817958268097789972]


print('Starting bot')
try:
    bot.run(bot.TOKEN)
finally:
    json.dump(bot.settings, open('settings.json', 'w+'))
    print('Exited')
