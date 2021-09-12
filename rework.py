import logging
from os import getenv
from sys import stderr

import dis_snek.const
from dis_snek.client import Snake
from dis_snek.models.discord_objects.components import ActionRow, Button
from dis_snek.models.discord_objects.context import InteractionContext, ComponentContext
from dis_snek.models.discord_objects.interactions import SlashCommandOption, slash_command, context_menu, slash_option
from dis_snek.models.enums import Intents, CommandTypes
from dotenv import load_dotenv


def get_logger(name):
    logger = logging.getLogger(name)
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
    return logger
logger = get_logger(dis_snek.const.logger_name)


bot = Snake(intents=Intents.DEFAULT, sync_interactions=True)


@slash_command(
    "command",
    description="This is a test",
    scope=783740572824895498,
)
@slash_option("another", "str option", 3, required=True)
@slash_option("option", "int option", 4, required=True)
async def command(ctx: InteractionContext, **kwargs):

    await ctx.send(str(ctx.resolved))
    await ctx.send(f"Test: {kwargs}", components=[ActionRow(Button(1, "Test"))])


@command.error
async def command_error(e, *args, **kwargs):
    print(f"Command hit error with {args=}, {kwargs=}")


@command.pre_run
async def command_pre_run(context, *args, **kwargs):
    print("I ran before the command did!")


@command.post_run
async def command_post_run(context, *args, **kwargs):
    print("I ran after the command did!")


@slash_command(name="global_command", description="test")
async def global_cmd(ctx):
    await ctx.send("global command")


@slash_command("test_command", scope=783740572824895498, options=[SlashCommandOption("test", 3, "test option")])
async def command_two(ctx: InteractionContext, **kwargs):
    await ctx.send(f"Test: {kwargs}", components=[Button(1, "Test")])


@context_menu(name="user menu", context_type=CommandTypes.USER, scope=783740572824895498)
async def user_context(ctx):
    await ctx.send("Context menu:: user")


@bot.event
async def on_ready():
    print("Ready")


@bot.event
async def on_guild_create(guild):
    print(f"guild created : {guild.name}")


@bot.event
async def on_message_create(message):
    print(f"message received: {message.content}")


@bot.event
async def on_component(ctx: ComponentContext):
    await ctx.edit_origin("test")


load_dotenv()
bot.TOKEN = getenv('LITE_TOKEN')
bot.load_extension("cog_test")
bot.start(bot.TOKEN)
