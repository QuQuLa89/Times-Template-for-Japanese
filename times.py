import discord
from discord.ext import commands
import json
import os

from dotenv import load_dotenv

# --------------------------------------------------
# 設定項目
# --------------------------------------------------
SETTINGS_FILE = "settings.json"

def load_settings(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def save_settings(path, active_id, archive_id):
    data = {
        "active_category_id": active_id,
        "archive_category_id": archive_id,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not TOKEN:
    print("DISCORD_BOT_TOKEN が設定されていません。.env.example をコピーして .env を作成してください")
    raise SystemExit(1)
ACTIVE_CATEGORY_ID = None  # !setup active <category_id> で設定
ARCHIVE_CATEGORY_ID = None  # !setup archive <category_id> で設定

_settings = load_settings(SETTINGS_FILE)
if isinstance(_settings.get("active_category_id"), int):
    ACTIVE_CATEGORY_ID = _settings["active_category_id"]
if isinstance(_settings.get("archive_category_id"), int):
    ARCHIVE_CATEGORY_ID = _settings["archive_category_id"]

async def sort_times_channels_in_category(category):
    channels = [ch for ch in category.text_channels if ch.name.startswith("times-")]
    if len(channels) < 2:
        return
    channels_sorted = sorted(channels, key=lambda c: c.name)
    positions = sorted(ch.position for ch in channels)
    try:
        for ch, pos in zip(channels_sorted, positions):
            if ch.position != pos:
                await ch.edit(position=pos)
    except Exception as e:
        print(f"チャンネル並び替えエラー: {e}")
# --------------------------------------------------

# Botの権限設定 (Intents)
intents = discord.Intents.default()
intents.members = True          # メンバーの入退室を検知するために必要
intents.message_content = True  # メッセージ内容を読み取るために必要

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')

# --------------------------------------------------
# セットアップコマンド
# --------------------------------------------------
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx, mode: str, category_id: int):
    global ACTIVE_CATEGORY_ID, ARCHIVE_CATEGORY_ID
    mode = mode.lower()

    category = ctx.guild.get_channel(category_id) if ctx.guild else None
    if not isinstance(category, discord.CategoryChannel):
        await ctx.send("カテゴリIDが無効です。カテゴリチャンネルのIDを指定してください。")
        return

    if mode == "active":
        ACTIVE_CATEGORY_ID = category_id
        save_settings(SETTINGS_FILE, ACTIVE_CATEGORY_ID, ARCHIVE_CATEGORY_ID)
        await ctx.send(f"ACTIVE_CATEGORY_ID を設定しました: {category.name} ({category_id})")
        return

    if mode == "archive":
        ARCHIVE_CATEGORY_ID = category_id
        save_settings(SETTINGS_FILE, ACTIVE_CATEGORY_ID, ARCHIVE_CATEGORY_ID)
        await ctx.send(f"ARCHIVE_CATEGORY_ID を設定しました: {category.name} ({category_id})")
        return

    await ctx.send("使い方: !setup active <category_id> または !setup archive <category_id>")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドは管理者権限が必要です。")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("使い方: !setup active <category_id> または !setup archive <category_id>")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("カテゴリIDは整数で指定してください。")
    else:
        raise error

# --------------------------------------------------
# ユーザー入室時の処理
# --------------------------------------------------
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    # チャンネル名に使用できるよう名前を正規化（小文字化、スペースをハイフンに置換など）
    # Discordのチャンネル名は小文字英数字とハイフンのみ等の制限があるため
    sanitized_name = member.name.lower().replace(" ", "-").replace("#", "").replace(".", "")
    channel_name = f"times-{sanitized_name}"

    if ACTIVE_CATEGORY_ID is None:
        print("エラー: ACTIVE_CATEGORY_ID が設定されていません。!setup active で設定してください。")
        return

    # 指定されたカテゴリーを取得
    category = guild.get_channel(ACTIVE_CATEGORY_ID)

    if category is None:
        print(f"エラー: カテゴリーID {ACTIVE_CATEGORY_ID} が見つかりません。")
        return

    # 既に同名のチャンネルがあるか確認（重複作成を防ぐ場合）
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    
    if existing_channel:
        # 既に存在する場合の処理（アーカイブから戻す or 通知のみ）
        if ARCHIVE_CATEGORY_ID is None:
            print("エラー: ARCHIVE_CATEGORY_ID が設定されていません。!setup archive で設定してください。")
            await existing_channel.send(f"{member.mention} おかえりなさい！既存のtimesチャンネルが見つかりました。")
            return

        archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)
        if archive_category and existing_channel.category and existing_channel.category.id == ARCHIVE_CATEGORY_ID:
            await existing_channel.edit(category=category)
            await existing_channel.send(f"{member.mention} おかえりなさい！チャンネルをアーカイブから戻しました。")
            await sort_times_channels_in_category(category)
        else:
            await existing_channel.send(f"{member.mention} おかえりなさい！既存のtimesチャンネルが見つかりました。")
    else:
        # チャンネルを作成
        try:
            new_channel = await guild.create_text_channel(name=channel_name, category=category)
            
            # 作成したチャンネルにメッセージを送信
            await new_channel.send(f"{member.mention} ここが貴方のtimesです。Xのように自由に呟いていってね！")
            print(f"チャンネル作成: {channel_name}")
            await sort_times_channels_in_category(category)
            
        except Exception as e:
            print(f"チャンネル作成エラー: {e}")

# --------------------------------------------------
# ユーザー退室時の処理
# --------------------------------------------------
@bot.event
async def on_member_remove(member):
    guild = member.guild
    
    # 検索対象のチャンネル名を定義
    sanitized_name = member.name.lower().replace(" ", "-").replace("#", "").replace(".", "")
    target_channel_name = f"times-{sanitized_name}"

    # チャンネルを検索
    target_channel = discord.utils.get(guild.text_channels, name=target_channel_name)
    
    if ARCHIVE_CATEGORY_ID is None:
        print("エラー: ARCHIVE_CATEGORY_ID が設定されていません。!setup archive で設定してください。")
        return

    # アーカイブ先のカテゴリーを取得
    archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)

    if archive_category is None:
        print(f"エラー: アーカイブ用カテゴリーID {ARCHIVE_CATEGORY_ID} が見つかりません。")
        return

    if target_channel:
        try:
            # チャンネルをアーカイブカテゴリに移動
            await target_channel.edit(category=archive_category)
            await target_channel.send("ユーザーが退室したため、このチャンネルをアーカイブしました。")
            print(f"チャンネル移動: {target_channel_name} -> アーカイブ")
        except Exception as e:
            print(f"チャンネル移動エラー: {e}")
    else:
        print(f"チャンネルが見つかりませんでした: {target_channel_name}")

# Botの実行
bot.run(TOKEN)
