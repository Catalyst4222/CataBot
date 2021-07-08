import asyncio
import aiofiles
from discord.ext import commands
import json
from discord_slash.cog_ext import cog_subcommand
import aiohttp
import pathlib
from discord_slash.utils.manage_components import *


class cache():
    def __init__(self, func):
        self.value = None
        self.func = func

    def __call__(self):
        if self.value is None:
            self.value = self.func()
        return self.value


@cache
def activity_data():
    async def future():
        print('Future running')
        source = pathlib.Path(__file__)
        source /= '../../resources/activities.json'
        async with aiofiles.open(source.resolve()) as f:
            contents = await f.read()
            return dict(contents)

    data = asyncio.get_running_loop().run_until_complete(future())
    print(data)
    return data

class Applications(commands.Cog):
    """Commands designed to create special applications, largely beta"""
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_activity(url, api_json, headers):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=api_json, headers=headers) as response:
                data = json.loads(await response.text())
                code = data["code"]
                return code

    @cog_subcommand(name="stable", base='activities', options=[{
            "name": "activity_type",
            "description": "Type of activity.",
            "required": True,
            "type": 3,
            "choices": [
                *[{'name': key, 'value': str(activity_data()['playable'][key])} for key in activity_data()['playable']],
            ]
        }], description='Create a voice channel activity')
    async def stable_slash(self, ctx, activity_type):
        await self.request(ctx, activity_type)

    @cog_subcommand(name="beta", base='activities', options=[{
            "name": "activity_type",
            "description": "Type of activity.",
            "required": True,
            "type": 3,
            "choices": [
                *[{'name': key, 'value': str(activity_data()['testing'][key])} for key in activity_data()['testing']],
            ]
        }], description='Create a voice channel activity')
    async def beta(self, ctx, activity_type):
        await self.request(ctx, activity_type)


    async def request(self, ctx, activity_type):
        if ctx.author.voice:
            url = f"https://discord.com/api/v8/channels/{ctx.author.voice.channel.id}/invites"
            api_json = {
                "max_age": 86400,
                "max_uses": 0,
                "target_application_id": f"{activity_type}",
                "target_type": 2,
                "temporary": False,
                "validate": None
            }
            headers = {
                "Authorization": f"Bot {self.bot.TOKEN}",
                "Content-Type": "application/json"
            }

            code = await self.get_activity(url, api_json, headers)
            button = create_button(5, label='Click me!', url=f"https://discord.gg/{code}")
            await ctx.send("Here's you activity:", components=[create_actionrow(button)])
        else:
            await ctx.send("You need to be in a voice channel.")

    @commands.group(invoke_without_command=True)
    async def activities(self, ctx):
        await ctx.send(
            'Stable activities:\n' +
            '\n'.join([f'{key}: {activity_data()["playable"][key]}' for key in activity_data()['playable']]) + '\n' +
            '\nBeta activities:\n' +
            '\n'.join([f'{key}: {activity_data()["testing"][key]}' for key in activity_data()["testing"]]) + '\n' +
            '\nUse `#activities play <id>` to start one'
        )

    @activities.command()
    async def play(self, ctx, activity: int):
        """Choose an activity to play. Must be in a voice channel"""
        await self.request(ctx, activity)


def setup(bot):
    bot.add_cog(Applications(bot))
