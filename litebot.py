from discord.ext import commands
from os import getenv
import discord
from discord_slash import SlashCommand

bot = commands.Bot(command_prefix='#', case_insensitive=True)
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

bot.TOKEN = getenv('MAIN_TOKEN')

bot.load_extension('cogs.applications')

# @bot.command()
# async def check_perms(ctx):
#     out = ctx.channel.permissions_for(ctx.guild.get_member(
#         bot.user.id
#     ))
#     # out = discord.Permissions(permissions=out)
#     print(f'Permissions for {ctx.guild.name}')
#     for perm, value in out:
#         if value:
#             print(f'{perm}: {value}')
#     # out = bot.user.permissions_in(ctx.channel)
#     # print(out)


print('Ready!')
bot.run(bot.TOKEN)
