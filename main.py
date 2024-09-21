"""Run the bot."""

from importlib import import_module
from json import load
from os import listdir
from pickle import UnpicklingError
from pickle import load as pklload
from time import time

from aiohttp.web import Application, AppRunner, TCPSite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import Client, Intents, listen
from interactions.api.events import MessageCreate

from util import DataGenerator, ServerManager

start = time()
with open("config.json") as f:
    CONFIG = load(f)


class Bot(Client):
    """Slightly modified discord client."""

    on_message_create_callback = None

    @listen()
    async def on_ready(self: "Bot") -> None:
        """Handle bot starting."""
        await bot.change_presence()
        await runner.setup()
        site = TCPSite(runner, "0.0.0.0", 8085)  # noqa: S104
        await site.start()
        scheduler.start()

        await server_manager.update_announcements()

        print(f"Bot started in {round(time()-start, 2)}s")

    @listen()
    async def on_disconnect(self: "Bot") -> None:
        """Handle bot disconnection."""
        await runner.cleanup()
        scheduler.shutdown()

    @listen()
    async def on_message_create(self: "Bot", message: MessageCreate) -> None:
        """Run message callback on new message."""
        if self.on_message_create_callback:
            await self.on_message_create_callback(message.message)


intents = Intents.DEFAULT
intents |= Intents.MESSAGE_CONTENT
intents |= Intents.MESSAGES

bot = Bot(intents=intents)

data_gen = DataGenerator(CONFIG["tokens"]["github"])

try:
    with open("universe.pkl", "rb") as f:
        data_gen.universe = pklload(f)  # noqa: S301
except (FileNotFoundError, UnpicklingError):
    print("Static universe not found, loading dynamic universe.")
    data_gen.reload_all()

scheduler = AsyncIOScheduler()

web_server = Application()
runner = AppRunner(web_server)

servers = []
for file in listdir("servers"):
    servers.append(import_module(f"servers.{file}").server)
server_manager = ServerManager(bot, servers, web_server, scheduler, data_gen.universe)

bot.load_extension("exts.admin", None, manager=server_manager)
bot.load_extension("exts.card", None, universe=data_gen.universe)
bot.load_extension("exts.dotd", None, manager=server_manager)
bot.load_extension("exts.forums", None, manager=server_manager)
bot.load_extension("exts.match", None, manager=server_manager)
bot.load_extension("exts.util", None, manager=server_manager)

bot.start(CONFIG["tokens"]["discord"])
