import asyncio
import datetime
import re
import time
import typing
import discord
from discord.ext import commands
from discord_slash.model import ContextMenuType
from discord_slash.cog_ext import cog_context_menu, cog_slash
from discord_slash.context import MenuContext, SlashContext, ComponentContext
from discord_slash.utils.manage_components import create_select_option, create_select, create_actionrow, \
    wait_for_component

from .utils import run_cmd, diff_from_unix


class Utility(commands.Cog):
    """Helpful commands for handling the bot"""

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        before = time.monotonic()
        message = await ctx.send(f"Pong! \nDiscord latency: `{int(self.bot.latency * 1000)}`")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content="Pong! \n"
                                   f"Discord latency: `{int(self.bot.latency * 1000)}ms`\n"
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

    @cog_context_menu(name='WhoIs', target=ContextMenuType.USER, )
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
            .add_field(name=f'Roles: {len(member.roles) - 1}',
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

    @commands.command()
    async def stats(self, ctx: commands.Context):
        embed = discord.Embed(color=discord.Color.orange()) \
            .set_author(name=self.bot.user.display_name,
                        icon_url=str(self.bot.user.avatar_url)) \
            .set_footer(text=datetime.datetime.now().time()) \
            .add_field(name='Latency', value=f'{self.bot.latency:.2f} seconds') \
            .add_field(name='Time since start', value=diff_from_unix(self.bot.start_time))

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
            ('Crystaline', 'Played a bad song and <something> youtube-dl, crashing the bot'),
            ("9th's family", 'Restarting the modem')
        ]

        embed = discord.Embed(title='Bad people', description="Please don't break CataBot, CataBot loves you")
        [embed.add_field(name=person, value=reason) for person, reason in people]
        await ctx.send(embed=embed)

    @cog_context_menu(name="Steal Emoji", target=ContextMenuType.MESSAGE)
    async def steal_emoji(self, ctx: MenuContext):
        pattern = re.compile(r'<(a?):(\w+):(\d+)>')

        emojis = {  # set to prevent duplicates
            match.group(0)  # group 0 is all
            for match in pattern.finditer(ctx.target_message.content)
        }


        if not emojis:
            return await ctx.send('No emojis detected', hidden=True)

        other_guilds: dict[discord.Guild, str] = {}
        for guild in ctx.author.mutual_guilds:
            # other_guilds = [guild for guild in ctx.author.mutual_guilds if guild]
            member: discord.Member = guild.get_member(ctx.author_id)
            if member.guild_permissions.manage_emojis or member.guild_permissions.administrator \
                    or ctx.author_id == guild.owner_id:
                other_guilds[guild] = guild.name

        if not other_guilds:
            return await ctx.send("You don't have the permissions to manage emojis in any mutual servers with the bot",
                                  hidden=True)

        guild_opts = []
        for guild in other_guilds:
            me: discord.Member = guild.me
            if me.guild_permissions.manage_emojis or me.guild_permissions.administrator \
                    or me.id == guild.owner_id:
                guild_opts.append(
                    create_select_option(guild.name, guild.name)
                )

        if not guild_opts:
            return await ctx.send('None of the mutual servers have Manage Emojis granted to the bot', hidden=True)

        select = create_select(guild_opts, max_values=len(guild_opts))
        await ctx.send('Choose your server:', components=[create_actionrow(select)], hidden=True)
        comp_ctx: ComponentContext = await wait_for_component(self.bot, components=select)
        await comp_ctx.defer(edit_origin=True)
        # This is a bit of a bad solution
        guilds = [k for k, v in other_guilds.items() if v in comp_ctx.selected_options]

        if len(emojis) > 1:

            # send a select to ask which ones
            opts = [create_select_option(
                label=emoji, value=emoji
            ) for emoji in set(emojis)]

            if len(opts) == 2:
                # discord be mad if less than 3 options
                opts.append(create_select_option('<:CataBot:805113887748784180>', '<:CataBot:805113887748784180>',
                                                 description='This is a buffer option, not meant to be used'))

            select = create_select(options=list(opts), min_values=1, max_values=len(emojis))

            await ctx.send('Choose your emoji:', components=[create_actionrow(select)], hidden=True)
            comp_ctx: ComponentContext = await wait_for_component(self.bot, components=select)

            await comp_ctx.defer(edit_origin=True)
            emojis = comp_ctx.selected_options

        for guild in guilds:
            for emoji in emojis:
                image = await commands.PartialEmojiConverter().convert(ctx, emoji)
                await guild.create_custom_emoji(
                    name=emoji.split(':')[1],
                    image=await image.url.read()
                )


        # This is where we are now
        await ctx.send('Finished!', hidden=True)



def setup(bot):
    bot.add_cog(Utility(bot))
