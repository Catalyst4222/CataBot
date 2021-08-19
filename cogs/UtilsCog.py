import typing

import discord
from discord.ext import commands
from discord_slash.model import ContextMenuType
from discord_slash.cog_ext import cog_context_menu
from discord_slash.context import MenuContext


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
        await ctx.channel.purge(
            limit=messages + 1, check=lambda x: x.author == self.bot.user
        )

    @commands.command()
    async def invite(
        self,
        ctx,
        perms: typing.Optional[int] = 2483416129,
        slashCommands: typing.Optional[bool] = True,
    ):
        """Create an invite for the bot.
        \rUse this link to create invites:
        \rhttps://discordapi.com/permissions.html"""
        msg = f'https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions={perms}'
        if slashCommands:
            msg += '&scope=bot%20applications.commands'
        return await ctx.send(msg)

    # Menu, usertype
    # whois
    # stealing dyno's thing

    # user.name + user.discriminator?
    # Joined: .target_user.joined_at
    # Registered: .target_user.created_at
    # Roles: len(.target_user.roles)-1, [role.mention for role in .target_user.roles]

    # color: .target_user.color
    # image/thumbnail: .target_user.default_avatar_url
    # footer: member.id

    @cog_context_menu(name='WhoIs', target=ContextMenuType.USER,)
    async def whois(self, ctx: MenuContext):
        member: discord.Member = ctx.target_author
        form = '%B %d, %Y'
        # await ctx.send('This is currently in testing', hidden=True)

        embed = discord.Embed(color=member.color, description=member.mention) \
            .set_author(name=str(member), icon_url=member.avatar_url) \
            .set_thumbnail(url=member.avatar_url) \
            .set_footer(text=f'ID: {member.id}')

        embed.add_field(name='Joined:',
                        value=member.joined_at.__format__(form)) \
             .add_field(name='Registered:',
                        value=member.created_at.date().__format__(form)) \
             .add_field(name=f'Roles: {len(member.roles)-1}',
                        value=' '.join(
                            [role.mention for role in member.roles][1:]
                        ),
                        inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(UtilsCog(bot))
