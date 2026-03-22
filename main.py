import os, asyncio, discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# รายการเก็บคิวเพลง (เก็บเป็น Dictionary: {'url': ..., 'title': ...})
song_queue = []

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'add_header': ['User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36']
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- ฟังก์ชันจัดการคิวเพลง (เล่นเพลงถัดไปอัตโนมัติ) ---
def play_next(ctx):
    if len(song_queue) > 0:
        song_queue.pop(0) # ลบเพลงที่เพิ่งเล่นจบออก
        if len(song_queue) > 0:
            next_song = song_queue[0]
            # เรียกฟังก์ชันเล่นเพลงถัดไป
            coro = start_playing(ctx, next_song)
            asyncio.run_coroutine_threadsafe(coro, bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("หมดคิวแล้วนะคับคุณเปรม! เพิ่มเพลงต่อได้เลย 🎶"), bot.loop)

async def start_playing(ctx, song_info):
    vc = ctx.voice_client
    if not vc: return
    
    # ดึงข้อมูล URL ล่าสุด (ป้องกันลิงก์หมดอายุ)
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(song_info['url'], download=False)
        url = info['url'] if 'url' in info else info['entries'][0]['url']
        
        # ✅ ห้ามมี await หน้า FFmpegOpusAudio เพื่อป้องกัน Error "AudioSource not coroutine"
        source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
        vc.play(source, after=lambda e: play_next(ctx))
        await ctx.send(f"▶️ ตอนนี้กำลังเล่น: **{song_info['title']}** 🎵")

@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("คุณเปรมต้องเข้าห้องเสียงก่อนนะคับ‼️")
    
    vc = ctx.voice_client if ctx.voice_client else await ctx.author.voice.channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search, download=False)
                if 'entries' in info: info = info['entries'][0]
                
                # เพิ่มข้อมูลเพลงลงในคิว
                song_data = {'url': info['webpage_url'], 'title': info['title']}
                song_queue.append(song_data)
                
                if not vc.is_playing():
                    await start_playing(ctx, song_data)
                else:
                    await ctx.send(f"➕ เพิ่มเพลง **{info['title']}** ลงในคิวแล้ว (ลำดับที่ {len(song_queue)-1})")
            except Exception as e:
                print(f"Error: {e}")
                await ctx.send("❌ หาเพลงไม่เจอหรือ YouTube บล็อกครับ ลองพิมพ์ชื่อเพลงอื่นดูนะ")

# --- คำสั่งข้ามเพลง ---
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() # ฟังก์ชัน stop() จะไปเรียก after=play_next อัตโนมัติ
        await ctx.send("⏭️ ข้ามเพลงให้แล้วนะคับ!")
    else:
        await ctx.send("ตอนนี้ไม่ได้เล่นเพลงอะไรอยู่เลยนะคุณเปรม")

# --- คำสั่งดูคิวเพลง ---
@bot.command()
async def queue(ctx):
    if not song_queue:
        await ctx.send("ตอนนี้ยังไม่มีคิวเพลงครับคุณเปรม 🎶")
    else:
        msg = "**🎵 รายการคิวเพลงตอนนี้:**\n"
        for i, song in enumerate(song_queue):
            if i == 0:
                msg += f"▶️ กำลังเล่น: {song['title']}\n"
            else:
                msg += f"{i}. {song['title']}\n"
        await ctx.send(msg)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("ปิดเพลงและล้างคิวเรียบร้อยจ้า! 👋")

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
