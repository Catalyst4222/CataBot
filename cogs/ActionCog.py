import discord
from discord.ext import commands


class MaybeUser(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        # finished = []
        # for word in argument.split():
        try:
            string = argument[:18]
            if string.isnumeric():
                res = await commands.MemberConverter().convert(ctx, string)
                res = res.mention + argument[18:]
            else:
                res = (await commands.MemberConverter().convert(ctx, argument)).mention

        except commands.MemberNotFound:
            res = argument

            # finished.append(res)
        return res


def command_maker(name: str, action: str) -> commands.Command:
    """"""
    # MultiUser = cls.MultiUser

    @commands.command(name=name, description=f'Give someone a {name}!')
    async def inner(ctx, people: commands.Greedy[MaybeUser]):
        print(people)
        await ctx.send(action.format(ctx.author.mention, ' '.join(people)),
                       allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))

    assert type(inner) == commands.Command
    return inner


class Actions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def action_maker(self, ctx, name: str, *, action: str):
        if await self.bot.is_owner(ctx.author):
            try:
                cmd = command_maker(name, action)
                self.bot.add_command(cmd)
            except commands.CommandRegistrationError:
                await ctx.send('Command was previously registered')

        raw = f"""
        @commands.command(description=f'Give someone a {name}!')
        async def {name}(self, ctx, people: commands.Greedy[MultiUser]):
            await ctx.send(f"{action.format("{ctx.author.mention}", "{' '.join(people)}")}",
                           allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))"""

        await ctx.send(f'Command made! Code:\n```py\n{raw}```')
        await ctx.send('Example:\n' +
                       action.format(ctx.author.mention, self.bot.user.mention),
                       allowed_mentions=discord.AllowedMentions.none())


    @commands.command(description=f'Give someone a hug!')
    async def hug(self, ctx, people: commands.Greedy[MaybeUser]):
        await ctx.send(f"{ctx.author.mention} has hugged {' '.join(people)}! <:hug:847969770702766110>",
                       allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))

    @commands.command(description=f'Give someone a pet!')
    async def pet(self, ctx, people: commands.Greedy[MaybeUser]):
        await ctx.send(f"{ctx.author.mention} petted {' '.join(people)}!",
                       allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))


def setup(bot):
    bot.add_cog(Actions(bot))
