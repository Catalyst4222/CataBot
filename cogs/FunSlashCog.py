import asyncio
from os import remove

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
from discord_slash.cog_ext import cog_slash, cog_context_menu
from discord_slash.utils.manage_components import *
from discord_slash.context import SlashContext, MenuContext, InteractionContext
from discord_slash.model import ContextMenuType

from . import utils


class FunThings(commands.Cog):
    """Commands for general fun things"""

    def __init__(self, bot):
        self.bot = bot

    @cog_slash(name='avatar', options=[{
        'name': 'member',
        'description': 'The user you want to get the avatar of',
        'required': False,
        'type': 6,
    }])
    async def avatar(self, ctx: SlashContext, member: discord.Member = None):
        """Get an avatar of a user"""
        if member is None:
            member = ctx.author
        avatar_url = member.avatar_url
        await ctx.send(str(avatar_url))


    # # Currently unfixable
    # @commands.command(help='Spoiler tag an image for those on mobile')
    # async def spoiler(self, ctx: commands.Context, *, rest=''):
    #     files = []
    #     for attachment in ctx.message.attachments:
    #         file = attachment
    #         file.filename = f'SPOILER_{file.filename}'
    #         spoiler = await file.to_file(spoiler=True)
    #         files.append(spoiler)
    #
    #     await ctx.send(
    #         '{}Sent by: {}'.format(
    #             '> ' + rest + '\r\n' if rest else '', ctx.author.name
    #         ),
    #         files=files,
    #     )
    #
    #     try:
    #         await ctx.message.delete()
    #     except discord.Forbidden:
    #         await ctx.send(
    #             "You'll need to delete your message manually\n"
    #             'Give the bot Manage Message perms to remove this step'
    #         )


    @cog_slash(name='video', description='Grab the video from a link', options=[{
        'name': 'url',
        'description': 'The url you want to grab the video from',
        'required': True,
        'type': 3,
    }])
    async def video(self, ctx, url):
        """Grab a video from a link
        \rCurrently works with Reddit and YouTube, possibly others
        \rWill fail if the video is too long
        """
        async with ctx.typing():

            def curl():
                ydl_opts = {
                    'outtmpl': 'out.%(ext)s',
                    'quiet': 'true',
                    'merge_output_format': 'mp4',
                    # 'max-filesize': '8m'
                }
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(curl)

            try:
                with open('out.mp4', 'rb') as fp:
                    await ctx.send(
                        'Here is your video:', file=discord.File(fp, 'video.mp4')
                    )
            except discord.HTTPException:
                await ctx.send('That video is too large!')

            remove('out.mp4')

    @cog_slash(name='pngify', description='Convert any emoji to a png', options=[
        {
            'name': 'emoji',
            'description': 'The emoji you want to grab',
            'required': True,
            'type': 3
        },
        {
            'name': 'animated',
            'description': 'If the emoji is animated, default False',
            'required': True,
            'type': 5
        }
    ])
    async def pngify(self, ctx, emoji, ani: typing.Optional[bool] = False):
        try:
            partial = await commands.PartialEmojiConverter().convert(ctx, emoji)
            await ctx.send(partial.url)
            return
        except (commands.PartialEmojiConversionFailure, AttributeError):
            pass

        if emoji.isdigit():
            if ani is not None:
                await ctx.send(f'https://cdn.discordapp.com/emojis/{emoji}.png')
                return
            else:
                await ctx.send(f'https://cdn.discordapp.com/emojis/{emoji}.gif')
                return
        await ctx.send(
            'Unable to get the image. Once you double-checked that everything is right, yell at Cata'
        )

    # # No need to add
    # @commands.command()
    # async def embed(self, ctx):
    #     embed = discord.Embed(title='Test', description='Failed embed', color=0xFF0000)
    #     embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    #     embed.add_field(name='Field1', value='Value of Field1', inline=False)
    #     embed.set_footer(
    #         text=f'Created at {str(ctx.message.created_at):.19} UTC?',
    #         icon_url=ctx.author.avatar_url,
    #     )
    #     await ctx.send(embed=embed)

    @cog_slash(name='link', description='just a harmless link')
    async def rickroll(self, ctx: SlashContext):
        button = create_button(
            5, label='Link?', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        )
        await ctx.send('Here you go~', components=[create_actionrow(button)])


    @cog_slash(name='say')
    async def msg_send(self, ctx, msg: str):
        await ctx.channel.send(msg)
        await ctx.send('Thing said!', hidden=True)

    @cog_slash(description='uwuify some text', options=[{
        'name': 'text',
        'description': 'text to uwuify',
        'required': True,
        'type': 3
    }])
    async def uwuify(self, ctx: InteractionContext, text):
        """
        uwuify some text
        credit: https://github.com/Daniel-Liu-c0deb0t/uwu
        """
        message = object()
        message._raw_channel_mentions = []
        message.raw_mentions = []
        message.content = text
        message.raw_role_mentions = []
        ctx.message = message

        text = (await commands.clean_content(
                    escape_markdown=True, fix_channel_mentions=True
                ).convert(ctx, text)).replace("'", "'\\''")
        stdout, stderr = await utils.run_cmd(
            f"""echo '{text}' | uwuify /dev/stdin"""
        )

        if stderr:
            raise OSError(stderr.decode())

        await ctx.send(
            '>>> '
            + (await commands.clean_content(
                escape_markdown=True, fix_channel_mentions=True
            ).convert(ctx, stdout.decode())).replace('\\\\', '\\'),
            allowed_mentions=discord.AllowedMentions.none()
        )

    @cog_context_menu(name='uwuifier', target=ContextMenuType.MESSAGE)  # Maybe target 3?
    async def menu_uwu(self, ctx: MenuContext):
        await self.uwuify.func(self, ctx, text=ctx.target_message.content)


def setup(bot):
    bot.add_cog(FunThings(bot))
