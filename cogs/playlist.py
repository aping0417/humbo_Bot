import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from core.classes import Cog_Extension
import sqlite3

DATABASE_PATH = "music_bot.db"


class Playlist(Cog_Extension):
    def __init__(self, bot, db_path=DATABASE_PATH):
        self.bot = bot
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化 SQLite3 資料表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS playlists (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            guild_id TEXT NOT NULL UNIQUE)"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS songs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            playlist_id INTEGER NOT NULL,
                            title TEXT NOT NULL,
                            url TEXT NOT NULL,
                            FOREIGN KEY (playlist_id) REFERENCES playlists(id))"""
        )
        conn.commit()
        conn.close()

    def ensure_playlist_exists(self, guild_id):
        """確保此 guild_id 對應的歌單存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        if result:
            playlist_id = result[0]
        else:
            cursor.execute("INSERT INTO playlists (guild_id) VALUES (?)", (guild_id,))
            conn.commit()
            playlist_id = cursor.lastrowid
        conn.close()
        return playlist_id

    def add_song(self, guild_id, title, url):
        """新增歌曲到伺服器專屬歌單"""
        playlist_id = self.ensure_playlist_exists(guild_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO songs (playlist_id, title, url) VALUES (?, ?, ?)",
            (playlist_id, title, url),
        )
        conn.commit()
        conn.close()

    def get_songs(self, guild_id):
        """獲取伺服器對應歌單內的歌曲（依加入順序）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT songs.title, songs.url FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            ORDER BY songs.id ASC
            """,
            (guild_id,),
        )
        songs = cursor.fetchall()
        conn.close()
        return songs

    def delete_song_by_url(self, guild_id, url):
        """根據 URL 刪除歌"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        if result:
            playlist_id = result[0]
            cursor.execute(
                "DELETE FROM songs WHERE playlist_id = ? AND url = ?",
                (playlist_id, url),
            )
            conn.commit()
            cursor.execute(
                "SELECT COUNT(*) FROM songs WHERE playlist_id = ?", (playlist_id,)
            )
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
                print(f"🗑 已刪除空的歌單 for guild `{guild_id}`")
                conn.commit()
        conn.close()

    def clear_playlist(self, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        if result:
            playlist_id = result[0]
            cursor.execute("DELETE FROM songs WHERE playlist_id = ?", (playlist_id,))
            conn.commit()
            print(f"🧹 已清空 `{guild_id}` 的歌單")
        conn.close()

    def pop_next_song(self, guild_id):
        """取出並刪除這個 guild 的歌單中第一首歌"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT songs.id, songs.title, songs.url FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            ORDER BY songs.id ASC LIMIT 1
            """,
            (guild_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        song_id, title, url = row

        # 刪除這首
        cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()

        # 如果清單已空，刪除 playlist
        cursor.execute(
            """
            SELECT COUNT(*) FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            """,
            (guild_id,),
        )
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute("DELETE FROM playlists WHERE guild_id = ?", (guild_id,))
            print(f"🗑 自動刪除空歌單：{guild_id}")
            conn.commit()

        conn.close()
        return title, url

    def pop_random_song(self, guild_id):
        """隨機取出並刪除這個 guild 的一首歌"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT songs.id, songs.title, songs.url FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            ORDER BY RANDOM() LIMIT 1
            """,
            (guild_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        song_id, title, url = row
        cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()

        # 若歌單空了就清掉 playlist
        cursor.execute(
            """
            SELECT COUNT(*) FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            """,
            (guild_id,),
        )
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute("DELETE FROM playlists WHERE guild_id = ?", (guild_id,))
            conn.commit()

        conn.close()
        return title, url

    def get_song_count(self, guild_id) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
            """,
            (guild_id,),
        )
        n = cursor.fetchone()[0]
        conn.close()
        return int(n)

    def remove_song_at(self, guild_id: str, index_1_based: int):
        """依序號刪除（1 起算）。成功回傳 (title, url)，否則回傳 None。"""
        if index_1_based <= 0:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM playlists WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        playlist_id = row[0]

        cursor.execute(
            """
            SELECT id, title, url
            FROM songs
            WHERE playlist_id = ?
            ORDER BY id ASC
            LIMIT 1 OFFSET ?
            """,
            (playlist_id, index_1_based - 1),
        )
        song = cursor.fetchone()
        if not song:
            conn.close()
            return None

        song_id, title, url = song
        cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM songs WHERE playlist_id = ?", (playlist_id,)
        )
        left = cursor.fetchone()[0]
        if left == 0:
            cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            conn.commit()

        conn.close()
        return (title, url)


async def setup(bot):
    await bot.add_cog(Playlist(bot))
