import asyncio
import random
from os import remove
from discord.ext import commands
from youtube_dl import YoutubeDL
from discord_slash.cog_ext import cog_slash, cog_component, cog_context_menu
from discord_slash.utils.manage_components import *
from discord_slash.context import SlashContext, MenuContext
from contextlib import suppress
from typing import Optional
from discord_slash.model import ContextMenuType
import aiofiles

from . import utils


class FunThings(commands.Cog):
    """Commands for general fun things"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='avatar')
    async def avatar(self, ctx, avamember: discord.Member = None):
        """Get an avatar of a user"""
        if avamember is None:
            avamember = ctx.author
        avatar_url = avamember.avatar_url
        await ctx.send(avatar_url)

    @commands.command(help='Spoiler tag an image for those on mobile')
    async def spoiler(self, ctx: commands.Context, *, rest=''):
        files = []
        for attachment in ctx.message.attachments:
            file = attachment
            file.filename = f'SPOILER_{file.filename}'
            spoiler = await file.to_file(spoiler=True)
            files.append(spoiler)

        await ctx.send(
            '{}Sent by: {}'.format(
                '> ' + rest + '\r\n' if rest else '', ctx.author.name
            ),
            files=files,
        )

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send(
                "You'll need to delete your message manually\n"
                'Give the bot Manage Message perms to remove this step'
            )

    @commands.command(name='video', description='Grab the video from a link')
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

    @commands.command(
        name='emoji', help='Convert any emoji to a png (if animated, add "True")'
    )
    async def emoji(self, ctx, emoji, ani: typing.Optional[str]):
        try:
            partial = await commands.PartialEmojiConverter().convert(ctx, emoji)
            await ctx.send(partial.url)
            return
        except (commands.PartialEmojiConversionFailure, AttributeError):
            pass

        if emoji.isdigit():
            if ani is not None:
                await ctx.send(f'https://cdn.discordapp.com/emojis/{emoji}.png')
            else:
                await ctx.send(f'https://cdn.discordapp.com/emojis/{emoji}.gif')
            return
        await ctx.send(
            'Unable to get the image. Once you double-checked that everything is right, yell at Cata'
        )

    @commands.command()
    async def embed(self, ctx):
        embed = discord.Embed(title='Test', description='Failed embed', color=0xFF0000)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name='Field1', value='Value of Field1', inline=False)
        embed.set_footer(
            text=f'Created at {str(ctx.message.created_at):.19} UTC?',
            icon_url=ctx.author.avatar_url,
        )
        await ctx.send(embed=embed)

    @commands.command(name='say', hidden=True)
    async def msg_send(self, ctx, channel: Optional[utils.GlobalChannel], *, msg: str):
        await (
            channel
            if await self.bot.is_owner(ctx.author) and channel is not None
            else ctx
        ).send(msg)
        with suppress(discord.Forbidden):
            await ctx.message.delete()

    # noinspection SpellCheckingInspection
    @commands.command(rest_is_raw=True)
    async def uwuify(self, ctx, *, uwu='uwu'):
        """
        uwuify some text
        credit: https://github.com/Daniel-Liu-c0deb0t/uwu
        """
        uwu = (await commands.clean_content(
            escape_markdown=True, fix_channel_mentions=True
        ).convert(ctx, uwu)).replace("'", "'\\''")

        stdout, stderr = await utils.run_cmd(
            f"""echo '{uwu}' | uwuify /dev/stdin"""
        )

        if stderr:
            raise OSError(stderr.decode())

        postuwu = stdout.decode()
        postuwu = await commands.clean_content(escape_markdown=True).convert(ctx, postuwu)
        postuwu = postuwu.replace('\\\\\\', '').replace('\\\\', '\\')
        await ctx.send('>>> ' + postuwu)

    @commands.command(name='image')
    async def image(self, ctx):
        return await ctx.send(random.choice([
            'https://cdn.discordapp.com/attachments/777076253790306324/889287385395888138/uei41m0xoho71.webp',
            'https://cdn.discordapp.com/attachments/772935200706789376/889152267117281310/image0.png',
            'https://cdn.discordapp.com/attachments/777076253790306324/889290523997765642/image0.jpg',
        ]))




def setup(bot):
    bot.add_cog(FunThings(bot))
