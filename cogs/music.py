import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import random
from core.classes import Cog_Extension


class Music(Cog_Extension):
    @app_commands.command()
    async def join(): ...

    @app_commands.command()
    async def play(): ...

    @app_commands.command()
    async def pause(): ...

    @app_commands.command()
    async def skip(): ...

    @app_commands.command()
    async def nowplay(): ...

    @app_commands.command()
    async def list(): ...

    @app_commands.command()
    async def skipto(): ...

    @app_commands.command()
    async def shuffle(): ...

    @app_commands.command()
    async def repeat(): ...
