import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

# --- 1. ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

song_queue = []

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- 2. ฟังก์ชันระบบเพลง ---

def play_next(ctx):
    if len(song_queue) > 0:
        song_queue.pop(0) # ลบเพลงที่จบแล้ว
        if len(song_queue) > 0:
            next_song = song_queue[0]
            coro = start_playing(ctx, next_song)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("หมดคิวแล้วจ้าคุณเปรม! 👋"), bot.loop)

async def start_playing(ctx, song_info):
    vc = ctx.voice_client
    if not vc: return
    
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(song_info['url'], download=False)
            url = info['url'] if 'url' in info else info['entries'][0]['url']
            
            # ✅ จุดที่ต้องระวังที่สุด: บรรทัดนี้ห้ามมี await นำหน้า
            # เพื่อป้องกัน RuntimeWarning: coroutine was never awaited
            source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            
            vc.play(source, after=lambda e: play_next(ctx))
            await ctx.send(f"▶️ **ตอนนี้กำลังเล่น:** {song_info['title']}")
        except Exception as e:
            await ctx.send(f"❌ เล่นเพลงไม่ได้ครับ: {song_info['title']}")
            play_next(ctx)

# --- 3. คำสั่งบอท ---

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} Is Ready!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("คุณเปรมต้องเข้าห้องเสียงก่อนนะคับ!")
    
    vc = ctx.voice_client if ctx.voice_client else await ctx.author.voice.channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search, download=False)
                if 'entries' in info: info = info['entries'][0]
                
                song_data = {'url': info['webpage_url'], 'title': info['title']}
                song_queue.append(song_data)
                
                if not vc.is_playing():
                    await start_playing(ctx, song_data)
                else:
                    await ctx.send(f"➕ เพิ่มเข้าคิว: **{info['title']}** (ลำดับที่ {len(song_queue)-1})")
            except:
                await ctx.send("❌ หาเพลงไม่เจอจ้า")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ ข้ามเพลงให้แล้วนะคับคุณเปรม!")

@bot.command()
async def queue(ctx):
    if not song_queue:
        return await ctx.send("คิวว่างจ้า 🎶")
    msg = "**🎵 รายการคิวเพลงตอนนี้:**\n"
    for i, s in enumerate(song_queue[:10], 1):
        msg += f"{'▶️ กำลังเล่น' if i==1 else str(i-1)+'.'}: {s['title']}\n"
    await ctx.send(msg)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("ปิดบอทและล้างคิวแล้วจ้า!")

bot.run(os.environ.get("DISCORD_TOKEN"))
