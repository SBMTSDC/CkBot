# ---------- Render(Web Service, Free)용 더미 웹서버 ----------
from keep_alive import keep_alive
keep_alive()  # 포트를 열어 두어야 Render 무료 플랜에서 유지됩니다.

# ---------- 기본 import ----------
import os
import asyncio
from datetime import datetime, timedelta
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

# ---------- 봇 설정 ----------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- 주간 참가 데이터 ----------
events = {
    "토요일-3시": [],
    "토요일-8시": [],
    "일요일-3시": [],
    "일요일-8시": []
}
MAX_PLAYERS = 10

# ---------- 유틸 ----------
def user_display_name(interaction: discord.Interaction) -> str:
    """서버 닉네임 -> 글로벌 이름 -> 계정명 순으로 표시 이름 결정"""
    u = interaction.user
    return getattr(u, "display_name", None) or getattr(u, "global_name", None) or u.name

def progress_bar(current: int, total: int, width: int = 10) -> str:
    """▰▱ 진행바(고정 폭)"""
    current = max(0, min(current, total))
    on = "▰" * current
    off = "▱" * (width - current)
    return on + off

def slot_line(names: list[str]) -> str:
    """이름 목록을 1줄 요약(길면 생략)"""
    if not names:
        return "없음"
    text = ", ".join(names)
    return text if len(text) <= 70 else text[:67] + "…"

# ---------- 월요일 0시에 초기화 ----------
async def reset_weekly_data():
    while True:
        now = datetime.now()
        # 다음 월요일 0시 계산 (월=0 … 일=6)
        days_ahead = (7 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_ahead)
        reset_time = datetime.combine(next_monday.date(), datetime.min.time())
        if reset_time <= now:
            reset_time += timedelta(days=7)
        wait_sec = max(1, int((reset_time - now).total_seconds()))
        await asyncio.sleep(wait_sec)
        for k in events.keys():
            events[k] = []
        print("✅ 주간 참가 데이터 초기화 완료")

# ---------- 봇 준비 ----------
@bot.event
async def on_ready():
    print(f"🤖 봇 로그인 완료: {bot.user}")
    # 길드별 강제 동기화(캐시 무시하고 즉시 반영)
    for guild in bot.guilds:
        try:
            await tree.sync(guild=guild)
        except Exception as e:
            print("sync error:", guild.name, e)
    # 주간 리셋 태스크 시작(중복 방지)
    if not any(t.get_coro().__name__ == "reset_weekly_data" for t in asyncio.all_tasks() if not t.done()):
        bot.loop.create_task(reset_weekly_data())

# ---------- 슬래시 명령어들 ----------
# 참가신청: 요일/시간 드롭다운(고정 선택지)
@tree.command(name="참가신청", description="성CK 참가 신청")
@app_commands.describe(요일="토요일/일요일", 시간="3시/8시")
async def register(
    interaction: discord.Interaction,
    요일: Literal["토요일", "일요일"],
    시간: Literal["3시", "8시"],
):
    key = f"{요일}-{시간}"
    if key not in events:
        await interaction.response.send_message("❌ 잘못된 입력입니다. (요일: 토/일, 시간: 3시/8시)", ephemeral=True)
        return
    user = user_display_name(interaction)
    if user in events[key]:
        await interaction.response.send_message("⚠️ 이미 신청하셨습니다.", ephemeral=True)
        return
    if len(events[key]) >= MAX_PLAYERS:
        await interaction.response.send_message("❌ 자리가 가득 찼습니다.", ephemeral=True)
        return
    events[key].append(user)
    await interaction.response.send_message(f"✅ {key} 참가 신청 완료!")

# 등록현황(임베드 + 진행바)
@tree.command(name="등록현황", description="현재 참가 현황 보기")
async def status(interaction: discord.Interaction):
    emb = discord.Embed(
        title="📋 성CK 등록 현황",
        color=discord.Color.blurple()
    )
    order = ["토요일-3시", "토요일-8시", "일요일-3시", "일요일-8시"]
    for key in order:
        names = events[key]
        cnt = len(names)
        bar = progress_bar(cnt, MAX_PLAYERS, width=10)
        value = f"{bar}  **{cnt}/{MAX_PLAYERS}**\n{slot_line(names)}"
        emb.add_field(name=key, value=value, inline=False)
    emb.set_footer(text="매주 월요일 0시에 자동 초기화")
    await interaction.response.send_message(embed=emb)

# 취소: 요일/시간 드롭다운
@tree.command(name="취소", description="참가 신청 취소")
@app_commands.describe(요일="토요일/일요일", 시간="3시/8시")
async def cancel(
    interaction: discord.Interaction,
    요일: Literal["토요일", "일요일"],
    시간: Literal["3시", "8시"],
):
    key = f"{요일}-{시간}"
    user = user_display_name(interaction)
    if key in events and user in events[key]:
        events[key].remove(user)
        await interaction.response.send_message(f"❎ {key} 참가가 취소되었습니다.")
    else:
        await interaction.response.send_message("⚠️ 해당 시간에 신청 내역이 없습니다.", ephemeral=True)

# 남은자리(빈 슬롯만 깔끔히)
@tree.command(name="남은자리", description="빈 자리 확인")
async def spots(interaction: discord.Interaction):
    emb = discord.Embed(title="🎯 남은 자리", color=discord.Color.green())
    any_open = False
    order = ["토요일-3시", "토요일-8시", "일요일-3시", "일요일-8시"]
    for key in order:
        left = MAX_PLAYERS - len(events[key])
        if left > 0:
            any_open = True
            emb.add_field(name=key, value=f"남은 자리: **{left}** / {MAX_PLAYERS}", inline=False)
    if not any_open:
        emb.description = "모든 슬롯이 가득 찼습니다."
    await interaction.response.send_message(embed=emb)

# ---------- 실행 ----------
bot.run(os.getenv("DISCORD_TOKEN"))
