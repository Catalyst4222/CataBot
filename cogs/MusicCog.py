from discord.ext import commands
from typing import Optional, Union
import discord
import youtube_dl
import discord.opus
import discord.voice_client
from discord.ext import commands


BASIC_OPTS = {
    'format': 'webm[abr>0]/bestaudio/best',
    'prefer_ffmpeg': True,
    'quiet': True,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/75.0.3770.80 Safari/537.36 ",
    'cachedir': False
}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}


class BasicYouTubeDLSource(discord.FFmpegPCMAudio):
    """
    Basic audio source for youtube_dl-compatible URLs.
    """

    def __init__(self, url, download: bool = False):
        ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
        info = ytdl.extract_info(url, download=download)
        super().__init__(info['url'])


def youtube_to_ffmpeg(url, download: bool = False):
    ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
    info = ytdl.extract_info(url, download=download)
    return info['url']


class Song:
    __slots__ = ('data', 'url', 'title', 'author', 'duration',)

    def __init__(self, data: dict,):
        # # Expected format:
        # # noinspection PyStatementEffect
        # {
        #     'name': Optional[str],
        #     'url': str,
        # }
        # print(data)
        self.data = data
        self.url = data['url']
        self.title = data.get('title') or self.url
        self.author = data.get('author')
        self.duration = data.get('duration') or float('inf')

    def __len__(self):
        return self.duration

    def __str__(self):
        return self.title

    @property
    def embed(self) -> discord.Embed:
        # Do later
        embed = discord.Embed(title=self.title)
        embed.set_thumbnail(url=self.data['thumbnail'])

        embed.set_author(name=self.author, url=self.data.get('channel_url', discord.Embed.Empty))

        return embed


class Queue:
    __slots__ = ('bot', 'voice_channel', 'bound_channel', 'guild', 'queue', 'loop', 'loopqueue', 'ctx')

    def __init__(self, bot, ctx: commands.Context):
        self.bot: commands.Bot = bot
        self.ctx = ctx
        self.voice_channel: discord.VoiceClient = ctx.guild.voice_client
        self.bound_channel: discord.TextChannel = ctx.channel
        self.guild: discord.Guild = ctx.guild
        self.queue: list[Song] = []
        self.loop: bool = False
        self.loopqueue: bool = False

    @property
    def _create_task(self):
        return self.bot.loop.create_task

    def _send(self, *args, **kwargs):
        return self._create_task(self.bound_channel.send(*args, **kwargs))

    def add(self, song: Song):
        self.queue.append(song)

    def skip(self, amount=1):
        [self.queue.pop(0) for _ in range(amount-1)]
        self.voice_channel.stop()

    # def _get_player(self, source: str, type_: str):
    #     if type_ == 'uri':
    #         return discord.FFmpegPCMAudio(source)
    #     elif type_ == 'url':
    #         return BasicYouTubeDLSource(source)
    #     else:
    #         raise ValueError(f'Unexpected value: {type_ }')

    def cleanup(self):
        self.queue = []
        # self.guild.voice_client.stop()
        self._create_task(self.guild.voice_client.disconnect())

    def prime_song(self):
        vc = self.guild.voice_client
        if not self.queue:
            return

        if vc is not None and not vc.is_playing():
            self.guild.voice_client.play(
                discord.PCMVolumeTransformer(
                    # self._get_player(*source)
                    discord.FFmpegPCMAudio(
                        self.queue[0].url, **FFMPEG_OPTIONS
                    )
                ),
                after=self.after
            )

    def after(self, error=None):
        # raise NotImplementedError
        if error is not None:
            cog = self.bot.get_cog('Events')
            self._create_task(cog.error_checker(self.ctx, error))

        # looping logic, will not affect next song playing
        # it just works, no touchy
        if not self.loop:
            try:
                finished = self.queue.pop(0)
            except IndexError:
                return
            # self._send(f'Finished playing {finished.title}')
            if self.loopqueue:
                self.queue.append(finished)

        if self.queue:
            source = self.queue[0]
            self._create_task(self.bound_channel.send(f'Now playing {source.title}'))

            self.prime_song()
        # else:
        #     self._create_task(self.bound_channel.send(f'Finished playing {finished}'))






