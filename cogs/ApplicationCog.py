import json
import typing
import aiohttp
from discord.ext import commands
from discord_slash.cog_ext import cog_slash, cog_component
from discord_slash.context import ComponentContext, SlashContext, InteractionContext
from discord_slash.utils.manage_components import (
    create_select,
    create_actionrow,
    create_button,
)


class Applications(commands.Cog):
    """Commands designed to create special applications, largely beta"""

    select_opts = [
        {
            'default': False,
            'description': None,
            'emoji': {'id': 864601164544081920, 'name': 'act_chess'},
            'label': 'Chess In The Park',
            'value': 'Chess In The Park',
        },
        {
            'default': False,
            'description': None,
            'emoji': {'id': 864601164422184961, 'name': 'act_fish'},
            'label': 'Fishington.io',
            'value': 'Fishington.io',
        },
        {
            'default': False,
            'description': None,
            'emoji': {'id': 864601185369587733, 'name': 'act_poker'},
            'label': 'Poker Night',
            'value': 'Poker Night',
        },
        {
            'default': False,
            'description': None,
            'emoji': {'id': 864601185598832690, 'name': 'act_yt'},
            'label': 'Youtube Together',
            'value': 'Youtube Together',
        },
        {
            'default': False,
            'description': None,
            'emoji': {'id': 864601087364825099, 'name': 'act_betray'},
            'label': 'Betrayal.io',
            'value': 'Betrayal.io',
        },
    ]

    game_ids = {
        'Betrayal.io': 773336526917861400,
        'Youtube Together': 755600276941176913,
        'Fishington.io': 814288819477020702,
        'Chess In The Park': 832012774040141894,
        'Poker Night': 755827207812677713,
    }

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_activity(url: str, api_json: dict, headers: dict) -> int:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=api_json, headers=headers) as response:
                res = json.loads(await response.text())
                return res['code']

    async def request(self, ctx: InteractionContext, activity_type: int) -> int:
        url = (
            f'https://discord.com/api/v8/channels/{ctx.author.voice.channel.id}/invites'
        )
        api_json = {
            'max_age': 86400,
            'max_uses': 0,
            'target_application_id': f'{activity_type}',
            'target_type': 2,
            'temporary': False,
            'validate': None,
        }
        headers = {
            'Authorization': f'Bot {self.bot.TOKEN}',
            'Content-Type': 'application/json',
        }
        return await self.get_activity(url, api_json, headers)

    async def send_select(
        self, ctx: typing.Union[commands.Context, InteractionContext]
    ):
        select = create_select(self.select_opts, custom_id='act_callback', min_values=0)
        await ctx.send(
            'Choose your activity here:', components=[create_actionrow(select)]
        )

    @cog_component()
    async def act_callback(self, ctx: ComponentContext):
        if len(ctx.selected_options) == 1:
            if ctx.author.voice:
                code = await self.request(
                    ctx, activity_type=self.game_ids[ctx.selected_options[0]]
                )
                button = create_button(
                    5, label='Click me!', url=f'https://discord.gg/{code}'
                )
                await ctx.send(
                    f'''Here's your activity ({ctx.selected_options[0]})''',
                    components=[create_actionrow(button)],
                    hidden=True,
                )
            else:
                await ctx.send('You need to be in a voice channel.', hidden=True)
        else:
            await ctx.defer(edit_origin=True)

    @cog_slash(name='activity', description='Create a voice channel activity')
    async def slash_activity(self, ctx: SlashContext):
        await self.send_select(ctx)

    @commands.command()
    async def activity(self, ctx: commands.Context):
        """Create a voice channel activity
        A select will be sent with the different activities available"""
        await self.send_select(ctx)


def setup(bot):
    bot.add_cog(Applications(bot))
