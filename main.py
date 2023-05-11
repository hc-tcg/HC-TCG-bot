from interactions import Client

from datagen import dataGetter

bot = Client()

API_URL = "https://hc-tcg-beta.fly.dev/api"

with open("token.txt", "r",) as f:
    lines = f.readlines()
    botToken = lines[0].rstrip("\n")
    gitToken = lines[1].rstrip("\n")
    tcgToken = lines[2].rstrip("\n")

dataGen = dataGetter(gitToken)

bot.load("exts.card", None, dataGen)
bot.load("exts.util", None)
bot.load("exts.admin", None, (dataGen, tcgToken, API_URL))

bot.start(botToken)