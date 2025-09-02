from keep_alive import keep_alive
keep_alive()

import os
import asyncio
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands

# ---- 기본 봇 설정 ----
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---- 주간 참가 데이터 ----
events = {
    "토요일-3시": [],
    "토요일-8시": [],
    "일요일-3시": [],
    "일요일-8시": []
}
MAX_PLAYERS = 10

# 월요일 0시에 초기화
async def reset_weekly_data():
    while True:
        now = datetime.now()
        # 다음 월요일 0시 계산
        days_ahead = (7 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_ahead)
        reset_time = datetime.combine(next_monday.date(), datetime.min.time())
        wait_sec = max(1, int((reset_time - now).total_seconds()))
        await asyncio.sleep(wait_sec)
        for k in events.keys():
            events[k] = []
        print("✅ 주간 참가 데이터 초기화 완료")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"🤖 봇 로그인 완료: {bot.user}")
    # 초기화 태스크 시작(중복 방지)
    if not any(t.get_coro().__name__ == "reset_weekly_data" for t in asyncio.all_tasks() if not t.done()):
        bot.loop.create_task(reset_weekly_data())

# ---- 슬래시 명령어들 ----
@tree.command(name="참가신청", description="성CK 참가 신청")
async def register(interaction: discord.Interaction, 요일: str, 시간: str):
    key = f"{요일}-{시간}"
    if key not in events:
        await interaction.response.send_message("❌ 잘못된 입력입니다. (요일: 토/일, 시간: 3시/8시)", ephemeral=True)
        return
    user = interaction.user.name
    if user in events[key]:
        await interaction.response.send_message("⚠️ 이미 신청하셨습니다.", ephemeral=True)
        return
    if len(events[key]) >= MAX_PLAYERS:
        await interaction.response.send_message("❌ 자리가 가득 찼습니다.", ephemeral=True)
        return
    events[key].append(user)
    await interaction.response.send_message(f"✅ {key} 참가 신청 완료!")

@tree.command(name="등록현황", description="현재 참가 현황 보기")
async def status(interaction: discord.Interaction):
    msg = "📋 현재 참가 현황:\n"
    for k, v in events.items():
        msg += f"- {k}: {len(v)}/{MAX_PLAYERS} → {', '.join(v) if v else '없음'}\n"
    await interaction.response.send_message(msg)

@tree.command(name="취소", description="참가 신청 취소")
async def cancel(interaction: discord.Interaction, 요일: str, 시간: str):
    key = f"{요일}-{시간}"
    user = interaction.user.name
    if key in events and user in events[key]:
        events[key].remove(user)
        await interaction.response.send_message(f"❎ {key} 참가가 취소되었습니다.")
    else:
        await interaction.response.send_message("⚠️ 해당 시간에 신청 내역이 없습니다.", ephemeral=True)

@tree.command(name="남은자리", description="빈 자리 확인")
async def spots(interaction: discord.Interaction):
    msg = "🎯 남은 자리 현황:\n"
    for k, v in events.items():
        left = MAX_PLAYERS - len(v)
        msg += f"- {k}: {left}자리 남음\n"
    await interaction.response.send_message(msg)

# ---- 실행 ----
bot.run(os.getenv("DISCORD_TOKEN"))
