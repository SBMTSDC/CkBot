# ---------- Render(Web Service, Free)용 더미 웹서버 ----------
from keep_alive import keep_alive
keep_alive()

# ---------- 기본 import ----------
import os
import json
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

# ---------- 참가 데이터 파일 저장 기능 ----------
DATA_FILE = "registrations.json"

default_keys = ["토요일-3시", "토요일-8시", "일요일-3시", "일요일-8시"]

# 고정 + 임의 데이터 구조
events = {k: [] for k in default_keys}
custom_events = []

def load_events():
    global events, custom_events
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            events = data.get("고정", {k: [] for k in default_keys})
            custom_events = data.get("임의", [])
    except (FileNotFoundError, json.JSONDecodeError):
        events = {k: [] for k in default_keys}
        custom_events = []

def save_events():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "고정": events,
            "임의": custom_events
        }, f, ensure_ascii=False, indent=2)

# ---------- 초기 로드 ----------
load_events()

# ---------- 유틸 ----------
def user_display_name(interaction: discord.Interaction) -> str:
    u = interaction.user
    return getattr(u, "display_name", None) or getattr(u, "global_name", None) or u.name

def slot_line(names: list[str]) -> str:
    if not names:
        return "없음"
    text = ", ".join(names)
    return text if len(text) <= 70 else text[:67] + "…"

# ---------- 월요일 0시에 초기화 ----------
async def reset_weekly_data():
    while True:
        now = datetime.now()
        days_ahead = (7 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_ahead)
        reset_time = datetime.combine(next_monday.date(), datetime.min.time())
        if reset_time <= now:
            reset_time += timedelta(days=7)
        wait_sec = max(1, int((reset_time - now).total_seconds()))
        await asyncio.sleep(wait_sec)

        for k in events.keys():
            events[k] = []
        custom_events.clear()
        save_events()
        print("✅ 주간 참가 데이터 초기화 완료")

# ---------- 봇 준비 ----------
@bot.event
async def on_ready():
    print(f"🤖 봇 로그인 완료: {bot.user}")

    try:
        synced = await tree.sync()
        print(f"synced global commands: {len(synced)}")
    except Exception as e:
        print("global sync error:", e)

    for guild in bot.guilds:
        try:
            gsynced = await tree.sync(guild=guild)
            print(f"synced to guild {guild.name}: {len(gsynced)}")
        except Exception as e:
            print("sync error:", guild.name, e)

    if not any(t.get_coro().__name__ == "reset_weekly_data"
               for t in asyncio.all_tasks()
               if not t.done()):
        bot.loop.create_task(reset_weekly_data())

@bot.event
async def on_disconnect():
    print("⚠️  게이트웨이 연결 끊김")

@bot.event
async def on_resumed():
    print("🔄  게이트웨이 세션 재개")

# ---------- 슬래시 명령어 ----------
@tree.command(name="참가신청", description="성CK 참가 신청")
@app_commands.describe(요일="토요일/일요일", 시간="3시/8시")
async def register(
    interaction: discord.Interaction,
    요일: Literal["토요일", "일요일"],
    시간: Literal["3시", "8시"],
):
    key = f"{요일}-{시간}"
    if key not in events:
        await interaction.response.send_message("❌ 잘못된 입력입니다.", ephemeral=True)
        return
    user = user_display_name(interaction)
    if user in events[key]:
        await interaction.response.send_message("⚠️ 이미 신청하셨습니다.", ephemeral=True)
        return
    events[key].append(user)
    save_events()
    await interaction.response.send_message(f"✅ {key} 참가 신청 완료!")

@tree.command(name="임의신청", description="고정시간 외 원하는 시간에 신청")
@app_commands.describe(
    날짜="예: 9월 14일",
    시간="예: 오후 6시",
    비고="선택 사항 (예: 고정시간 불가 등)"
)
async def custom_register(
    interaction: discord.Interaction,
    날짜: str,
    시간: str,
    비고: str = ""
):
    user = user_display_name(interaction)
    for e in custom_events:
        if e["user"] == user and e["날짜"] == 날짜 and e["시간"] == 시간:
            await interaction.response.send_message("⚠️ 이미 해당 시간에 임의 신청하셨습니다.", ephemeral=True)
            return
    custom_events.append({
        "user": user,
        "날짜": 날짜,
        "시간": 시간,
        "비고": 비고
    })
    save_events()
    await interaction.response.send_message(f"🆗 요청 완료! 제안한 시간: {날짜} {시간}")

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
        value = f"**{cnt}명 신청**\n{slot_line(names)}"
        emb.add_field(name=key, value=value, inline=False)

    # 임의 신청자 보여주기
    if custom_events:
        lines = [
            f"{e['날짜']} {e['시간']} - {e['user']}" + (f" ({e['비고']})" if e["비고"] else "")
            for e in custom_events
        ]
        emb.add_field(name="🆕 임의 시간 신청자", value="\n".join(lines), inline=False)

    emb.set_footer(text="매주 월요일 0시에 자동 초기화됩니다.")
    await interaction.response.send_message(embed=emb)

@tree.command(name="취소", description="고정 시간 참가 신청 취소")
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
        save_events()
        await interaction.response.send_message(f"❎ {key} 참가가 취소되었습니다.")
    else:
        await interaction.response.send_message("⚠️ 해당 시간에 신청 내역이 없습니다.", ephemeral=True)

# ---------- 실행 ----------
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    bot.run(token)
