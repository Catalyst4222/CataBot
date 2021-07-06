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
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def create_roles(self, ctx: commands.Context, *, roles: typing.Optional[str] = None):
        """Show/Generate different roles used by the bot"""
        if roles is None:
            return await ctx.send("""Roles and keywords:
            \rGender roles: genders
            \rMute role: mute     
            """)

        if roles == 'muted':
            muted = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted, speak=False, send_messages=False)

        elif roles == 'genders':
            [
                await ctx.guild.create_role(name=name)
                for name in ['he/him', 'she/her', 'they/them']
            ]






def setup(bot):
    bot.add_cog(UtilsCog(bot))

