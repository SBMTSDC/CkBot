from keep_alive import keep_alive
keep_alive()

import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import os

# Get Discord token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN", "your_discord_token_here")

# Set up Discord intents (without privileged intents)
intents = discord.Intents.default()
intents.message_content = False  # Disable privileged intent

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Registration data structure - stores players for each time slot
registrations = {
    ("토요일", 15): [],  # Saturday 15:00
    ("토요일", 20): [],  # Saturday 20:00
    ("일요일", 15): [],  # Sunday 15:00
    ("일요일", 20): []   # Sunday 20:00
}

# Maximum number of players per time slot
MAX_PLAYERS = 10

# Status messages that rotate every 6 hours
STATUS_MESSAGES = [
    "9.6 성CK OPEN!",
    "내전1 은 그만. 성CK ON.",
    "뉴페이스 언제든 환영",
    "문의사항은 관리자에게"
]

@tasks.loop(hours=6)
async def update_status():
    """Update bot status every 6 hours"""
    try:
        # Get current hour to determine which status to show
        current_hour = datetime.datetime.now().hour
        # Choose status based on 6-hour intervals (0-6, 6-12, 12-18, 18-24)
        status_index = (current_hour // 6) % len(STATUS_MESSAGES)
        status_message = STATUS_MESSAGES[status_index]
        
        # Update bot status
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=status_message
            )
        )
        print(f"🔄 상태 메시지 업데이트: {status_message}")
        
    except Exception as e:
        print(f"❌ 상태 업데이트 오류: {e}")

@tasks.loop(hours=1)
async def reset_every_monday():
    """Reset all registrations every Monday at midnight (KST)"""
    now = datetime.datetime.now()
    # Check if it's Monday (weekday 0) at midnight hour (0)
    if now.weekday() == 0 and now.hour == 0:
        # Clear all registration lists
        for key in registrations:
            registrations[key].clear()
        print("🧹 참가자 명단 초기화 완료 (Registration lists cleared)")

@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    try:
        # Sync slash commands with Discord
        await tree.sync()
        # Start the weekly reset task
        reset_every_monday.start()
        # Start the status update task
        update_status.start()
        print(f"🤖 봇 로그인 완료: {bot.user.name}")
        print(f"📊 등록된 서버 수: {len(bot.guilds)}")
    except Exception as e:
        print(f"❌ 봇 초기화 오류: {e}")

@tree.command(name="참가신청", description="요일/시간을 선택하여 성CK 참가 신청")
@app_commands.describe(
    day="참가하고 싶은 요일을 선택하세요",
    hour="참가하고 싶은 시간을 선택하세요"
)
@app_commands.choices(
    day=[
        app_commands.Choice(name="토요일", value="토요일"),
        app_commands.Choice(name="일요일", value="일요일")
    ],
    hour=[
        app_commands.Choice(name="15시", value=15),
        app_commands.Choice(name="20시", value=20)
    ]
)
async def register(interaction: discord.Interaction, day: app_commands.Choice[str], hour: app_commands.Choice[int]):
    """Register for a game session"""
    try:
        key = (day.value, hour.value)
        user = interaction.user.display_name
        
        # Check if user is already registered for this time slot
        if user in registrations[key]:
            await interaction.response.send_message(
                f"⚠️ **이미 신청하셨습니다!**\n"
                f"📅 {day.value} {hour.value}시에 이미 등록되어 있습니다.",
                ephemeral=True
            )
            return
        
        # Check if the time slot is full
        if len(registrations[key]) >= MAX_PLAYERS:
            await interaction.response.send_message(
                f"❌ **마감되었습니다!**\n"
                f"📅 {day.value} {hour.value}시 세션이 가득 찼습니다. ({MAX_PLAYERS}/{MAX_PLAYERS})",
                ephemeral=True
            )
            return
        
        # Add user to registration list
        registrations[key].append(user)
        current_count = len(registrations[key])
        
        await interaction.response.send_message(
            f"✅ **참가 신청 완료!**\n"
            f"📅 {day.value} {hour.value}시\n"
            f"👥 현재 인원: {current_count}/{MAX_PLAYERS}\n"
            f"🎮 게임에서 만나요!",
            ephemeral=True
        )
        
        print(f"📝 신규 등록: {user} -> {day.value} {hour.value}시 ({current_count}/{MAX_PLAYERS})")
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ **오류가 발생했습니다**\n"
            f"잠시 후 다시 시도해 주세요.",
            ephemeral=True
        )
        print(f"❌ 참가신청 오류: {e}")

