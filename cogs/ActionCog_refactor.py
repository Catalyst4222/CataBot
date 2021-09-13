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


def command_maker(name: str, action: str, author: str) -> commands.Command:
    @commands.command(name=name, description=f'Give someone a {name}!\nCreated by {author}')
    async def inner(self, ctx, people: commands.Greedy[MaybeUser]):
        await ctx.send(action.format(ctx.author.mention, ' '.join(people)),
                       allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))
    return inner


class Actions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def action_maker(self, ctx, name: str, *, action: str):
        """Make a custom action command
        The first argument is the command name, the second is the phrase to send
        The action phrase _must_ have {0} and {1}
        {0} is replaced with the message author, and {1} with the string the user uses"""
        try:
            cmd = command_maker(name, action, ctx.author.name)
            cmd.cog = self
            self.bot.add_command(cmd)
        except commands.CommandRegistrationError:
            return await ctx.send('Command was previously registered')

        await ctx.send('Command made!')
        await ctx.send('Example:\n' +
                       action.format(ctx.author.mention, self.bot.user.mention),
                       allowed_mentions=discord.AllowedMentions.none())

        if await self.bot.is_owner(ctx.author):
            raw = f"""
            @commands.command(description=f'Give someone a {name}!')
            async def {name}(self, ctx, people: commands.Greedy[MultiUser]):
                await ctx.send(f"{action.format("{ctx.author.mention}", "{' '.join(people)}")}",
                               allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))"""

            await ctx.send(f'Code:\n```py\n{raw}```')


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