class VoiceFeature(commands.Cog):
    """
    Feature containing the core voice-related commands
    """
    def __init__(self, bot):
        self._bot: commands.Bot = bot
        self._queues: dict[int, Queue] = {}

    def cog_unload(self):
        for queue in self._queues.values():
            queue.cleanup()

    def _get_queue(self, ctx) -> Optional[Queue]:
        guild = ctx.guild
        for queue in self._queues.values():
            if queue.guild == guild:
                return queue

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
                          destination: Union[discord.VoiceChannel, discord.Member] = None):
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
        self._queues[ctx.guild.id] = Queue(self._bot, ctx)

        await ctx.send(f"Connected to {destination.mention}.")

    @commands.command(name="disconnect", aliases=["dc", "fuckoff", "leave"])
    async def jsk_vc_disconnect(self, ctx: commands.Context):
        """
        Disconnects from the voice channel in this guild, if there is one.
        """
        voice = ctx.guild.voice_client

        if not voice:
            return await ctx.send("Not connected to a voice channel in this guild.")

        queue = self._queues.get(ctx.guild.id)
        await queue.cleanup()

        # await voice.disconnect()
        await ctx.send(f"Disconnected from {voice.channel.mention}.")

    @commands.command(name="skip", aliases=['s'])
    async def jsk_vc_skip(self, ctx: commands.Context, amount=1):
        """
        Skip the current song
        Add a number after to skip multiple
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        voice = ctx.guild.voice_client

        voice.stop()
        self._queues[ctx.guild.id].skip(amount)
        await ctx.send(f"Skipped the song in {voice.channel.mention}.")

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

        if not self.connected_check(ctx):
            return await ctx.send("There is no voice client in this guild.")

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

    @commands.command(name='loop', aliases=['l'])
    async def jsk_vc_loop(self, ctx: commands.Context, state: bool = None):
        queue = self._queues.get(ctx.guild.id)
        if queue is None:
            await ctx.send('There is no music queue bound to this channel')

        queue.loop = not queue.loop if state is None else state

        await ctx.send(f'Song loop set to {queue.loop}')

    @commands.command(name='loopqueue', aliases=['lq'])
    async def jsk_vc_loopqueue(self, ctx: commands.Context, state: bool = None):
        queue = self._queues.get(ctx.guild.id)
        if queue is None:
            await ctx.send('There is no music queue bound to this channel')

        queue.loopqueue = not queue.loopqueue if state is None else state

        await ctx.send(f'Queue loop set to {queue.loopqueue}')

    @commands.command(name="uri", aliases=["play_from_uri"])
    async def jsk_vc_play(self, ctx: commands.Context, *, uri: Optional[str]):
        """
        Plays audio direct from a URI.
        Can be either a local file or an audio resource on the internet.
        """

        await ctx.send('This feature is currently unsupported')

        if not self.connected_check(ctx):
            await self.jsk_vc_join(ctx)

        voice = ctx.guild.voice_client

        # if not voice.is_paused():
        #     voice.resume()
        #     await ctx.send("Audio unpaused.")

        # remove embed maskers if present
        uri = uri.lstrip("<").rstrip(">")

        queue = self._queues[ctx.guild.id]
        song = Song({'url': uri, 'title': uri})
        queue.add(song)

        if not voice.is_playing():
            queue.prime_song()
            await ctx.send(f"Playing in {voice.channel.mention}.")
        else:
            await ctx.send('File added to queue')


    @commands.command(parent="jsk_voice", name="play", aliases=["youtubedl", "p", "yt"])
    async def jsk_vc_youtube_dl(self, ctx: commands.Context, *, url: str):
        """
        Plays audio from youtube_dl-compatible sources.
        """

        if not self.connected_check(ctx):
            await self.jsk_vc_join(ctx)

        # if not youtube_dl:
        #     return await ctx.send("youtube_dl is not installed.")

        voice = ctx.guild.voice_client

        # if voice.is_playing():
        #     voice.stop()

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")


        # uri = youtube_to_ffmpeg(url)
        ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
        info = ytdl.extract_info(url, download=False)
        if 'url' not in info:
            return await ctx.send('Invalid link')

        queue = self._queues[ctx.guild.id]
        queue.add(Song(info))

        if not voice.is_playing():
            voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS)), after=queue.after)
            await ctx.send(f"Playing in {voice.channel.mention}.")
        else:
            await ctx.send('File added to queue')


def setup(bot):
    bot.add_cog(VoiceFeature(bot))
