from interactions import Extension, Client, SlashContext, Embed, File, Activity, ActivityType, OptionType, slash_option, slash_command
from aiohttp.web import post, Application, Response, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from interactions.ext.paginators import Paginator
from requests import get, ConnectionError
from datetime import datetime as dt
from PIL import Image, ImageDraw
from json import load, dump
from pyjson5 import decode
from io import BytesIO
from time import time

from datagen import dataGetter
from deck import deckToHash

class adminExt(Extension):
    def __init__(self, client:Client, dataGenerator:dataGetter, key:str, url:str, scheduler:AsyncIOScheduler, webServer:Application, dataFile:str, counterFile:str) -> None:
        self.dataGen = dataGenerator
        self.headers = {"api-key": key}
        self.url = url
        self.client = client
        
        self.dataFile = dataFile
        try:
            with open(self.dataFile, "r") as f:
                self.winData = load(f)
        except FileNotFoundError:
            self.winData = []

        self.countFile = counterFile
        try:
            with open(self.countFile, "r") as f:
                self.countData = load(f)
        except FileNotFoundError:
            self.countData = []

        scheduler.add_job(self.updateStatus, IntervalTrigger(seconds=5))

        webServer.add_routes([post("/game_end", self.gameEnd)])
    
    async def updateStatus(self):
        try:
            games:int = len(get(f"{self.url}/games", headers=self.headers).json())
        except ConnectionError:
            return await self.client.change_presence(activity=Activity("the server being down", ActivityType.WATCHING, "https://hc-tcg.fly.dev/"))
        self.countData.append([games, round(time(), 2)])
        with open(self.countFile, "w") as f:
            dump(self.countData, f)
        await self.client.change_presence(activity=Activity(f"{games} games", ActivityType.WATCHING, "https://hc-tcg.fly.dev/"))

    @slash_command()
    async def admin(self, ctx:SlashContext):
        """Commands linked to the administration of of hc-tcg.fly.dev"""

    def genHealth(self, val:int):
        if val < 101:
            health = self.dataGen.universeImage["health_low"]
        elif val < 201:
            health = self.dataGen.universeImage["health_mid"]
        else:
            health = self.dataGen.universeImage["health_hi"]
        health = health.copy()
        hDraw = ImageDraw.Draw(health)
        font = self.dataGen.font.font_variant(size=147)
        hDraw.text((200, 200), str(val), (0, 0, 0), font, "mt")
        return health.resize((200, 200))
    
    def genBoard(self, p1Board:dict, p2Board:dict):
        im = Image.new("RGBA", (200*13, 200*5), (174, 180, 180))
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
                    with self.dataGen.universeImage[single["cardId"]].resize((200, 200)) as card:
                        im.paste(card, (6*200, i*200), card)
            for itemNum, item in enumerate(p2["itemCards"], -3):
                if item:
                    with self.dataGen.universeImage[item["cardId"]].resize((200, 200)) as itemIm:
                        im.paste(itemIm, (itemNum*200+200*13, i*200), itemIm)
            if p2["effectCard"]:
                with self.dataGen.universeImage[p2["effectCard"]["cardId"]].resize((200, 200)) as effect:
                    im.paste(effect, ((9*200), i*200), effect)
            if p2["hermitCard"]:
                with self.dataGen.universeImage[p2["hermitCard"]["cardId"]].rotate(0 if p2Board["activeRow"] == i else -90).resize((200, 200)) as hermit:
                    im.paste(hermit, ((8*200), i*200), hermit)
                    health = self.genHealth(p2["health"])
                    im.paste(health, (7*200, i*200), health)
        return im

    def getGameInfo(self, game:dict):
        p1 = game["state"]["players"][game["playerIds"][0]]
        p1["deck"] = deckToHash((card["cardId"] for card in p1["pile"]+ p1["hand"] + p1["discarded"])).decode()
        p2 = game["state"]["players"][game["playerIds"][1]]
        p2["deck"] = deckToHash((card["cardId"] for card in p2["pile"]+ p2["hand"] + p2["discarded"])).decode()
        return p1, p2, {
            "code": game["code"],
            "id": game["id"],
            "creation": game["createdTime"],
        }

    def gameEmbed(self, game:dict):
        p1, p2, gameData = self.getGameInfo(game)
        e = Embed(
            title = f"{gameData['code']} ({gameData['id']})" if gameData["code"] else gameData["id"],
            description=f"{p1['playerName']} ({p1['lives']} lives) vs {p2['playerName']} ({p2['lives']} lives)",
            timestamp=dt.fromtimestamp(gameData["creation"]/1000),
        ).set_footer("Bot by Tyrannicodin",
        ).add_field(f"{p1['playerName']} hash", p1["deck"],
        ).add_field(f"{p2['playerName']} hash", p2["deck"],
        ).set_image("attachment://board.png"
        )
        im = self.genBoard(p1["board"], p2["board"])
        return e, im
    
    def simpleInfo(self, game:dict):
        p1, p2, gameData = self.getGameInfo(game)
        return f"{gameData['code']} ({gameData['id']})" if gameData["code"] else gameData["id"], f"{p1['playerName']} ({p1['lives']} lives) vs {p2['playerName']} ({p2['lives']} lives)"

    @admin.subcommand()
    @slash_option("search", "The player name, game id or game code to search for", OptionType.STRING)
    async def gameinfo(self, ctx:SlashContext, search:str="",):
        """Get information about ongoing games, do not pass a search argument to get all ongoing games"""
        data:list = get(f"{self.url}/games", headers=self.headers).json()
        data.sort(key = lambda x: x.get("createdTime"))
        if search != "":
            data = next((game for game in data if game["id"] == search or search in game["playerNames"] or game["code"] == search), None)
            if data:
                await ctx.send("Couldn't find that player, run `/admin gameinfo` without arguments to get a list of games", ephemeral=True)
            e, im = self.gameEmbed(data)
            with BytesIO() as imBytes:
                im.save(imBytes, "png")
                imBytes.seek(0)
                await ctx.send(embeds=e, files=File(imBytes, "board.png"))
            im.close()
            return
        embeds = []
        pageLength = len(data)//10+1
        for i in range(pageLength):
            e = Embed(
                title=f"Active games ({i*10+1} - {i*10+(len(data)%10 if i==pageLength-1 else 10)} of {len(data)})",
                timestamp=dt.now(),
            )
            for dat in range(i*10, i*10+(len(data)%10 if i==pageLength-1 else 10)):
                e.add_field(*self.simpleInfo(data[dat]), False)
            embeds.append(e)
        if len(embeds) > 1:
            await Paginator.create_from_embeds(self.client, embeds, 60).run()
        else:
            await ctx.send(embeds=embeds[0])
    
    def addData(self, game:dict):
        self.winData.append(game)
        with open(self.dataFile, "w") as f:
            dump(self.winData, f)

    async def gameEnd(self, req:Request):
        json:dict = decode((await req.content.read()).decode())
        if req.headers.get("api-key") != self.headers["api-key"]:
            return Response(status=403)
        requiredKeys = ["createdTime", "id", "code", "playerIds", "playerNames", "endInfo"]
        if not all((requiredKey in json.keys() for requiredKey in requiredKeys)):
            return Response(status=400)

        json["endInfo"].pop("deadPlayerIds")
        self.addData(json)
        return Response()

def setup(client, dataGenerator:dataGetter, key:str, url:str, scheduler:AsyncIOScheduler, server:Application, dataFile:str, countFile:str):
    return adminExt(client, dataGenerator, key, url, scheduler, server, dataFile, countFile)
