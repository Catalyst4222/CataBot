import asyncio
import random
import time
from typing import Optional, Coroutine, TYPE_CHECKING

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL

from .utils import sync_to_thread, short_diff_from_unix, short_diff_from_time, chunk

if TYPE_CHECKING:
    from .MusicCog import VoiceFeature

BASIC_OPTS = {
    'format': 'webm[abr>0]/bestaudio/best',
    'prefer_ffmpeg': True,
    'quiet': True,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/75.0.3770.80 Safari/537.36 ",
    'cachedir': False,
    "extract_flat": 'in_playlist'
}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn'}


class Song:
    __slots__ = ('data', 'url', 'title', 'author', 'duration', 'channel', 'playlist', 'start_time')

    def __init__(self, data: dict):
        self.data = data
        self.url = data['url']
        self.title = data.get('title', self.url)

        self.author = data.get('uploader')
        self.channel = data.get('channel_url')
        self.playlist = data.get('playlist')

        self.duration = data.get('duration', 0)
        self.start_time: Optional[int] = None

    def __len__(self):
        return self.duration

    def __str__(self):
        return self.title

    def start(self):
        self.start_time = time.time()

    @property
    def elapsed_time(self) -> Optional[str]:
        if self.start_time is None:
            return None
        return f'{short_diff_from_unix(self.start_time)}/{self.duration_str or "unknown"}'

    @property
    def duration_str(self):
        return short_diff_from_time(self.duration)

    @property
    def embed(self) -> discord.Embed:
        return discord.Embed(title=self.title, url=self.url) \
            .set_thumbnail(url=self.data['thumbnail']) \
            .set_author(name=self.author, url=self.channel) \
            .add_field(name='Playlist', value=self.playlist) \
            .add_field(name='Duration', value=self.elapsed_time)

    # muscle memory
    def to_embed(self) -> discord.Embed:
        return self.embed


class Queue:
    __slots__ = ('bot', 'cog', 'bound_channel', 'voice', 'ctx',
                 'queue', 'extractor',
                 'loop', 'loopqueue', 'volume', 'silent')

    def __init__(self, ctx: commands.Context):
        self.bot: commands.Bot = ctx.bot
        # assert isinstance(ctx.cog, VoiceFeature)
        self.cog: "VoiceFeature" = ctx.cog
        self.ctx = ctx
        self.bound_channel: discord.TextChannel = ctx.channel
        self.voice: discord.VoiceClient = ctx.guild.voice_client
        self.queue: list[Song] = []
        self.loop: bool = False
        self.loopqueue: bool = False
        self.volume: int = 100
        self.extractor: Optional['Extractor'] = None
        self.silent: bool = False

    @property
    def _create_task(self):
        return self.bot.loop.create_task

    def _send(self, *args, **kwargs) -> Optional[discord.Message]:
        if not self.silent:
            return self._create_task(self.bound_channel.send(*args, **kwargs))

    def add(self, song: Song):
        self.queue.append(song)

    def extend(self, songs: list[Song]):
        self.queue.extend(songs)

    def skip(self, amount=1):
        if self.loopqueue:
            queue = self.queue
            queue.extend = [queue.pop(0) for _ in range(amount - 1) if len(queue)]
        else:
            try:
                [self.queue.pop(0) for _ in range(amount - 1)]
            except IndexError:
                pass
        self.voice.stop()

        if not self.queue:
            self.cleanup()

    def shuffle(self):
        first = self.queue.pop(0)
        random.shuffle(self.queue)
        self.queue.insert(0, first)

    # def _get_player(self, source: str, type_: str):
    #     if type_ == 'uri':
    #         return discord.FFmpegPCMAudio(source)
    #     elif type_ == 'url':
    #         return BasicYouTubeDLSource(source)
    #     else:
    #         raise ValueError(f'Unexpected value: {type_ }')

    def cleanup(self):
        self.queue = [None]
        # self.guild.voice_client.stop()
        try:
            self._create_task(self.voice.disconnect())
        except AttributeError:
            pass
        # noinspection PyProtectedMember
        self.cog._queues.remove(self)

    def prime_song(self):
        vc = self.voice
        if not self.queue:
            return

        if vc is not None and not vc.is_playing():
            source = self.queue[0]
            if source.duration == 0:
                print(source)
                print(source.url)
            source.start()
            self._create_task(self.bound_channel.send(f'Now playing {source.title}'))

            player = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    source.url, **FFMPEG_OPTIONS
                )
            )

            player.volume = self.volume

            self.voice.play(player, after=self.after)

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
                self._send('An error happened managing the queue')
                return self.cleanup()
            # self._send(f'Finished playing {finished.title}')
            if self.loopqueue:
                self.queue.append(finished)

        if self.queue:
            self.prime_song()

        else:
            self._send('The queue is empty, disconnecting')
            return self.cleanup()
        # else:
        #     self._create_task(self.bound_channel.send(f'Finished playing {finished}'))

    def __len__(self):
        return len(self.queue)


class Extractor:
    def __init__(self, queue: Queue, **options):
        self.queue = queue
        self._ytdl = YoutubeDL(BASIC_OPTS | options)

    def _extract(self, link: str, download: bool = False) -> dict:
        return self._ytdl.extract_info(link, download=download)

    @sync_to_thread
    def extract_single_vid(self, url: str) -> Song:
        data = self._extract(url)
        if 'url' not in data:
            raise ExtractionError('Invalid url')
        return Song(data)

    # noinspection PyProtectedMember
    async def play_single_song(self, url):
        song = await self.extract_single_vid(url)
        self.queue.add(song)

        self.queue.prime_song()

        if not self.queue.voice.is_playing():
            await self.queue._send(f"Playing in {self.queue.voice.channel.mention}.")
        else:
            await self.queue._send('File added to queue')

    async def play_playlist(self, url: str):
        # if 'youtube' not in url:
        #     raise ExtractionError('Only YouTube links support playlists')
        info = self._extract(url)

        coros: list[Coroutine[None, None, Song]] = [self.extract_single_vid(item['url']) for item in
                                                    iter(info['entries'])]

        msg = await self.queue.bound_channel.send('Processing playlist')

        first = await coros.pop()
        self.queue.add(first)
        self.queue.prime_song()

        for group in chunk(coros, size=25):
            songs = await asyncio.gather(*group, return_exceptions=True)
            for item in songs:
                if isinstance(item, Song):
                    self.queue.add(item)
                else:
                    # noinspection PyUnresolvedReferences
                    await msg.channel.send(f'Exception Caught: `{item.__class__.__name__}: {item.msg}`')

        await msg.reply('Playlist added!')


class ExtractionError(Exception):
    pass
