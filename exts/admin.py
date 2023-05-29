from interactions import (
    Extension,
    Client,
    SlashContext,
    Embed,
    File,
    Activity,
    ActivityType,
    OptionType,
    slash_option,
    slash_command,
)
from aiohttp.web import post, Application, Response, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from interactions.ext.paginators import Paginator
from requests import get, post, ConnectionError
from datetime import datetime as dt
from PIL import Image, ImageDraw
from json import load, dump
from pyjson5 import decode
from io import BytesIO
from time import time

from datagen import dataGetter
from deck import deckToHash


def getOpponent(players: list[str], player: str) -> str:
    try:
        players.remove(player)
    except ValueError:
        return None
    return players[0] if len(players) > 0 else None


def getWinnerStatement(game: dict) -> str:
    winnerId = game["endInfo"].get("winner")
    if not winnerId:
        return "Game was a tie"
    if len(game["playerNames"]) == 1:
        return f"{game['playerNames'][0]} beat {game['playerNames'][0]}"
    winner = game["playerNames"][game["playerIds"].index(winnerId)]
    loser = getOpponent(game["playerNames"], winner)
    return f"{winner} beat {loser}"


class adminExt(Extension):
    def __init__(
        self,
        client: Client,
        dataGenerator: dataGetter,
        key: str,
        url: str,
        scheduler: AsyncIOScheduler,
        webServer: Application,
        dataFile: str,
    ) -> None:
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

        scheduler.add_job(self.updateStatus, IntervalTrigger(seconds=5))

        webServer.add_routes([post("/game_end", self.gameEnd)])

        self.reloadInfo = {"scheduler": scheduler, "server": webServer}

    async def updateStatus(self):
        try:
            games: int = len(get(f"{self.url}/games", headers=self.headers).json())
        except ConnectionError:
            return await self.client.change_presence(
                activity=Activity(
                    "the server being down",
                    ActivityType.WATCHING,
                    "https://hc-tcg.fly.dev/",
                )
            )
        await self.client.change_presence(
            activity=Activity(
                f"{games} games", ActivityType.WATCHING, "https://hc-tcg.fly.dev/"
            )
        )

    @slash_command()
    async def admin(self, ctx: SlashContext):
        """Commands linked to the administration of of hc-tcg.fly.dev"""

    def genHealth(self, val: int):
        if val < 101:
            health = self.dataGen.universeImage["health_low"]
        elif val < 201:
            health = self.dataGen.universeImage["health_mid"]
        else:
            health = self.dataGen.universeImage["health_hi"]
        health = health.copy()
        hDraw = ImageDraw.Draw(health)
        font = self.dataGen.font.font_variant(size=73)
        hDraw.text((100, 100), str(val), (0, 0, 0), font, "mt")
        return health

    def genBoard(self, p1Board: dict, p2Board: dict):
        im = Image.new("RGBA", (200 * 13, 200 * 5), (174, 180, 180))
        for i, (p1, mid, p2) in enumerate(
            zip(p1Board["rows"], ["", "", "", "", "effect"], p2Board["rows"])
        ):
            for itemNum, item in enumerate(p1["itemCards"]):
                if item:
                    itemIm = self.dataGen.universeImage[item["cardId"]]
                    im.paste(itemIm, (itemNum * 200, i * 200), itemIm)
            if p1["effectCard"]:
                effect = self.dataGen.universeImage[p1["effectCard"]["cardId"]]
                im.paste(effect, ((3 * 200), i * 200), effect)
            if p1["hermitCard"]:
                hermit = self.dataGen.universeImage[p1["hermitCard"]["cardId"]].rotate(
                    0 if p1Board["activeRow"] == i else -90
                )
                im.paste(hermit, ((4 * 200), i * 200), hermit)
                health = self.genHealth(p1["health"])
                im.paste(health, (5 * 200, i * 200), health)
            if mid:
                single = (
                    p1Board["singleUseCard"]
                    if p1Board["singleUseCard"]
                    else p2Board["singleUseCard"]
                    if p2Board["singleUseCard"]
                    else None
                )
                if single != None:
                    with self.dataGen.universeImage[single["cardId"]] as card:
                        im.paste(card, (6 * 200, i * 200), card)
            for itemNum, item in enumerate(p2["itemCards"], -3):
                if item:
                    with self.dataGen.universeImage[item["cardId"]] as itemIm:
                        im.paste(itemIm, (itemNum * 200 + 200 * 13, i * 200), itemIm)
            if p2["effectCard"]:
                with self.dataGen.universeImage[p2["effectCard"]["cardId"]] as effect:
                    im.paste(effect, ((9 * 200), i * 200), effect)
            if p2["hermitCard"]:
                with self.dataGen.universeImage[p2["hermitCard"]["cardId"]].rotate(
                    0 if p2Board["activeRow"] == i else -90
                ) as hermit:
                    im.paste(hermit, ((8 * 200), i * 200), hermit)
                    health = self.genHealth(p2["health"])
                    im.paste(health, (7 * 200, i * 200), health)
        return im

    def getGameInfo(self, game: dict):
        p1 = game["state"]["players"][game["playerIds"][0]]
        p1["deck"] = deckToHash(
            (card["cardId"] for card in p1["pile"] + p1["hand"] + p1["discarded"])
        ).decode()
        try:
            p2 = game["state"]["players"][game["playerIds"][1]]
            p2["deck"] = deckToHash(
                (card["cardId"] for card in p2["pile"] + p2["hand"] + p2["discarded"])
            ).decode()
        except:
            p2 = None
        return (
            p1,
            p2,
            {
                "code": game["code"],
                "id": game["id"],
                "creation": game["createdTime"],
            },
        )

    def gameEmbed(self, game: dict):
        p1, p2, gameData = self.getGameInfo(game)
        e = (
            Embed(
                title=f"{gameData['code']} ({gameData['id']})"
                if gameData["code"]
                else gameData["id"],
                description=f"{p1['playerName']} ({p1['lives']} lives) vs {p2['playerName']} ({p2['lives']} lives)"
                if p2
                else f"{p1['playerName']} waiting for opponent",
                timestamp=dt.fromtimestamp(gameData["creation"] / 1000),
            )
            .set_footer(
                "Bot by Tyrannicodin",
            )
            .add_field(
                f"{p1['playerName']} hash",
                p1["deck"],
            )
        )
        im = Image.new("RGBA", (0, 0))
        if p2:
            e.add_field(
                f"{p2['playerName']} hash",
                p2["deck"],
            )
            e.set_image("attachment://board.png")
            im = self.genBoard(p1["board"], p2["board"])
        return e, im

    def simpleInfo(self, game: dict):
        p1, p2, gameData = self.getGameInfo(game)
        if p2:
            return (
                f"{gameData['code']} ({gameData['id']})"
                if gameData["code"]
                else gameData["id"],
                f"{p1['playerName']} ({p1['lives']} lives) vs {p2['playerName']} ({p2['lives']} lives)",
            )
        return (
            f"{gameData['code']} ({gameData['id']})"
            if gameData["code"]
            else gameData["id"],
            f"Waiting for second player",
        )

    @admin.subcommand()
    @slash_option(
        "search",
        "The player name, game id or game code to search for",
        OptionType.STRING,
    )
    async def gameinfo(
        self,
        ctx: SlashContext,
        search: str = "",
    ):
        """Get information about ongoing games, do not pass a search argument to get all ongoing games"""
        data: list = get(f"{self.url}/games", headers=self.headers).json()
        data.sort(key=lambda x: x.get("createdTime"))
        if search != "":
            data = next(
                (
                    game
                    for game in data
                    if game["id"] == search
                    or search in game["playerNames"]
                    or game["code"] == search
                ),
                None,
            )
            if not data:
                await ctx.send(
                    "Couldn't find that game, run `/admin gameinfo` without arguments to get a list of games",
                    ephemeral=True,
                )
                return
            e, im = self.gameEmbed(data)
            with BytesIO() as imBytes:
                im.save(imBytes, "png")
                imBytes.seek(0)
                await ctx.send(embeds=e, files=File(imBytes, "board.png"))
            im.close()
            return
        embeds = []
        pageLength = len(data) // 10 + 1
        for i in range(pageLength):
            e = Embed(
                title=f"Active games ({i*10+1} - {i*10+(len(data)%10 if i==pageLength-1 else 10)} of {len(data)})",
                timestamp=dt.now(),
            )
            for dat in range(
                i * 10, i * 10 + (len(data) % 10 if i == pageLength - 1 else 10)
            ):
                e.add_field(*self.simpleInfo(data[dat]), False)
            embeds.append(e)
        if len(embeds) > 1:
            await Paginator.create_from_embeds(self.client, *embeds, timeout=60).send(
                ctx
            )
        else:
            await ctx.send(embeds=embeds[0])

    def addWin(self, game: dict):
        self.winData.append(game)
        with open(self.dataFile, "w") as f:
            dump(self.winData, f)

    async def gameEnd(self, req: Request):
        json: dict = decode((await req.content.read()).decode())
        if req.headers.get("api-key") != self.headers["api-key"]:
            return Response(status=403)
        requiredKeys = [
            "createdTime",
            "id",
            "code",
            "playerIds",
            "playerNames",
            "endInfo",
            "endTime",
        ]
        if not all((requiredKey in json.keys() for requiredKey in requiredKeys)):
            return Response(status=400)

        json["endInfo"].pop("deadPlayerIds")
        self.addWin(json)
        return Response()

    def pastEmbed(self, game: dict):
        e = (
            Embed(
                title=f"{game['code']} ({game['id']})" if game["code"] else game["id"],
                description=getWinnerStatement(game),
                timestamp=dt.fromtimestamp(game["endTime"] / 1000),
            )
            .add_field(
                "Reason",
                f"{game['endInfo']['outcome']}" + f": {game['endInfo']['reason']}"
                if game["endInfo"]["reason"]
                else "",
            )
            .add_field(
                "From - To",
                f"<t:{round(game['createdTime']/1000)}:f> - <t:{round(game['createdTime']/1000)}:f>",
            )
        )
        return e

    @admin.subcommand()
    @slash_option(
        "search",
        "The game code, game id, player name or player id to search for",
        OptionType.STRING,
    )
    async def getwins(self, ctx: SlashContext, search: str = ""):
        """Get basic information about past games"""
        self.winData.sort(key=lambda x: x.get("endTime"))
        if search != "":
            results = [
                game
                for game in self.winData
                if game["id"] in search
                or any(search in playerName for playerName in game["playerNames"])
                or search in game["code"]
            ]
            if len(results) == 0:
                await ctx.send(
                    "Couldn't find that game, run `/admin getwins` without arguments to get a list of all past games",
                    ephemeral=True,
                )
        else:
            results = self.winData
        embeds = []
        for r in results:
            embeds.append(self.pastEmbed(r))
        if len(embeds) > 1:
            await Paginator.create_from_embeds(self.client, *embeds, timeout=60).send(
                ctx
            )
        elif len(embeds) == 1:
            await ctx.send(embeds=embeds[0])
        else:
            await ctx.send("Couldn't find any logged wins", ephemeral=True)

    @admin.subcommand()
    @slash_option("player1id", "The first player's id", OptionType.STRING)
    @slash_option("player2id", "The second player's id", OptionType.STRING)
    async def creategame(self, ctx: SlashContext, player1id: str, player2id: str):
        res = post(
            f"{self.url}/createGame",
            json={
                "player1": player1id,
                "player2": player2id,
            },
            headers=self.headers,
        )
        if res.status_code == 201:
            await ctx.send("Game created!", ephemeral=True)
        elif res.status_code == 404:
            await ctx.send(
                "Couldn't find one (or both) of those players!", ephemeral=True
            )
        else:
            await ctx.send(
                f"Some other error happened, {res.status_code}, got body: {res.text}"
            )


def setup(
    client,
    dataGenerator: dataGetter,
    key: str,
    url: str,
    scheduler: AsyncIOScheduler,
    server: Application,
    dataFile: str,
):
    return adminExt(client, dataGenerator, key, url, scheduler, server, dataFile)
