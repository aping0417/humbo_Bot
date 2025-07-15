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
        """獲取伺服器對應歌單內的歌曲"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT songs.title, songs.url FROM songs
            JOIN playlists ON songs.playlist_id = playlists.id
            WHERE playlists.guild_id = ?
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


async def setup(bot):
    await bot.add_cog(Playlist(bot))
