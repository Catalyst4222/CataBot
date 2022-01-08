from typing import Optional, Union

import dinteractions_Paginator
import discord
import discord.opus
from discord.ext import commands, tasks

from .YouTube import Song, Queue, Extractor
from .utils import chunk, Cache, AsyncCache


class VoiceFeature(commands.Cog):
    """
    Feature containing the core voice-related commands
    """
    def __init__(self, bot):
        self._bot: commands.Bot = bot
        self._queues: list[Queue] = []

    def cog_unload(self):
        for queue in self._queues:
            queue.cleanup()

    def _get_queue(self, ctx) -> Queue:
        guild = ctx.guild
        for queue in self._queues:
            if queue.ctx.guild == guild:
                return queue
        new_queue = Queue(ctx)
        new_queue.extractor = Extractor(new_queue)
        self._queues.append(new_queue)
        return new_queue

    @tasks.loop(hours=1, reconnect=True)
    async def queue_clean(self):
        for queue in self._queues:
            if not queue.voice.is_connected():
                del queue

    @staticmethod
    @AsyncCache
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
            await ctx.send("Not connected.")
            return

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
                await ctx.send("Member has no voice channel.")
                return

        voice = ctx.guild.voice_client

        if voice:
            await voice.move_to(destination)
        else:
            await destination.connect(reconnect=True)

        await ctx.send(f"Connected to {destination.mention}.")

    @commands.command(name="disconnect", aliases=["dc", "fuckoff", "leave"])
    async def jsk_vc_disconnect(self, ctx: commands.Context):
        """
        Disconnects from the voice channel in this guild, if there is one.
        """
        voice = ctx.guild.voice_client

        if not voice:
            return await ctx.send("Not connected to a voice channel in this guild.")

        queue = self._get_queue(ctx)
        queue.cleanup()

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
        self._get_queue(ctx).skip(amount)
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
    async def jsk_vc_volume(self, ctx: commands.Context, *, percentage: Optional[float]):
        """
        Adjusts the volume of an audio source if it is supported.
        """

        if not self.playing_check(ctx):
            return await ctx.send("The voice client in this guild is not playing anything.")

        if percentage is None:
            return await ctx.send(f'Current volume: {self._get_queue(ctx).volume:.2f}%')

        volume = max(0.0, min(1.0, percentage / 100))

        source = ctx.guild.voice_client.source

        if not isinstance(source, discord.PCMVolumeTransformer):
            return await ctx.send("This source doesn't support adjusting volume or "
                                  "the interface to do so is not exposed.")

        source.volume = self._get_queue(ctx).volume = volume

        await ctx.send(f"Volume set to {volume * 100:.2f}%")

    @commands.command(name='loop', aliases=['l'])
    async def jsk_vc_loop(self, ctx: commands.Context, state: bool = None):
        queue = self._get_queue(ctx)
        if queue is None:
            await ctx.send('There is no music queue bound to this channel')

        queue.loop = not queue.loop if state is None else state

        await ctx.send(f'Song loop set to {queue.loop}')

    @commands.command(name='loopqueue', aliases=['lq'])
    async def jsk_vc_loopqueue(self, ctx: commands.Context, state: bool = None):
        queue = self._get_queue(ctx)
        if queue is None:
            await ctx.send('There is no music queue bound to this channel')

        queue.loopqueue = not queue.loopqueue if state is None else state

        await ctx.send(f'Queue loop set to {queue.loopqueue}')

    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        self._get_queue(ctx).shuffle()
        await ctx.send('Queue shuffled')

    @commands.command(name='make_sticky')
    async def stickify(*_): raise NotImplementedError

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

        queue = self._get_queue(ctx)
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

        # voice = ctx.guild.voice_client

        # if voice.is_playing():
        #     voice.stop()

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")

        if 'list' in url:
            return await ctx.send('Playlists are not supported using this command. '
                                  f'Use `{ctx.prefix}playlist` instead')


        queue = self._get_queue(ctx)
        await queue.extractor.play_single_song(url)

        # # uri = youtube_to_ffmpeg(url)
        # ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)  # 'noplaylist': True
        # info = ytdl.extract_info(url, download=False)
        # if 'url' not in info:
        #     return await ctx.send('Invalid link')
        #
        # queue.add(Song(info))
        #
        # queue.prime_song()
        # if not voice.is_playing():
        #     await ctx.send(f"Playing in {voice.channel.mention}.")
        # else:
        #     await ctx.send('File added to queue')

    @commands.command(name='now_playing', aliases=['np'])
    async def now_playing(self, ctx: commands.Context):
        """
        Show details of the currently playing song
        """
        queue = self._get_queue(ctx)
        await ctx.send(embed=queue.queue[0].embed)

    @commands.command(name='playlist', aliases=['pl'])
    async def playlist(self, ctx: commands.Context, *, url: str):
        """
        Play a song from a youtube playlist
        Currently, most other playlists from sites are untested
        """
        if not self.connected_check(ctx):
            await self.jsk_vc_join(ctx)

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")

        queue = self._get_queue(ctx)
        await queue.extractor.play_playlist(url)

        # # uri = youtube_to_ffmpeg(url)
        # ytdl = youtube_dl.YoutubeDL({"extract_flat": 'in_playlist', **BASIC_OPTS})
        # info = ytdl.extract_info(url, download=False)
        #
        # print(info)
        #
        # song_links = ("https://youtube.com/v/" + str(dict_['id']) for dict_ in info['entries'])
        # song_info = (ytdl.extract_info(link, download=False) for link in song_links)  # Something here?
        #
        # queue = self._get_queue(ctx)
        #
        # first_song = next(song_info)
        # queue.add(Song(first_song))
        # queue.prime_song()
        #
        # msg = await ctx.send('First song primed, chunking the remainder')
        #
        # # TODO: show progress
        # for group in chunk(song_info, size=25):
        #
        #     def blocking():
        #         for song in group:
        #             queue.add(Song(song))
        #
        #     await asyncio.to_thread(blocking)
        #
        #     print('Chunk loaded')
        #     queue.prime_song()
        #
        # # [queue.add(song) for song in songs]
        # await msg.reply('Playlist added')
        # queue.prime_song()

    @commands.command(name='search')
    async def search(self, ctx, *, phrase):

        """
        Play a song from a youtube playlist
        Currently, most other playlists from sites are untested
        """
        if not self.connected_check(ctx):
            await self.jsk_vc_join(ctx)

        queue = self._get_queue(ctx)
        await queue.extractor.search_song('ytsearch:' + phrase)

    @commands.command(name='_queues')
    @commands.is_owner()
    async def owner_queues(self, ctx):
        await ctx.send(
            '\n\n'.join(
                f"Server: {queue.ctx.guild}\nSongs: {len(queue)}"
                for queue in self._queues
            ) or None
        )

    @commands.command(name='queue', aliases=['q'])
    async def queue(self, ctx):
        """Show the queue"""
        if not self.playing_check(ctx):
            return await ctx.send('Nothing is playing')

        songs = self._get_queue(ctx).queue.copy()
        # np = songs.pop(0)

        embeds = []
        for group in chunk(songs):
            descriptions = [
                f'{song} | `{song.duration_str}`'
                for song in group
            ]
            embed = discord.Embed(title='title', description='\n\n'.join(descriptions))
            embeds.append(embed)

        await dinteractions_Paginator.Paginator(
            bot=self._bot, ctx=ctx, pages=embeds, useIndexButton=True,
            timeout=60, deleteAfterTimeout=True
        ).run()



def setup(bot):
    bot.add_cog(VoiceFeature(bot))
