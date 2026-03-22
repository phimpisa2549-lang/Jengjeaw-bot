import os, asyncio, discord
from discord.ext import commands
import yt_dlp

# --- ตั้งค่าสิทธิ์บอท ---
intents = discord.Intents.default()
intents.message_content = True  # ต้องเปิดใน Developer Portal ด้วยนะคับ
bot = commands.Bot(command_prefix="!", intents=intents)

song_queue = []

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'add_header': {'User-Agent': 'Mozilla/5.0'}
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- ระบบจัดการเพลงถัดไป ---
def play_next(ctx):
    if len(song_queue) > 0:
        song_queue.pop(0)
        if len(song_queue) > 0:
            next_song = song_queue[0]
            coro = start_playing(ctx, next_song)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("หมดคิวแล้วจ้า!"), bot.loop)

async def start_playing(ctx, song_info):
    vc = ctx.voice_client
    if not vc: return
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(song_info['url'], download=False)
            url = info['url'] if 'url' in info else info['entries'][0]['url']
            # ✅ แก้ Error: ห้ามมี await หน้า FFmpegOpusAudio
            source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: play_next(ctx))
            await ctx.send(f"▶️ กำลังเล่น: **{song_info['title']}**")
        except:
            await ctx.send("❌ เล่นเพลงนี้ไม่ได้จ้า")
            play_next(ctx)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} Is Ready!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice: return await ctx.send("เข้าห้องเสียงก่อนนะคับคุณเปรม‼️")
    vc = ctx.voice_client if ctx.voice_client else await ctx.author.voice.channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info: info = info['entries'][0]
            song_data = {'url': info['webpage_url'], 'title': info['title']}
            song_queue.append(song_data)
            
            if not vc.is_playing():
                await start_playing(ctx, song_data)
            else:
                await ctx.send(f"➕ เพิ่มเข้าคิว: **{info['title']}**")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ ข้ามเพลงให้แล้วนะคับ!")

@bot.command()
async def queue(ctx):
    if not song_queue: return await ctx.send("คิวว่างจ้า")
    msg = "**🎵 รายการคิวเพลง:**\n"
    for i, s in enumerate(song_queue[:10], 1):
        msg += f"{'▶️' if i==1 else str(i-1)+'.'} {s['title']}\n"
    await ctx.send(msg)

bot.run(os.environ.get("DISCORD_TOKEN"))
