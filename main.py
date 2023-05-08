from interactions import Client

bot = Client()

with open("token.txt", "r",) as f:
    lines = f.readlines()
    botToken = lines[0].rstrip("\n",)
    gitToken = lines[1].rstrip("\n")

bot.load("exts.card", None, gitToken)
bot.load("exts.util", None)

bot.start(botToken)