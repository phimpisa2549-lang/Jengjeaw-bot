import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- ระบบคิวเพลงแบบปรับปรุงใหม่ ---
song_queue = []

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def play_next(ctx):
    if len(song_queue) > 0:
        # ลบเพลงที่เพิ่งเล่นจบออกจากคิว
        song_queue.pop(0)
        
        # ถ้ายังมีเพลงเหลือในคิว ให้เล่นเพลงถัดไป
        if len(song_queue) > 0:
            next_song = song_queue[0]
            url = next_song['url']
            source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda e: play_next(ctx))
            asyncio.run_coroutine_threadsafe(ctx.send(f"▶️ เพลงถัดไปงับ: **{next_song['title']}**"), bot.loop)

@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')

@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("คุณต้องเข้าห้องเสียงก่อนนะค่า!")
    
    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client if ctx.voice_client else await channel.connect()

    async with ctx.typing():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                
                song_data = {'url': info['url'], 'title': info['title']}
                song_queue.append(song_data)
                
                if not voice_client.is_playing():
                    source = await discord.FFmpegOpusAudio.from_probe(song_data['url'], **FFMPEG_OPTIONS)
                    voice_client.play(source, after=lambda e: play_next(ctx))
                    await ctx.send(f" ตอนนี้กำลังเล่น: **{song_data['title']}**🩷")
                else:
                    await ctx.send(f"🔅 เพิ่มเพลง: **{song_data['title']}**ลงในคิวเพลงเเล้วค่า!(ลำดับที่ {len(song_queue)-1})")
            except Exception as e:
                await ctx.send("หาเพลงไม่เจอค่า ลองพิมพ์ชื่อเพลงใหม่อีกทีนะ")

# --- คำสั่งใหม่: ดูคิวเพลง ---
@bot.command()
async def queue(ctx):
    if not song_queue:
        return await ctx.send("ตอนนี้คิวว่างเลยคับ 🎶")
    
    msg = "**🌟 รายการเพลงในคิว:**\n"
    for i, song in enumerate(song_queue):
        if i == 0:
            msg += f"🎀 กำลังเล่น: {song['title']}\n"
        else:
            msg += f"{i}. {song['title']}\n"
    await ctx.send(msg)

# --- คำสั่งใหม่: ข้ามเพลง ---
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() # เมื่อหยุด play_next จะทำงานอัตโนมัติ
        await ctx.send("⏭️ ไปเพลงต่อไปดีกว่างับ!")
    else:
        await ctx.send("ไม่มีเพลงให้ข้ามจ้า ❌")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("ปิดเพลงและล้างคิวเรียบร้อยจ้า!")

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
