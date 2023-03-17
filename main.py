from interactions import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from os import name as OSname

slash = "\\" if OSname == "nt" else "/"

bot = Client()
scheduler = AsyncIOScheduler()

bot.load("exts.card", None, slash,)
bot.load("exts.tournament", None, scheduler,)
bot.load("exts.util", None,)

scheduler.start()

with open("token.txt", "r",) as f:
    bot.start(f.readlines()[0].rstrip("\n",),)