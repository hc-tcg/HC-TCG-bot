from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp.web import Application, AppRunner, TCPSite
from interactions import Client, listen

from datagen import dataGetter

class Bot(Client):
    @listen()
    async def on_ready(event):
        await runner.setup()
        site = TCPSite(runner, "127.0.0.1", 80)
        await site.start()
    
    @listen()
    async def on_disconnect(event):
        await runner.cleanup()

bot = Bot()

API_URL = "https://hc-tcg.fly.dev/api"
DOTD_PATH = "dotd.json"
WIN_DATA = "games.json"
COUNT_DATA = "count.json"

with open("token.txt", "r",) as f:
    lines = f.readlines()
    botToken = lines[0].rstrip("\n").split(" //")[0]
    gitToken = lines[1].rstrip("\n").split(" //")[0]
    tcgToken = lines[2].rstrip("\n").split(" //")[0]

dataGen = dataGetter(gitToken)
scheduler = AsyncIOScheduler()

webServer = Application()
runner = AppRunner(webServer)

bot.load_extension("exts.card", None, dataGenerator=dataGen)
bot.load_extension("exts.util", None)
bot.load_extension("exts.admin", None,
                   dataGenerator=dataGen,
                   key=tcgToken,
                   url=API_URL,
                   scheduler=scheduler,
                   server=webServer,
                   dataFile=WIN_DATA,
                   countFile=COUNT_DATA,
                  )
bot.load_extension("exts.dotd", None, fp=DOTD_PATH)

print("Bot running!")

scheduler.start()
bot.start(botToken)