import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- ตั้งค่าสิทธิ์บอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- เชื่อมต่อ Spotify (ใช้รหัสจาก Railway Variables) ---
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET")
))

# --- ตั้งค่าคิวเพลงและตัวเล่นเสียง ---
song_queue = []

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,  # เปิดให้ดึงข้อมูลเพลย์ลิสต์ได้
    'quiet': True,
    'default_search': 'ytsearch',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- ฟังก์ชันเล่นเพลงถัดไปอัตโนมัติ ---
def play_next(ctx):
    if len(song_queue) > 0:
        song_queue.pop(0)  # ลบเพลงที่จบแล้ว
        if len(song_queue) > 0:
            next_song = song_queue[0]
            
            # ถ้าเป็นเพลงจาก Spotify (ytsearch) ต้องดึง URL จริงก่อนเล่น
            url = next_song['url']
            if url.startswith('ytsearch:'):
                with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    url = info['entries'][0]['url']

            source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda e: play_next(ctx))
            asyncio.run_coroutine_threadsafe(ctx.send(f"▶️🔥เพลงถัดไปมาเเล้วงับ: **{next_song['title']}**"), bot.loop)

@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("คุณต้องเข้าห้องเสียงก่อนนะค่า‼️")
    
    channel = ctx.author.voice.channel
    vc = ctx.voice_client if ctx.voice_client else await channel.connect()

    async with ctx.typing():
        # --- 1. กรณีเป็น Spotify Playlist / Track ---
        if "spotify.com" in search:
            try:
                if "playlist" in search:
                    results = sp.playlist_items(search)
                    for item in results['items']:
                        t = item['track']
                        song_queue.append({'url': f"ytsearch:{t['name']} {t['artists'][0]['name']}", 'title': t['name']})
                    await ctx.send(f"❣️เพิ่มเพลงจาก Spotify Playlist {len(results['items'])} เรียบร้อยเว้ย⁉️")
                else:
                    t = sp.track(search)
                    song_queue.append({'url': f"ytsearch:{t['name']} {t['artists'][0]['name']}", 'title': t['name']})
                    await ctx.send(f"🔅 เพิ่มเพลง: **{t['name']}** ลงในคิวแล้วค่า")
            except:
                return await ctx.send("อ่าน Spotify ไม่ได้จ้า เช็คหน่อยดิว่ะ🔥🔥")

        # --- 2. กรณีเป็น YouTube Playlist / Video หรือค้นหาชื่อ ---
        else:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(search, download=False)
                # ถ้าเป็น YouTube Playlist
                if 'entries' in info and "playlist" in search:
                    for entry in info['entries']:
                        song_queue.append({'url': entry['url'], 'title': entry['title']})
                    await ctx.send(f"❣️เพิ่มเพลย์ลิสต์ YouTube {len(info['entries'])} เรียบร้อยเว้ย⁉️")
                # ถ้าเป็นเพลงเดียว
                else:
                    if 'entries' in info: info = info['entries'][0]
                    song_queue.append({'url': info['url'], 'title': info['title']})
                    if vc.is_playing():
                        await ctx.send(f"🔅 เพิ่มเพลง: **{info['title']}** ลงในคิวแล้วค่า")

        # --- เริ่มเล่นถ้าบอทว่าง ---
        if not vc.is_playing() and song_queue:
            curr = song_queue[0]
            url = curr['url']
            if url.startswith('ytsearch:'):
                with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
                    url = ydl.extract_info(url, download=False)['entries'][0]['url']
            
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: play_next(ctx))
            await ctx.send(f"🌟➖ตอนนี้กำลังเล่น: **{curr['title']}**🩷")

@bot.command()
async def queue(ctx):
    if not song_queue: return await ctx.send("⛔️ตอนนี้คิวว่างเปล่าคับ 🎶")
    msg = "**🌟🎧 รายการเพลงในคิว:**\n"
    for i, song in enumerate(song_queue[:10]):
        msg += f"{'🎀🫧 กำลังเล่น: ' if i==0 else f'{i}. '}{song['title']}\n"
    await ctx.send(msg + ("\n...(มีต่อด้วย)" if len(song_queue) > 10 else ""))

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ ไปเพลงต่อไปดีกว่างับ!")
    else:
        await ctx.send("ไม่มีเพลงให้เปลี่ยนละ ❌")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("➖ปิดเพลงและล้างคิวเรียบร้อยจ้า➖")

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
