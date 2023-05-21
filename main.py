from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import Client

from datagen import dataGetter

bot = Client()

API_URL = "https://hc-tcg-beta.fly.dev/api"
DOTD_PATH = "dotd.json"

with open("token.txt", "r",) as f:
    lines = f.readlines()
    botToken = lines[0].rstrip("\n").split(" //")[0]
    gitToken = lines[1].rstrip("\n").split(" //")[0]
    tcgToken = lines[2].rstrip("\n").split(" //")[0]

dataGen = dataGetter(gitToken)
scheduler = AsyncIOScheduler()

@bot.event()
async def on_ready():
    scheduler.start()

bot.load_extension("exts.card", None, dataGenerator=dataGen)
bot.load_extension("exts.util", None)
bot.load_extension("exts.admin", None, dataGenerator=dataGen, key=tcgToken, url=API_URL, scheduler=scheduler)
bot.load_extension("exts.dotd", None, fp=DOTD_PATH)

print("Bot running!")

bot.start(botToken)