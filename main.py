from interactions import Client
from os import name as OSname

slash = "\\" if OSname == "nt" else "/"

bot = Client()

bot.load("exts.card", None, slash,)
bot.load("exts.util", None,)

with open("token.txt", "r",) as f:
    bot.start(f.readlines()[0].rstrip("\n",),)