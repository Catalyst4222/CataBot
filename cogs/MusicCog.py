from discord.ext import commands
import typing
import discord
import youtube_dl
import discord.opus
import discord.voice_client
from discord.ext import commands


BASIC_OPTS = {
    'format': 'webm[abr>0]/bestaudio/best',
    'prefer_ffmpeg': True,
    'quiet': True
}


class BasicYouTubeDLSource(discord.FFmpegPCMAudio):
    """
    Basic audio source for youtube_dl-compatible URLs.
    """

    def __init__(self, url, download: bool = False):
        ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
        info = ytdl.extract_info(url, download=download)
        super().__init__(info['url'])


class VoiceFeature(commands.Cog):
    """
    Feature containing the core voice-related commands
    """

    @staticmethod
    async def voice_check(ctx: commands.Context):
        """
        Check for whether VC is available in this bot.
        """

        if not discord.voice_client.has_nacl:
            return await ctx.send("Voice cannot be used because PyNaCl is not loaded.")

        if not discord.opus.is_loaded():
            if not hasattr(discord.opus, '_load_default'):
                return await ctx.send("Voice cannot be used because libopus is not loaded.")
            # noinspection PyProtectedMember
            if not discord.opus._load_default():
                return await ctx.send(
                    "Voice cannot be used because libopus is not loaded and attempting to load the default failed."
                )

    @staticmethod
    def connected_check(ctx: commands.Context) -> bool:
        """
        Check whether we are connected to VC in this guild.
        """

        voice = ctx.guild.voice_client
        return voice and voice.is_connected()

        # if not voice or not voice.is_connected():
        #     return await ctx.send("Not connected to a voice channel in this guild.")

    @staticmethod
    def playing_check(ctx: commands.Context) -> bool:
        """
        Checks whether we are playing audio in VC in this guild.
        This doubles up as a connection check.
        """

        check = VoiceFeature.connected_check(ctx)
        if not check:
            return check

        return ctx.guild.voice_client.is_playing()


    @commands.command(name="voice", aliases=["vc"],
                      invoke_without_command=True, ignore_extra=False)
    async def jsk_voice(self, ctx: commands.Context):
        """
        Voice-related commands.
        If invoked without subcommand, relays current voice state.
        """

        if await self.voice_check(ctx):
            return

        # give info about the current voice client if there is one
        voice = ctx.guild.voice_client

        if not voice or not voice.is_connected():
            return await ctx.send("Not connected.")

        await ctx.send(f"Connected to {voice.channel.mention}, "
                       f"{'paused' if voice.is_paused() else 'playing' if voice.is_playing() else 'idle'}.")

    @commands.command(name="join", aliases=["connect"])
    async def jsk_vc_join(self, ctx: commands.Context, *,
                          destination: typing.Union[discord.VoiceChannel, discord.Member] = None):
        """
        Joins a voice channel, or moves to it if already connected.
        Passing a voice channel uses that voice channel.
        Passing a member will use that member's current voice channel.
        Passing nothing will use the author's voice channel.
        """

        if await self.voice_check(ctx):
            return

        destination = destination or ctx.author

        if isinstance(destination, discord.Member):
            if destination.voice and destination.voice.channel:
                destination = destination.voice.channel
            else:
                return await ctx.send("Member has no voice channel.")

        voice = ctx.guild.voice_client

        if voice:
            await voice.move_to(destination)
        else:
            await destination.connect(reconnect=True)

        await ctx.send(f"Connected to {destination.mention}.")

    @commands.command(name="disconnect", aliases=["dc", "fuckoff"])
    async def jsk_vc_disconnect(self, ctx: commands.Context):
        """
        Disconnects from the voice channel in this guild, if there is one.
        """

        if not self.connected_check(ctx):
            return await ctx.send("Not connected to a voice channel in this guild.")

        voice = ctx.guild.voice_client

        await voice.disconnect()
        await ctx.send(f"Disconnected from {voice.channel.mention}.")

    @commands.command(name="stop")
    async def jsk_vc_stop(self, ctx: commands.Context):
        """
        Stops running an audio source, if there is one.
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        voice = ctx.guild.voice_client

        voice.stop()
        await ctx.send(f"Stopped playing audio in {voice.channel.mention}.")

    @commands.command(name="pause")
    async def jsk_vc_pause(self, ctx: commands.Context):
        """
        Pauses a running audio source, if there is one.
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        voice = ctx.guild.voice_client

        if voice.is_paused():
            return await ctx.send("Audio is already paused.")

        voice.pause()
        await ctx.send(f"Paused audio in {voice.channel.mention}.")

    @commands.command(name="resume")
    async def jsk_vc_resume(self, ctx: commands.Context):
        """
        Resumes a running audio source, if there is one.
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        voice = ctx.guild.voice_client

        if not voice.is_paused():
            return await ctx.send("Audio is not paused.")

        voice.resume()
        await ctx.send(f"Resumed audio in {voice.channel.mention}.")

    @commands.command(name="volume")
    async def jsk_vc_volume(self, ctx: commands.Context, *, percentage: float):
        """
        Adjusts the volume of an audio source if it is supported.
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        volume = max(0.0, min(1.0, percentage / 100))

        source = ctx.guild.voice_client.source

        if not isinstance(source, discord.PCMVolumeTransformer):
            return await ctx.send("This source doesn't support adjusting volume or "
                                  "the interface to do so is not exposed.")

        source.volume = volume

        await ctx.send(f"Volume set to {volume * 100:.2f}%")

    @commands.command(name="play", aliases=["play_local"])
    async def jsk_vc_play(self, ctx: commands.Context, *, uri: str):
        """
        Plays audio direct from a URI.
        Can be either a local file or an audio resource on the internet.
        """

        if not self.connected_check(ctx):
            await self.jsk_vc_join(ctx)

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # remove embed maskers if present
        uri = uri.lstrip("<").rstrip(">")

        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(uri)))
        await ctx.send(f"Playing in {voice.channel.mention}.")


class YouTubeFeature(VoiceFeature):
    """
    Feature containing the youtube-dl command
    """

    @commands.command(parent="jsk_voice", name="youtube_dl", aliases=["youtubedl", "ytdl", "yt"])
    async def jsk_vc_youtube_dl(self, ctx: commands.Context, *, url: str):
        """
        Plays audio from youtube_dl-compatible sources.
        """

        if not VoiceFeature.connected_check(ctx):
            return await ctx.send("Not connected to a voice channel in this guild.")

        if not youtube_dl:
            return await ctx.send("youtube_dl is not installed.")

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")

        voice.play(discord.PCMVolumeTransformer(BasicYouTubeDLSource(url)))
        await ctx.send(f"Playing in {voice.channel.mention}.")

def setup(bot):
    bot.add_cog(YouTubeFeature(bot))
