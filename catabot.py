import asyncio
import logging
import pickle
import time
from sys import stderr
from contextlib import suppress
from os import getenv, name
import discord
from discord.ext import commands
from discord_slash import SlashCommand
from dotenv import load_dotenv
from pretty_help import PrettyHelp, DefaultMenu

from cogs import utils

if name == 'posix':  # Make laptop speeeed!
    import uvloop
    uvloop.install()

# from cogs import utils

# TODO
# remove bad commands
# Better subcommands
# Guild autorole
# prevent fail in youtubedl
# docstring action commands
# special thing for rps
# MIT licence
# thing with replies and say
# rename pngify to emoji
# --rm-cache-dir


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] [%(name)s]: %(message)s', '%H:%M:%S')

file_handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w+')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(stderr)
stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


menu = DefaultMenu(active_time=60)
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("#"),
    case_insensitive=True,
    help_command=PrettyHelp(menu=menu, show_index=False),
    intents=discord.Intents.all()
)
bot.logger = logger
slash = SlashCommand(
    bot,
    sync_commands=True,
    # delete_from_unused_guilds=True,
)

load_dotenv()
bot.TOKEN = getenv('MAIN_TOKEN')

pkl = {}
with suppress(FileNotFoundError), open('settings.pickle', 'rb') as f:
    pkl.update(pickle.load(f))
bot.settings = pkl

print('Loading Cogs!')
bot.load_extension('cogs')


@bot.command(name='restart', hidden=True)
@commands.is_owner()
async def restart(ctx):
    logger.warning(f'{ctx.author.name} has rebooted!')

    try:
        bot.unload_extension('cogs')
    except commands.ExtensionNotLoaded:
        pass
    bot.load_extension('cogs')

    with suppress(FileNotFoundError), open('settings.pickle', 'rb') as f:
        pkl: dict = pickle.load(f)
    bot.settings.update(utils.merge(pkl, bot.settings))

    await ctx.send("You better know what you're doing")


@bot.event
async def on_ready():
    bot.ready_time = time.time()
    print('Ready!')


guild_ids = [
    740302616713756878,
    775035228309422120,
    783740572824895498,
    730606260948303882,
    817958268097789972,
]


print('Starting bot')
bot.start_time = time.time()
try:
    bot.run(bot.TOKEN)
finally:
    pickle.dump(bot.settings, open('settings.pickle', 'wb+'))

    for cog in list(bot.cogs):
        bot.remove_cog(cog.qualified_name)

    print('Finishing loop')
    tasks = asyncio.all_tasks(bot.loop)
    print(f'Remaining tasks: {tasks}')
    bot.loop.run_until_complete(asyncio.gather(*tasks))
    print('Exited')
