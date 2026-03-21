import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# สร้างรายการเก็บคิวเพลง
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
                
                url = info['url']
                title = info['title']
                
                # เพิ่มชื่อเพลงลงในคิว
                song_queue.append(title)
                
                source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
                
                if voice_client.is_playing():
                    await ctx.send(f"เพิ่มเพลง **{title}** ลงในคิวแล้วค่า! (รอเพลงแรกจบก่อนนะ)")
                else:
                    voice_client.play(source, after=lambda e: song_queue.pop(0) if song_queue else None)
                    await ctx.send(f"ตอนนี้กำลังเล่น: **{title}** 🎵")
            except Exception as e:
                await ctx.send("หาเพลงไม่เจอค่า ลองพิมพ์ชื่อเพลงใหม่อีกทีนะ")

# --- คำสั่งใหม่: ดูคิวเพลง ---
@bot.command()
async def queue(ctx):
    if not song_queue:
        await ctx.send("ตอนนี้ยังไม่มีคิวเพลง 🎶")
    else:
        # แสดงรายการเพลงในคิว
        msg = "**รายการคิวเพลงตอนนี้:**\n"
        for i, title in enumerate(song_queue):
            if i == 0:
                msg += f"▶️ กำลังเล่น: {title}\n"
            else:
                msg += f"{i}. {title}\n"
        await ctx.send(msg)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear() # ล้างคิวเมื่อปิดบอท
        await ctx.voice_client.disconnect()
        await ctx.send("ปิดเพลงและล้างคิวเรียบร้อยจ้า!")

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
