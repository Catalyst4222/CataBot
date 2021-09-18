import datetime
import time
import typing
import discord
from discord.ext import commands
from discord_slash.model import ContextMenuType
from discord_slash.cog_ext import cog_context_menu, cog_slash
from discord_slash.context import MenuContext, SlashContext

from .utils import run_cmd

class Utility(commands.Cog):
    """Helpful commands for handling the bot"""

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        before = time.monotonic()
        message = await ctx.send(f"Pong! \nDiscord latency: `{int(self.bot.latency*1000)}`")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content="Pong! \n"
                                   f"Discord latency: `{int(self.bot.latency*1000)}ms`\n"
                                   f"Edit Latency `{int(ping)}ms`")
        print(f'Ping {int(ping)}ms')

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
        perms: typing.Optional[int] = 2486561857,
        slashCommands: typing.Optional[bool] = True,
    ):
        """Create an invite for the bot.
        \rUse this link to create invites:
        \rhttps://discordapi.com/permissions.html"""
        msg = f'https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions={perms}&scope=bot'
        if slashCommands:
            msg += '%20applications.commands'
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

    @cog_slash(name='timestamp', description='Get a formatted timestamp from unix time or a discord id', options=[
                   {
                        'name': 'type',
                        'description': 'The type of timestamp or id the number is',
                        'required': True,
                        'type': 3,
                        'choices': [
                            {'name': 'unix', 'value': 'unix'},
                            {'name': 'discord', 'value': 'discord'},
                        ]
                   },
                   {
                       'name': 'number',
                       'description': 'The number to get the timestamp of',
                       'required': True,
                       'type': 3,
                   }
               ], connector={'type': 'method'}
               )
    async def carbon_date(self, ctx, method, number: str):
        if not number.isnumeric():
            return await ctx.send('number must be a number!')
        number = int(number)

        if method == 'discord':
            number = int((number / 4194304 + 1420070400000) / 1000)

        await ctx.send(f'Mode: {method}\n'
                       f'Static: <t:{number}:F>\n'
                       f'Relative: <t:{number}:R>')

    @staticmethod
    def sec_to_time(then: int) -> str:
        now = time.time() - then
        minutes, seconds = divmod(int(now), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'


    @commands.command()
    async def stats(self, ctx: commands.Context):
        embed = discord.Embed(color=discord.Color.orange()) \
            .set_author(name=self.bot.user.display_name,
                        icon_url=str(self.bot.user.avatar_url)) \
            .set_footer(text=datetime.datetime.now().time()) \
            .add_field(name='Latency', value=f'{self.bot.latency:.2f} seconds') \
            .add_field(name='Time since start', value=self.sec_to_time(self.bot.start_time))

        uwu = (await run_cmd('echo "Hello World" | uwuify /dev/stdin'))[0] == b'hewwo wowwd'
        embed.add_field(name='uwuifier', value=('On' if uwu else 'Off') + 'line')

        await ctx.send(embed=embed)


    @cog_slash(name='stats')
    async def _stats(self, ctx: SlashContext):
        return await self.stats(ctx)

    # noinspection SpellCheckingInspection
    @commands.command(name='badlist')
    async def badlist(self, ctx):
        """People who broke CataBot at least once, and what they did"""
        people: list[tuple] = [
            ('Catalyst', 'General dev things and exiting from a repl'),
            ('Crystaline', 'Played a bad song and <something> youtube-dl, crashing the bot')
        ]

        embed = discord.Embed(title='Bad people', description="Please don't break CataBot, CataBot loves you")
        [embed.add_field(name=person, value=reason) for person, reason in people]
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utility(bot))
