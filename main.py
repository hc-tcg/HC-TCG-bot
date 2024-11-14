"""Run the bot."""

from importlib import import_module
from json import load
from os import listdir
from pickle import UnpicklingError
from pickle import load as pklload
from time import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import Client, Intents, listen
from interactions.api.events import MessageCreate

from util import DataGenerator, ServerManager

start = time()
with open("config.json") as f:
    CONFIG = load(f)


class Bot(Client):
    """Slightly modified discord client."""

    @listen()
    async def on_ready(self: "Bot") -> None:
        """Handle bot starting."""
        await bot.change_presence()
        scheduler.start()

        print(f"Bot started in {round(time()-start, 2)}s")

    @listen()
    async def on_disconnect(self: "Bot") -> None:
        """Handle bot disconnection."""
        scheduler.shutdown()


intents = Intents.DEFAULT
intents |= Intents.MESSAGE_CONTENT
intents |= Intents.MESSAGES

bot = Bot(intents=intents)

data_gen = DataGenerator("https://hc-tcg.online")
data_gen.reload_all()

scheduler = AsyncIOScheduler()

servers = []
for file in listdir("servers"):
    servers.append(import_module(f"servers.{file}").server)
server_manager = ServerManager(bot, servers)

ext_args = {
    "manager": server_manager,
    "scheduler": scheduler,
    "data_generator": data_gen,
}

bot.load_extension("exts.card", None, **ext_args)
bot.load_extension("exts.dotd", None, **ext_args)
bot.load_extension("exts.forums", None, **ext_args)
bot.load_extension("exts.game", None, **ext_args)
bot.load_extension("exts.util", None, **ext_args)

bot.start(CONFIG["tokens"]["discord"])
