import typing

from discord.ext import commands


class UtilsCog(commands.Cog):
    """Helpful commands for handling the bot"""

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx: commands.Context, messages: int = 25):
        """Delete all messages sent by the bot in the last X messages"""
        # [await message.delete()
        #  async for message in ctx.channel.history(limit=messages+1)
        #  if message.author == self.bot.user]
        await ctx.channel.purge(limit=messages+1, check=lambda x: x.author == self.bot.user)


    @commands.command()
    async def invite(self, ctx, perms: typing.Optional[int] = 2483416129, slashCommands: typing.Optional[bool] = True):
        """Create an invite for the bot.
        \rUse this link to create invites:
        \rhttps://discordapi.com/permissions.html"""
        msg = f'https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions={perms}'
        if slashCommands:
            msg += '&scope=bot%20applications.commands'
        return await ctx.send(msg)



def setup(bot):
    bot.add_cog(UtilsCog(bot))

