import discord
from discord.ext import commands
import asyncpg
import os

# Botの設定
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 環境変数からNeonの接続URLを取得
DATABASE_URL = os.environ.get("DATABASE_URL")

@bot.event
async def on_ready():
    # Neon(PostgreSQL)への接続プールを作成
    bot.db = await asyncpg.create_pool(DATABASE_URL)
    
    # データベースのテーブルを初期化
    async with bot.db.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                word TEXT NOT NULL
            )
        ''')
        
    print(f"{bot.user} としてログインしました！")
    await bot.tree.sync()

@bot.tree.command(name="add", description="単語を追加します")
async def add_word(interaction: discord.Interaction, word: str):
    async with bot.db.acquire() as conn:
        # SQLインジェクション対策のため、$1を使って変数を渡します
        await conn.execute('INSERT INTO words (word) VALUES ($1)', word)
    await interaction.response.send_message(f"「{word}」を追加しました！")

@bot.tree.command(name="list", description="追加したすべての単語を表示します")
async def list_words(interaction: discord.Interaction):
    async with bot.db.acquire() as conn:
        rows = await conn.fetch('SELECT word FROM words')
    
    if not rows:
        await interaction.response.send_message("まだ単語は追加されていません。")
        return
        
    # rowsから単語を取り出して箇条書きにする
    words_list = "\n".join([f"・{row['word']}" for row in rows])
    await interaction.response.send_message(f"**【追加された偏見単語リスト】**\n{words_list}")

# 環境変数からトークンを読み込んで起動
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)