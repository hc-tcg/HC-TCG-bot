from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp.web import Application, AppRunner, TCPSite
from interactions import Client, listen
from json import load

from util import dataGetter

with open("config.json", "r") as f:
    CONFIG = load(f)


class Bot(Client):
    @listen()
    async def on_ready(event):
        await runner.setup()
        site = TCPSite(runner, "0.0.0.0", 8194)
        await site.start()
        scheduler.start()

    @listen()
    async def on_disconnect(event):
        await runner.cleanup()
        scheduler.shutdown()


bot = Bot()

dataGen = dataGetter(CONFIG["tokens"]["github"])
scheduler = AsyncIOScheduler()

webServer = Application()
runner = AppRunner(webServer)

bot.load_extension("exts.card", None, dataGenerator=dataGen)
bot.load_extension("exts.util", None)
bot.load_extension(
    "exts.admin",
    None,
    dataGenerator=dataGen,
    servers=CONFIG["server_data"],
    scheduler=scheduler,
    server=webServer,
    dataFile=CONFIG["win_fp"],
)
bot.load_extension("exts.dotd_weekly", None, fp=CONFIG["dotd_fp"])
bot.load_extension("exts.dotd", None, authed=CONFIG["dotd_permissions"])
bot.load_extension(
    "exts.forums", None, forumData=CONFIG["forum_data"], fp=CONFIG["forum_fp"]
)

print("Bot running!")

bot.start(CONFIG["tokens"]["discord"])
