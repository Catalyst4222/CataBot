from discord_slash.context import *
from discord.ext import commands
from discord_slash.cog_ext import *
from discord_slash.utils.manage_components import *


class Slash(commands.Cog):
    """Cog dedicated to slash commands"""
    def __init__(self, bot):
        self.bot = bot
        # nonlocal guilds
        # guilds = bot.guilds

    # [int(guild) for guild in open('resources/slash_guilds', 'w+').read().split()]
    @cog_slash(name="ping", )  # Fur Pile
    async def ping(self, ctx: SlashContext):
        await ctx.send(content="Pong!")


    @cog_slash(description='Make a select that gives you gender roles')
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def role_select(self, ctx: SlashContext):
        options = [
            create_select_option(label='He/Him', value='he/him', description='Get the He/Him role'),
            create_select_option(label='She/Her', value='she/her', description='Get the She/Her role'),
            create_select_option(label='They/Them', value='they/them', description='Get the They/Them role'),
            create_select_option(label='None', value='None', description='Choose only this to get no roles')
        ]
        select_row = create_select(options,
                                   custom_id='roles_test', max_values=3, min_values=1,
                                   placeholder="Choose the gender roles you would like to be assigned"
                                   )
        await ctx.send('Choose your gender roles here', components=[create_actionrow(select_row)])

    @cog_component()
    async def roles_test(self, ctx: ComponentContext):
        await ctx.defer(edit_origin=True)
        select_roles = {'he/him', 'she/her', 'they/them'}

        to_remove = select_roles - set(ctx.selected_options)
        to_add = select_roles - to_remove

        to_add = [
            discord.utils.get(ctx.guild.roles, name=name)
            for name in to_add
        ]
        to_remove = [
            discord.utils.get(ctx.guild.roles, name=name)
            for name in to_remove
        ]

        if None in (to_add + to_remove):
            return await ctx.send("Could not find the needed roles")

        await ctx.author.remove_roles(*to_remove)
        await ctx.author.add_roles(*to_add)

    @role_select.error
    async def roles_error(self, ctx, err):
        if isinstance(err, commands.CheckFailure):
            return await ctx.send('This command can only run in DMs, and the bot needs the `manage_roles` permission')
        raise err


def setup(bot):
    bot.add_cog(Slash(bot))
