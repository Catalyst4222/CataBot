import asyncio
import os
import discord
from discord.ext import commands
import youtube_dl
import typing
from discord_slash.cog_ext import cog_slash, cog_component
from discord_slash.utils.manage_components import *
from discord_slash.context import SlashContext, ComponentContext
from pathlib import Path


class FunCog(commands.Cog):
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
            file.filename = f"SPOILER_{file.filename}"
            spoiler = await file.to_file(spoiler=True)
            files.append(spoiler)

        await ctx.send('{}Sent by: {}'.format("> " + rest + "\r\n" if rest else "", ctx.author.name)
                       , files=files)

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send('You\'ll need to delete your message manually\n'
                           'Give the bot Manage Message perms to remove this step')

    @commands.command(name='video', description='Grab the video from a link')
    async def video(self, ctx, url):
        """Grab a video from a link
        \rCurrently works with Reddit and YouTube, possibly others
        \rWill fail if the video is too long
        """
        async with ctx.typing():

            def curl():
                ydl_opts = {'outtmpl': 'out.%(ext)s',
                            'quiet': 'true',
                            "merge_output_format": "mp4",
                            # 'max-filesize': '8m'
                            }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(curl)

            if os.path.getsize('out.mp4') > 8*10**6:
                await ctx.send('That video is too large!')
            else:
                with open('out.mp4', 'rb') as fp:
                    await ctx.send('Here is your video:', file=discord.File(fp, 'video.mp4'))

            os.remove('out.mp4')

    @commands.command(name='pngify', help='Convert any emoji to a png (if animated, add "True")')
    async def pngify(self, ctx, emoji, ani: typing.Optional[str]):
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
        await ctx.send('Unable to get the image. Once you double-checked that everything is right, yell at Cata')

    @commands.command()
    async def embed(self, ctx):
        embed = discord.Embed(title="Test", description="Failed embed", color=0xff0000)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Field1", value="Value of Field1", inline=False)
        embed.set_footer(text=f"Created at {str(ctx.message.created_at):.19} UTC?", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @cog_slash(name='link', description='just a harmless link')
    async def rickroll(self, ctx: SlashContext):
        button = create_button(5, label='Link?', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        await ctx.send('Here you go~', components=[create_actionrow(button)])

    @cog_slash(name='button', description='Trying to figure out buttons')
    async def slash_button(self, ctx: SlashContext):
        button = create_button(1, label='hi', custom_id='button_hi')
        await ctx.send('Trying to figure out buttons', components=[create_actionrow(button, )])

    @cog_component()
    async def button_hi(self, ctx: ComponentContext):
        await ctx.send('Hewwo!')


def setup(bot):
    bot.add_cog(FunCog(bot))
