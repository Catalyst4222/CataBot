import asyncio
from discord.ext import commands
from discord_slash.cog_ext import cog_slash, cog_component
from discord_slash.utils.manage_components import *
from discord_slash.context import SlashContext, ComponentContext
import datetime
import time

guild_ids = [740302616713756878, 775035228309422120, 783740572824895498, 730606260948303882]


class ButtonCog(commands.Cog):
    """Testing Cog designed for button experiments"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.running_polls = self.bot.settings.get('running_polls', {})
        if not self.running_polls:
            self.bot.settings['running_polls'] = self.running_polls

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

    @cog_slash(name='poll', description='Make a poll. Max of 25 options', options=[
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
            'type': 10,
        },
        {
            'name': 'max_choices',
            'description': 'How many choices a user can choose, default 1',
            'required': False,
            'type': 4,
        }
    ])
    async def vote(self, ctx: SlashContext, title: str = '', description: str = '',
                   options: str = '', timeout: int = 24, max_choices: int = 1):
        now = int(time.time())
        options = options.split('|')

        description += f'\n\nThis poll was made at <t:{now}>\n' + \
                       f'It will end <t:{now + (timeout * 3600)}:R> ({timeout} hours from the start)'
        embed = discord.Embed(title=title, description=description)

        select_opts = []
        for opt in options:
            select_opts.append(create_select_option(label=opt, value=opt))

        for key in options:
            embed.add_field(name=key, value='0')

        await ctx.send(embed=embed, components=[create_actionrow(create_select(
            select_opts, custom_id='pollman', max_values=max_choices
        ))])
        self.running_polls[ctx.message.id] = {
            'embed': embed,
            'options': {i: 0 for i in options},
            'voters': {}
        }

        await asyncio.sleep(timeout * 3600)

        embed = self.running_polls[ctx.message.id]['embed']
        embed.clear_fields()
        for key in (options := self.running_polls[ctx.message.id]['options']):
            embed.add_field(name=key, value=str(options[key]))
        embed.description = description + '\n\nThis poll is now closed'

        await ctx.message.edit(content='Poll closed!', embed=embed)
        del self.running_polls[ctx.message.id]

    @cog_component()
    async def pollman(self, ctx: ComponentContext):
        poll = self.running_polls.get(ctx.origin_message_id)
        if poll is None:
            print(self.running_polls)
            return await ctx.send('This poll is out of date', hidden=True)


        if ctx.author_id in poll['voters']:  # if voted, remove votes
            prev = poll["voters"][ctx.author_id]  # gives a list of previous choices
            for opt in (prev or []):
                poll['options'][opt] -= 1

        poll['voters'][ctx.author_id] = ctx.selected_options
        for opt in ctx.selected_options:
            poll['options'][opt] += 1

        embed = poll['embed']
        embed.clear_fields()
        for key in poll['options']:
            embed.add_field(name=key, value=poll['options'][key])
        await ctx.edit_origin(embed=embed)
        poll['embed'] = embed

def setup(bot):
    bot.add_cog(ButtonCog(bot))


def teardown(bot: commands.Bot):
    bot.settings['running_polls'] = bot.get_cog('ButtonCog').running_polls