@tree.command(name="등록현황", description="모든 시간대 등록 현황을 확인합니다")
async def show_status(interaction: discord.Interaction):
    """Show registration status for all time slots"""
    try:
        msg = "**📋 성CK 등록 현황**\n\n"
        
        for (day, hour), players in registrations.items():
            player_count = len(players)
            
            if players:
                # Show registered players
                player_list = ", ".join(players)
                msg += f"**{day} {hour}시** ({player_count}/{MAX_PLAYERS})\n"
                msg += f"👥 {player_list}\n\n"
            else:
                # Show empty slot
                msg += f"**{day} {hour}시** (0/{MAX_PLAYERS})\n"
                msg += f"📭 등록된 참가자가 없습니다\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 `/참가신청` 명령어로 신청하세요!"
        
        await interaction.response.send_message(msg)
        
    except Exception as e:
        await interaction.response.send_message(
            "❌ **현황 조회 중 오류가 발생했습니다**\n"
            "잠시 후 다시 시도해 주세요.",
            ephemeral=True
        )
        print(f"❌ 등록현황 오류: {e}")

@tree.command(name="취소", description="신청한 참가를 취소합니다")
@app_commands.describe(
    day="취소할 요일을 선택하세요",
    hour="취소할 시간을 선택하세요"
)
@app_commands.choices(
    day=[
        app_commands.Choice(name="토요일", value="토요일"),
        app_commands.Choice(name="일요일", value="일요일")
    ],
    hour=[
        app_commands.Choice(name="15시", value=15),
        app_commands.Choice(name="20시", value=20)
    ]
)
async def cancel(interaction: discord.Interaction, day: app_commands.Choice[str], hour: app_commands.Choice[int]):
    """Cancel registration for a game session"""
    try:
        key = (day.value, hour.value)
        user = interaction.user.display_name
        
        # Check if user is registered for this time slot
        if user in registrations[key]:
            registrations[key].remove(user)
            remaining_count = len(registrations[key])
            
            await interaction.response.send_message(
                f"❎ **참가 취소 완료**\n"
                f"📅 {day.value} {hour.value}시\n"
                f"👥 현재 인원: {remaining_count}/{MAX_PLAYERS}",
                ephemeral=True
            )
            
            print(f"🗑️ 취소: {user} -> {day.value} {hour.value}시 ({remaining_count}/{MAX_PLAYERS})")
            
        else:
            await interaction.response.send_message(
                f"⚠️ **취소할 신청이 없습니다**\n"
                f"📅 {day.value} {hour.value}시에 등록된 이력이 없습니다.\n"
                f"💡 `/등록현황`으로 현재 상태를 확인해보세요.",
                ephemeral=True
            )
            
    except Exception as e:
        await interaction.response.send_message(
            "❌ **취소 처리 중 오류가 발생했습니다**\n"
            "잠시 후 다시 시도해 주세요.",
            ephemeral=True
        )
        print(f"❌ 취소 오류: {e}")

@tree.command(name="남은자리", description="각 시간대별 남은 자리를 확인합니다")
async def show_remaining(interaction: discord.Interaction):
    """Show remaining slots for all time slots"""
    try:
        msg = "**📊 남은 자리 현황**\n\n"
        
        for (day, hour), players in registrations.items():
            current_count = len(players)
            remaining = MAX_PLAYERS - current_count
            
            if remaining > 0:
                msg += f"**{day} {hour}시**\n"
                msg += f"🟢 {remaining}자리 남음 ({current_count}/{MAX_PLAYERS})\n\n"
            else:
                msg += f"**{day} {hour}시**\n"
                msg += f"🔴 마감됨 ({current_count}/{MAX_PLAYERS})\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 빈 자리가 있는 시간대에 `/참가신청`하세요!"
        
        await interaction.response.send_message(msg)
        
    except Exception as e:
        await interaction.response.send_message(
            "❌ **자리 현황 조회 중 오류가 발생했습니다**\n"
            "잠시 후 다시 시도해 주세요.",
            ephemeral=True
        )
        print(f"❌ 남은자리 오류: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    print(f"❌ 명령어 오류: {error}")

# Start the bot
if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_discord_token_here":
        print("❌ 오류: DISCORD_TOKEN 환경 변수를 설정해주세요!")
        print("💡 Discord Developer Portal에서 봇 토큰을 발급받아 환경 변수로 설정하세요.")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("❌ 로그인 실패: 유효하지 않은 토큰입니다.")
        except Exception as e:
            print(f"❌ 봇 실행 오류: {e}")
