import random
from discord.ext import commands
from discord_slash.cog_ext import cog_subcommand
from discord_slash import SlashContext, ComponentContext
from discord_slash.utils.manage_components import (
    create_select, create_select_option, create_actionrow, wait_for_component
)
# from asyncio import Future, wait, TimeoutError
from typing import Union


# class MiniBus:  # Version of EventBus that only <something>
#     def __init__(self):
#         self.futures: dict[int, tuple[Future, Any]] = {}
#
#     def get_future(self, channel_id: int, value: Any) -> Future:
#         if self.futures.get(channel_id):
#             future: Future = self.futures[channel_id][0]
#             future.set_result([self.futures[channel_id][1], value])
#             return future
#         else:
#             self.futures[channel_id] = (Future(), value)
#             return self.futures[channel_id][0]
#
#     async def wait_for_two(self, channel_id: int, value: str, timeout: float) -> Union[list[Any, Any]]:
#         future = self.get_future(channel_id, value)
#
#         done, pending = await wait([future], timeout=timeout)
#
#         if not len(done):
#             raise TimeoutError
#
#         return future.result()  # Returns the value the first call made


class RpsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # self.bus = MiniBus()

    # @cog_subcommand(base='rock', subcommand_group='paper', name='scissors',
    #                 options=[{
    #                     'name': 'move',
    #                     'description': 'What move you want to do',
    #                     'type': 3,
    #                     'required': True,
    #                     'choices': [
    #                         {'name': 'rock', 'value': 'rock'},
    #                         {'name': 'paper', 'value': 'paper'},
    #                         {'name': 'scissors', 'value': 'scissors'},
    #                     ]
    #                 }]
    #                 )
    # async def rpc(self, ctx: SlashContext, move: str):
    #     ...

    @commands.command(aliases=['rps'])
    async def rock_paper_scissors(self, ctx: Union[commands.Context, SlashContext]):

        select = create_select(
            options=[
                create_select_option('rock', '1', '🪨', 'rock'),
                create_select_option('paper', '2', '📝', 'paper'),
                create_select_option('scissors', '3', '✂', 'scissors')
            ]
        )
        msg = await ctx.send('Who wants to play rock paper scissors?', components=[create_actionrow(select)])

        cmp1: ComponentContext = await wait_for_component(self.bot, messages=msg)
        await cmp1.edit_origin(content=cmp1.origin_message.content + f'\n{cmp1.author.name} has chosen their option!')

        cmp2: ComponentContext = await wait_for_component(self.bot, messages=msg)
        select['disabled'] = True
        await cmp2.edit_origin(content=cmp2.origin_message.content + f'\n{cmp2.author.name} has chosen their option!',
                               components=[create_actionrow(select)])

        choice1 = int(cmp1.selected_options[0])
        choice2 = int(cmp2.selected_options[0])

        choice_convert = {
            1: 'rock',
            2: 'paper',
            3: 'scissors',
        }

        if choice1 == choice2:
            await cmp2.send(f"It's a tie! Both players chose {choice1}!")
        elif (choice1 - choice2) % 3 == 1:
            await cmp2.send(f'{choice_convert[choice1].title()} beats {choice_convert[choice2]}!\n'
                            f'{cmp1.author.mention} wins!')
        elif (choice1 - choice2) % 3 == 2:
            await cmp2.send(f'{choice_convert[choice2].title()} beats {choice_convert[choice1]}!\n'
                            f'{cmp2.author.mention} wins!')
        else:
            await cmp2.send('A logic issue occurred')

    @cog_subcommand(base='rock', subcommand_group='paper', name='scissors', options=[])
    async def slash_rps(self, ctx: SlashContext):
        await self.rock_paper_scissors(ctx)

    # @commands.command(aliases=['rps'])
    # async def rock_paper_scissors(self, ctx: commands.context, move):
    #     if move not in ['rock', 'paper', 'scissors']:
    #         return await ctx.send('Your move has to be either rock, paper, or scissors')
    #     await ctx.send(f'{ctx.author.name} is ready to play rock paper scissors!')
    #
    #     id = move + random.randrange(1000, 9999).__str__()
    #
    #     res = (await self.bus.wait_for_two(ctx.channel.id, id, 60))[:]
    #
    #     print(res)
    #
    #     # # split paths
    #     # res.remove(id)
    #     # other_id = res[0]
    #     #
    #
    #     if res[0][:-4] == res[1][:-4]:  # Tie
    #         if res[0] == id:  # easy way to split paths
    #             await ctx.send("It's a tie!")
    #         return
    #
    #     print('removing...')
    #     res.remove(id)
    #     other_move = res[0][:-4]
    #
    #     # if move == other_move:
    #     #     return await ctx.send("It's a tie!")


def setup(bot):
    bot.add_cog(RpsCog(bot))
