from interactions import Extension, Client, CommandContext, Embed, File, extension_command, option
from datetime import datetime as dt
from PIL import Image, ImageDraw
from requests import get
from io import BytesIO

from datagen import dataGetter
from deck import deckToHash

class adminExt(Extension):
    def __init__(self, client:Client, dataGenerator:dataGetter, key:str, url:str) -> None:
        self.dataGen = dataGenerator
        self.headers = {"api-key": key}
        self.url = url

    @extension_command()
    async def admin(self, ctx:CommandContext):
        """Commands linked to the administration of of hc-tcg.fly.dev"""

    def genHealth(self, val:int):
        if val < 101:
            health = self.dataGen.universeImage["health_low"]
        elif val < 201:
            health = self.dataGen.universeImage["health_mid"]
        else:
            health = self.dataGen.universeImage["health_hi"]
        hDraw = ImageDraw.Draw(health)
        font = self.dataGen.font.font_variant(size=147)
        hDraw.text((200, 200), str(val), (0, 0, 0), font, "mt")
        return health.resize((200, 200))
    
    def genBoard(self, p1Board:dict, p2Board:dict):
        im = Image.new("RGBA", (200*11, 200*5))
        for i, (p1, mid, p2) in enumerate(zip(p1Board["rows"], ["", "", "", "", "effect"], p2Board["rows"])):
            for itemNum, item in enumerate(p1["itemCards"]):
                if item:
                    itemIm = self.dataGen.universeImage[item["cardId"]].resize((200, 200))
                    im.paste(itemIm, (itemNum*200, i*200), itemIm)
            if p1["effectCard"]:
                effect = self.dataGen.universeImage[p1["effectCard"]["cardId"]].resize((200, 200))
                im.paste(effect, ((3*200), i*200), effect)
            if p1["hermitCard"]:
                hermit = self.dataGen.universeImage[p1["hermitCard"]["cardId"]].rotate(0 if p1Board["activeRow"] == i else -90).resize((200, 200))
                im.paste(hermit, ((4*200), i*200), hermit)
                health = self.genHealth(p1["health"])
                im.paste(health, (5*200, i*200), health)
            if mid:
                single = p1Board["singleUseCard"] if p1Board["singleUseCard"] else p2Board["singleUseCard"] if p2Board["singleUseCard"] else None
                if single != None:
                    card = self.dataGen.universeImage[single["cardId"]].resize((200, 200))
                    im.paste(card, (i*200, 6*200), card)
            for itemNum, item in enumerate(p2["itemCards"], -3):
                if item:
                    itemIm = self.dataGen.universeImage[item["cardId"]].resize((200, 200))
                    im.paste(itemIm, (itemNum*200+200*11, i*200), itemIm)
            if p2["effectCard"]:
                effect = self.dataGen.universeImage[p2["effectCard"]["cardId"]].resize((200, 200))
                im.paste(effect, ((9*200), i*200), effect)
            if p2["hermitCard"]:
                hermit = self.dataGen.universeImage[p2["hermitCard"]["cardId"]].rotate(0 if p2Board["activeRow"] == i else -90).resize((200, 200))
                im.paste(hermit, ((8*200), i*200), hermit)
                health = self.genHealth(p2["health"])
                im.paste(health, (7*200, i*200), health)
        return im

    def gameEmbed(self, game:dict):
        p1 = game["state"]["players"][game["playerIds"][0]]
        p1Deck = deckToHash((card["cardId"] for card in p1["pile"]+ p1["hand"] + p1["discarded"])).decode()
        p2 = game["state"]["players"][game["playerIds"][1]]
        p2Deck = deckToHash((card["cardId"] for card in p1["pile"]+ p1["hand"] + p1["discarded"])).decode()
        e = Embed(
            title = f"{game['code']} ({game['id']})" if game["code"] else game["id"],
            description=f"{p1['playerName']} ({p1['lives']} lives) vs {p2['playerName']} ({p2['lives']} lives)",
            timestamp=dt.fromtimestamp(game["createdTime"]/1000),
        )
        e.set_footer("Bot by Tyrannicodin")
        e.add_field(f"{p1['playerName']} hash", p1Deck)
        e.add_field(f"{p2['playerName']} hash", p2Deck)
        e.set_image("attachment://board.png")
        im = self.genBoard(p1["board"], p2["board"])
        return e, im

    @admin.subcommand()
    @option("The player to search for")
    async def games(self, ctx:CommandContext, playername:str=""):
        data = get(f"{self.url}/games", headers=self.headers).json()[0]
        e, im = self.gameEmbed(data)
        with BytesIO() as imBytes:
            im.save(imBytes, "png")
            await ctx.send(embeds=e, files=File("board.png", imBytes))

def setup(client, args):
    return adminExt(client, *args)
