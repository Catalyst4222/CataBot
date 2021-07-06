import asyncio
from discord.ext import commands
from discord_slash.cog_ext import cog_slash, cog_component
from discord_slash.utils.manage_components import *
from discord_slash.context import SlashContext, ComponentContext
import datetime

guild_ids = [740302616713756878, 775035228309422120, 783740572824895498, 730606260948303882]


class Buttons(commands.Cog):
    """Testing Cog designed for button experiments"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_slash()
    async def counter(self, ctx: SlashContext):
        up_button = create_button(1, label='Count up', custom_id='counter_bump')
        down_button = create_button(2, label='Count down', custom_id='counter_debump')
        components = [create_actionrow(up_button, down_button)]
        await ctx.send('Counter: 0', components=components)

    @cog_component(use_callback_name=False, components=['counter_bump', 'counter_debump'])
    async def counter_callback(self, ctx: ComponentContext):
        await ctx.edit_origin(content='Counter: ' + str(
            int(ctx.origin_message.content[9:]) + (
                1 if ctx.component['custom_id'] == 'counter_bump' else -1
            )
        ))

    @cog_slash(description='Make a poll. Will fail when bot is being developed', options=[
        {
            'name': 'options',
            'description': 'What options you want, separated by |',
            'required': True,
            'type': 3,
        },
        {
            'name': 'title',
            'description': 'The title of your poll',
            'required': False,
            'type': 3,
        },
        {
            'name': 'description',
            'description': 'The description of your poll',
            'required': False,
            'type': 3,
        },

        {
            'name': 'timeout',
            'description': 'How long the poll should last in hours, default 24',
            'required': False,
            'type': 4,
        },
    ])
    async def vote(self, ctx: SlashContext, title: str = '', description: str = '',
                   options: str = '', timeout: int = 24):
        embed = discord.Embed(title=title, description=description)
        buttons = []

        for opt in options.split('|'):
            buttons.append(create_button(1, label=opt, custom_id=f'{opt}'))

        vote_opts = dict((opt, 0) for opt in options.split('|'))
        for key in vote_opts:
            embed.add_field(name=key, value=str(vote_opts[key]))
        await ctx.send(embed=embed, components=[create_actionrow(*buttons)])


        future = datetime.datetime.now() + datetime.timedelta(hours=timeout)
        voted = []

        while datetime.datetime.now() < future:
            try:
                btn_ctx = await wait_for_component(self.bot, messages=ctx.message,
                                                   check=lambda x: datetime.datetime.now() < future, timeout=300)
            except asyncio.TimeoutError:
                continue

            if btn_ctx.author_id in voted:
                await btn_ctx.send('You already voted!', hidden=True)
                continue
            else:
                voted.append(btn_ctx.author_id)

            vote_opts[btn_ctx.custom_id] += 1

            embed.clear_fields()
            for key in vote_opts:
                embed.add_field(name=key, value=str(vote_opts[key]))
            await btn_ctx.edit_origin(embed=embed,)
            await btn_ctx.send(f'Voted for {btn_ctx.custom_id}!', hidden=True)

        await ctx.send('Poll closed!')


    @cog_slash(name='button', description='Trying to figure out buttons')
    async def slash_button(self, ctx: SlashContext):
        button = create_button(1, label='hi', custom_id='button_hi')
        await ctx.send('Trying to figure out buttons', components=[create_actionrow(button, )])

    @cog_component()
    async def button_hi(self, ctx: ComponentContext):
        await ctx.send('Hewwo!')

    @cog_slash(name='link', description='just a harmless link')
    async def rickroll(self, ctx: SlashContext):
        button = create_button(5, label='Link?', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        await ctx.send('Here you go~', components=[create_actionrow(button)])


def setup(bot):
    bot.add_cog(Buttons(bot))
