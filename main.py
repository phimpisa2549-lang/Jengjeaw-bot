import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

import ctypes
import ctypes.util

try:
    if not discord.opus.is_loaded():
        lib = ctypes.util.find_library('opus')
        if lib:
            discord.opus.load_opus(lib)
        else:
            discord.opus.load_opus('libopus.so.0')
    print("Opus loaded successfully!")
except Exception as e:
    print(f"Opus loading note: {e}")
    
bot = commands.Bot(command_prefix="!", intents=intents)

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def get_audio_source(url: str):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        if "entries" in info:
            info = info["entries"][0]
        audio_url = info["url"]
        title = info.get("title", "Unknown")
        return audio_url, title


@bot.event
async def on_ready():
    print(f"Jengjeaw is online! Logged in as {bot.user}")


@bot.command(name="hello")
async def hello(ctx: commands.Context):
    await ctx.send("Sawadee krap! I'm Jengjeaw, your music bot! Use !play <song> to start playing music.")


@bot.command(name="play")
async def play(ctx: commands.Context, *, query: str):
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel first!")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    voice_client = ctx.voice_client

    await ctx.send(f"Searching for: **{query}**...")

    try:
        loop = asyncio.get_event_loop()
        audio_url, title = await loop.run_in_executor(None, get_audio_source, query)
    except Exception as e:
        await ctx.send(f"Could not find or play that song. Error: {e}")
        return

    if voice_client.is_playing():
        voice_client.stop()

    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
    voice_client.play(
        discord.PCMVolumeTransformer(source, volume=0.5),
        after=lambda e: print(f"Playback finished: {e}" if e else "Playback done"),
    )

    await ctx.send(f"Now playing: **{title}**")


@bot.command(name="stop")
async def stop(ctx: commands.Context):
    if ctx.voice_client is None:
        await ctx.send("I'm not in a voice channel!")
        return

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    await ctx.voice_client.disconnect()
    await ctx.send("Stopped playing and left the voice channel.")


@bot.command(name="pause")
async def pause(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused.")
    else:
        await ctx.send("Nothing is playing right now.")


@bot.command(name="resume")
async def resume(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed!")
    else:
        await ctx.send("Nothing is paused.")


@bot.command(name="volume")
async def volume(ctx: commands.Context, vol: int):
    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("Nothing is playing right now.")
        return
    if not 0 <= vol <= 100:
        await ctx.send("Please give a volume between 0 and 100.")
        return
    ctx.voice_client.source.volume = vol / 100
    await ctx.send(f"Volume set to {vol}%")


@bot.command(name="commands", aliases=["help_jengjeaw"])
async def show_commands(ctx: commands.Context):
    embed = discord.Embed(
        title="Jengjeaw - Commands",
        description="Here are all available commands:",
        color=discord.Color.purple(),
    )
    embed.add_field(name="!hello", value="Say hello to Jengjeaw", inline=False)
    embed.add_field(name="!play <song>", value="Search and play a song from YouTube", inline=False)
    embed.add_field(name="!pause", value="Pause the current song", inline=False)
    embed.add_field(name="!resume", value="Resume a paused song", inline=False)
    embed.add_field(name="!stop", value="Stop playing and leave the voice channel", inline=False)
    embed.add_field(name="!volume <0-100>", value="Adjust the playback volume", inline=False)
    embed.set_footer(text="Jengjeaw Music Bot")
    await ctx.send(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    bot.run(DISCORD_TOKEN)
