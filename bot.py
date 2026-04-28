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
    # スラッシュコマンドをDiscord側に同期
    await bot.tree.sync()

@bot.tree.command(name="add", description="単語を1つ追加します")
async def add_word(interaction: discord.Interaction, word: str):
    async with bot.db.acquire() as conn:
        # SQLインジェクション対策のため、$1を使って変数を渡します
        await conn.execute('INSERT INTO words (word) VALUES ($1)', word)
    await interaction.response.send_message(f"「{word}」を追加しました！")

@bot.tree.command(name="add_bulk", description="複数の単語を一括で追加します（スペースまたはカンマ区切り）")
async def add_bulk(interaction: discord.Interaction, words: str):
    # 全角・半角カンマをスペースに変換し、スペース区切りでリスト化（空文字は除外）
    word_list = [w for w in words.replace('、', ' ').replace(',', ' ').split() if w]
    
    if not word_list:
        await interaction.response.send_message("追加する単語が正しく認識できませんでした。")
        return

    # asyncpgの executemany で使うために [(単語1,), (単語2,), ...] のタプル形式に変換
    values = [(w,) for w in word_list]

    async with bot.db.acquire() as conn:
        # 複数のデータを一括でINSERTする
        await conn.executemany('INSERT INTO words (word) VALUES ($1)', values)
    
    added_words_str = ", ".join(word_list)
    await interaction.response.send_message(f"**{len(word_list)}個** の単語を一括追加しました！\n追加した単語: {added_words_str}")

@bot.tree.command(name="list", description="追加したすべての単語を番号付きで表示します")
async def list_words(interaction: discord.Interaction):
    async with bot.db.acquire() as conn:
        # id（番号）とword（単語）を取得し、id順に並べる
        rows = await conn.fetch('SELECT id, word FROM words ORDER BY id')
    
    if not rows:
        await interaction.response.send_message("まだ単語は追加されていません。")
        return
        
    # rowsから取り出して「1. 単語」のような番号付きリストにする
    words_list = "\n".join([f"{row['id']}. {row['word']}" for row in rows])
    await interaction.response.send_message(f"**【追加された偏見単語リスト】**\n{words_list}")

@bot.tree.command(name="delete", description="リストの番号を指定して単語を削除します")
async def delete_word(interaction: discord.Interaction, number: int):
    async with bot.db.acquire() as conn:
        # RETURNING word を使うことで、削除された単語の名前を取得できる
        deleted_word = await conn.fetchval('DELETE FROM words WHERE id = $1 RETURNING word', number)
        
    if deleted_word:
        await interaction.response.send_message(f"番号 **{number}** の「{deleted_word}」を削除しました！")
    else:
        await interaction.response.send_message(f"番号 **{number}** の単語は見つかりませんでした。`/list` で番号を確認してください。")

# 環境変数からトークンを読み込んで起動
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)