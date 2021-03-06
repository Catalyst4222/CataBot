import discord
from discord.ext import commands
from discord_slash.cog_ext import cog_component, cog_subcommand
from discord_slash.utils.manage_components import (
    create_select_option,
    create_select,
    create_actionrow,
    create_button,
)
from discord_slash.context import SlashContext, ComponentContext

from . import utils


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_subcommand(
        base='role',
        subcommand_group='add',
        name='select',
        description='Make a select that gives roles',
        options=[
            {
                'name': 'roles',
                'description': 'The roles you want to give, separated by |. Can be mentions or names',
                'required': True,
                'type': 3,
            },
            {
                'name': 'create_roles',
                'description': 'Whether to create any missing roles',
                'required': False,
                'type': 5,
            },
        ],
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_select(self, ctx: SlashContext, roles: str, create_roles: bool = False):
        try:
            roles: list[discord.Role] = [
                (
                    await utils.get_or_make_role(ctx, role)
                    if create_roles
                    else await commands.RoleConverter().convert(ctx, role)
                )
                for role in roles.split('|')
            ]
            if None in roles:
                raise commands.RoleNotFound

        except commands.RoleNotFound:
            return await ctx.send('One or more roles failed to convert')

        options = [create_select_option(role.name, role.name) for role in roles]
        select = create_select(
            options=options,
            custom_id='select_roles',
            min_values=0,
            max_values=len(options),
        )

        await ctx.send('Choose your roles here:', components=[create_actionrow(select)])

    @cog_component()
    async def select_roles(self, ctx: ComponentContext):
        all_roles = {
            discord.utils.get(ctx.guild.roles, name=option['value'])
            for option in ctx.component['options']
        }
        to_add = {
            discord.utils.get(ctx.guild.roles, name=option)
            for option in ctx.selected_options
        }
        to_remove = all_roles - to_add

        await ctx.author.add_roles(*to_add)
        await ctx.author.remove_roles(*to_remove)

        await ctx.send('Roles changed!', hidden=True)

    @cog_subcommand(
        base='role',
        subcommand_group='add',
        name='button',
        description='Make a button that gives roles',
        options=[
            {
                'name': 'role',
                'description': 'The role you want to give, separated by |. Can be a mention or name',
                'required': True,
                'type': 3,
            },
            {
                'name': 'create_role',
                'description': 'Whether to create the role if not found',
                'required': False,
                'type': 5,
            },
        ],
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_button(self, ctx: SlashContext, role: str, create_role: bool = False):
        try:
            role = (
                await utils.get_or_make_role(ctx, role)
                if create_role
                else await commands.RoleConverter().convert(ctx, role)
            )
            if role is None:
                raise commands.RoleNotFound

        except commands.RoleNotFound:
            return await ctx.send('The role failed to convert')

        button = create_button(label=role.name, style=1, custom_id='button_role')

        await ctx.send(
            f'Click the button to get the {role.name} role',
            components=[create_actionrow(button)],
        )

    @cog_component()
    async def button_role(self, ctx: ComponentContext):
        role = discord.utils.get(ctx.guild.roles, name=ctx.component['label'])

        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
        else:
            await ctx.author.add_roles(role)

        await ctx.send('Roles changed!', hidden=True)

    @cog_subcommand(
        base='role',
        subcommand_group='add',
        name='user',
        description='Add a role to a user',
        options=[
            {
                'name': 'roles',
                'description': 'The roles you want to give, separated by |. Can be mentions or names',
                'required': True,
                'type': 3,
            },
            {
                'name': 'user',
                'description': 'The user you want to give the role to',
                'required': True,
                'type': 6,
            },
            {
                'name': 'create_roles',
                'description': 'Whether to create any missing roles',
                'required': False,
                'type': 5,
            },
        ],
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def user_add(
        self,
        ctx: SlashContext,
        roles: str,
        user: discord.Member,
        create_roles: bool = False,
    ):
        try:
            role_func = (
                utils.get_or_make_role
                if create_roles
                else commands.RoleConverter().convert
            )

            roles: list[discord.Role] = [
                (await role_func(ctx, role)) for role in roles.split('|')
            ]
            if None in roles:
                raise commands.RoleNotFound

        except commands.RoleNotFound:
            return await ctx.send('One or more roles failed to convert')

        await user.add_roles(*roles)
        await ctx.send('Roles added!', hidden=True)

    # @cog_subcommand(
    #     base='role',
    #     name='auto',
    #     description='Make a select that gives roles',
    #     options=[{
    #             'name': 'role',
    #             'description': 'The role you want to give new members when they join the server',
    #             'required': False,
    #             'type': 8,
    #     }])
    # @utils.all_have_permissions(manage_roles=True)
    # async def autorole(self, ctx: SlashContext, role: discord.Role = None):
    #     guild_settings = self.bot.settings.get(ctx.guild_id)
    #     if guild_settings is None:
    #         self.bot.settings[ctx.guild_id] = guild_settings
    #
    #     # if not isinstance(role, (discord.Role, type(None))):
    #     #     try:
    #     #         role = commands.RoleConverter().convert(ctx, role)
    #     #     except commands.RoleNotFound:
    #     #         return await ctx.send('Role not found')
    #
    #     guild_settings['autorole'] = role
    #     await ctx.send('Role set!')


def setup(bot):
    bot.add_cog(Roles(bot))
