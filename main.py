import os, asyncio, discord
from discord.ext import commands
import yt_dlp, spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- ตั้งค่าพื้นฐาน ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# เชื่อมต่อ Spotify (ใช้ค่าจาก Railway Variables)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET")
))

# คิวเพลง
song_queue = []

# การตั้งค่าดึงเสียง (ปรับเพื่อลดการโดนบล็อก)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'add_header': [
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ]
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- ระบบจัดการการเล่นเพลง ---

def play_next(ctx):
    if len(song_queue) > 0:
        song_queue.pop(0) # ลบเพลงที่เล่นจบแล้ว
        if len(song_queue) > 0:
            next_song = song_queue[0]
            # ใช้ bot.loop เพื่อรันฟังก์ชัน async ใน callback
            coro = start_playing(ctx, next_song)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("หมดคิวแล้วจ้า! เพิ่มเพลงได้นะคุณเปรม"), bot.loop)

async def start_playing(ctx, song_info):
    vc = ctx.voice_client
    if not vc: return
    
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(song_info['url'], download=False)
            url = info['url'] if 'url' in info else info['entries'][0]['url']
            
            # แก้ไข: ห้ามใส่ await หน้า FFmpegOpusAudio (แก้ Error ในรูป 7ac305)
            source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            
            vc.play(source, after=lambda e: play_next(ctx))
            await ctx.send(f"🎶 **กำลังเล่น:** {song_info['title']}")
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send(f"⚠️ เล่นเพลง '{song_info['title']}' ไม่ได้ ข้ามไปเพลงถัดไปนะจ๊ะ")
            play_next(ctx)

# --- คำสั่งบอท ---

@bot.event
async def on_ready():
    print(f'{bot.user.name} Is Online!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice: return await ctx.send("คุณเปรมต้องเข้าห้องเสียงก่อนนะค่า‼️")
    vc = ctx.voice_client if ctx.voice_client else await ctx.author.voice.channel.connect()

    async with ctx.typing():
        # 1. จัดการ Spotify
        if "spotify.com" in search:
            try:
                if "playlist" in search:
                    results = sp.playlist_items(search)
                    for item in results['items']:
                        if item['track']:
                            t = item['track']
                            song_queue.append({'url': f"ytsearch:{t['name']} {t['artists'][0]['name']}", 'title': t['name']})
                    await ctx.send(f"📂 เพิ่ม {len(results['items'])} เพลงจาก Spotify แล้วจ้า!")
                else:
                    t = sp.track(search)
                    song_queue.append({'url': f"ytsearch:{t['name']} {t['artists'][0]['name']}", 'title': t['name']})
                    await ctx.send(f"🔅 เพิ่มเพลง: **{t['name']}** เข้าคิว")
            except:
                return await ctx.send("อ่าน Spotify ไม่ได้จ้า เช็ครหัสใน Railway ด้วยนะ")
        
        # 2. ค้นหาทั่วไป
        else:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(search, download=False)
                    if 'entries' in info: info = info['entries'][0]
                    song_queue.append({'url': info['webpage_url'], 'title': info['title']})
                    await ctx.send(f"➕ เพิ่มเข้าคิว: **{info['title']}**")
                except:
                    return await ctx.send("❌ YouTube บล็อกครับ ลองเปลี่ยนชื่อเพลงดูนะ")

        # ถ้าบอทไม่ได้เล่นเพลงอยู่ ให้เริ่มเล่น
        if not vc.is_playing() and len(song_queue) == 1:
            await start_playing(ctx, song_queue[0])

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ ข้ามให้แล้วนะคุณเปรม!")

@bot.command()
async def queue(ctx):
    if not song_queue: return await ctx.send("คิวว่างจ้า")
    msg = "**🎵 คิวเพลงตอนนี้:**\n"
    for i, s in enumerate(song_queue[:10], 1):
        msg += f"{i}. {s['title']}\n"
    await ctx.send(msg)

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        song_queue.clear()
        await ctx.send("ไปแล้วนะ บ๊ายบาย! 👋")

bot.run(os.environ.get("DISCORD_TOKEN"))
