"""Run the bot."""

from importlib import import_module
from os import listdir, path
from time import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import Client, Intents, listen

from bot.config import CONFIG
from bot.util import ServerManager

start = time()


class Bot(Client):
    """Slightly modified discord client."""

    @listen()
    async def on_ready(self: "Bot") -> None:
        """Handle bot starting."""
        await server_manager.reload_all_generators()

        await bot.change_presence()
        scheduler.start()

        print(f"Bot started in {round(time()-start, 2)}s")

    @listen()
    async def on_disconnect(self: "Bot") -> None:
        """Handle bot disconnection."""
        await server_manager.close_all_sessions()
        scheduler.shutdown()


intents = Intents.DEFAULT
intents |= Intents.MESSAGE_CONTENT
intents |= Intents.MESSAGES

bot = Bot(intents=intents)

scheduler = AsyncIOScheduler()

servers = []
for file in listdir("servers"):
    if not path.isfile(f"servers/{file}"):
        continue
    servers.append(import_module(f"servers.{file.removesuffix(".py")}").server)

server_manager = ServerManager(bot, servers)

ext_args = {"manager": server_manager, "scheduler": scheduler}

bot.load_extensions("bot\\exts", **ext_args)

bot.start(CONFIG.SECRET)
