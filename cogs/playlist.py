import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from core.classes import Cog_Extension
import sqlite3

DATABASE_PATH = "music_bot.db"

# class DatabaseManager:


class Playlist(Cog_Extension):
    def __init__(self, bot, db_path=DATABASE_PATH):
        self.bot = bot
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化 SQLite3 資料表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            owner_id TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS songs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            playlist_id INTEGER NOT NULL,
                            title TEXT NOT NULL,
                            url TEXT NOT NULL,
                            FOREIGN KEY (playlist_id) REFERENCES playlists(id))''')
        conn.commit()
        conn.close()

    def add_playlist(self, name, owner_id):
        """新增歌單"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO playlists (name, owner_id) VALUES (?, ?)", (name, owner_id))
        conn.commit()
        conn.close()

    def add_song(self, playlist_name, title, url):
        """新增歌曲到指定歌單"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        playlist = cursor.fetchone()
        if playlist:
            cursor.execute(
                "INSERT INTO songs (playlist_id, title, url) VALUES (?, ?, ?)", (playlist[0], title, url))
            conn.commit()
        conn.close()

    def get_songs(self, playlist_name):
        """獲取歌單內的歌曲"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT songs.title, songs.url FROM songs JOIN playlists ON songs.playlist_id = playlists.id WHERE playlists.name = ?", (playlist_name,))
        songs = cursor.fetchall()
        conn.close()
        return songs

    def delete_song_by_url(self, playlist_name, url):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 先查出 playlist 的 ID
        cursor.execute(
            "SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        result = cursor.fetchone()

        if result:
            playlist_id = result[0]

            # 刪除歌曲
            cursor.execute(
                "DELETE FROM songs WHERE playlist_id = ? AND url = ?",
                (playlist_id, url)
            )
            conn.commit()

            # 檢查這個歌單是否還有歌
            cursor.execute(
                "SELECT COUNT(*) FROM songs WHERE playlist_id = ?", (playlist_id,))
            song_count = cursor.fetchone()[0]

            if song_count == 0:
                # 如果歌單沒歌了，就刪除歌單
                cursor.execute(
                    "DELETE FROM playlists WHERE id = ?", (playlist_id,))
                print(f"🗑 已刪除空的歌單 `{playlist_name}`")

            conn.commit()

        conn.close()


# database = Playlist()  # 讓 `bot.py` 可以直接 import 使用


async def setup(bot):
    await bot.add_cog(Playlist(bot))
