from interactions import Extension, Client, CommandContext, File, Embed, Choice, extension_command, option
from datetime import datetime as dt
from collections import Counter
from os import listdir
from io import BytesIO
from json import load
from PIL import Image

from deck import hashToStars, hashToDeck, universe

typeColors = {
    "miner": (110, 105, 108),
    "terraform": (217, 119, 147),
    "speedrunner": (223, 226, 36),
    "pvp": (85, 202, 194),
    "builder": (184, 162, 154),
    "balanced": (101, 124, 50),
    "explorer": (103, 138, 190),
    "prankster": (116, 55, 168),
    "redstone": (185, 33, 42),
    "farm": (124, 204, 12)
}

class cardExt(Extension):
    def __init__(self, client:Client, slash:str) -> None:
        self.client:Client = client

        self.slash = slash

        self.cards:dict[str, str] = {}
        self.types:dict[str, list[str]] = {}

        for file in [f for f in listdir("hermitData") if not f.startswith(".")]:
            with open(f"hermitData{slash}{file}", "r") as f:
                d = load(f)
                self.cards[d[0]["name"].capitalize()] = f"hermitData{slash}{file}"
                for card in d:
                    if card["hermitType"] in self.types.keys():
                        self.types[card["hermitType"]].append(card["id"])
                    else:
                        self.types[card["hermitType"]] = [card["id"]]
    
    def getStats(self, deck:list) -> tuple[Image.Image, tuple[int,int,int], dict[str, int]]:
        typeCounts = {
            "miner": 0,
            "terraform": 0,
            "speedrunner": 0,
            "pvp": 0,
            "builder": 0,
            "balanced": 0,
            "explorer": 0,
            "prankster": 0,
            "redstone": 0,
            "farm": 0,
        }

        hermits, items, effects = [[] for _ in range(3)]
        for card in deck:
            if card.startswith("item"):
                items.append(card)
            elif card.endswith(("rare", "common")):
                hermits.append(card)
                for cardType, hermitList in self.types.items():
                    if card in hermitList:
                        typeCounts[cardType] += 1
                        break
            else:
                effects.append(card)
        
        hermits.sort()
        items.sort()
        effects.sort()

        im = Image.new("RGBA", (6*200, 7*200))
        for i, card in enumerate(hermits + effects + items):
            toPaste = Image.open(f"staticImages{self.slash}{card}.png").resize((200, 200)).convert("RGBA")
            im.paste(toPaste, ((i%6)*200,(i//6)*200), toPaste)
        return im, (len(hermits), len(effects), len(items)), typeCounts

    def longest(self, typeCounts:dict[str, dict]) -> list:
        return [key for key in typeCounts.keys() if typeCounts.get(key)==max([num for num in typeCounts.values()])]

    def count(self, s:str) -> str:
        final = []
        for k, v in Counter(s).most_common():
            final.append(f"{v}x {k}")
        return ", ".join(final)

    def hermitCards(self, file, rarity=None) -> list[tuple[Image.Image, Embed, str]]:
        with open(file, "r") as f:
            data = load(f)
        for card in data:
            if rarity != None and card["rarity"] != rarity: continue
            col = typeColors[card["hermitType"]]
            e = Embed(
                title = card["name"],
                description = card["rarity"].capitalize().replace("_", " ") + " " + card["name"],
                timestamp = dt.now(),
                color = (col[0] << 16) + (col[1] << 8) + (col[2]),
            )
            e.set_thumbnail(f"attachment://{card['id']}.png")

            e.add_field("Primary attack", card["primary"]["name"] if card["primary"]["power"] == None else card["primary"]["name"] + " - " + card["primary"]["power"], False)
            e.add_field("Attack damage", card["primary"]["damage"], True)
            e.add_field("Items required", self.count(card["primary"]["cost"]), True)

            e.add_field("Secondary attack", card["secondary"]["name"] if card["secondary"]["power"] == None else card["secondary"]["name"] + " - " + card["secondary"]["power"].replace("\n\n", "\n"), False)
            e.add_field("Attack damage", card["secondary"]["damage"], True)
            e.add_field("Items required", self.count(card["secondary"]["cost"]), True)

            im = Image.open(f"staticImages{self.slash}{card['id']}.png")
            yield im, e, card["id"]

    @extension_command()
    async def card(self, ctx:CommandContext):
        """Get information about cards and decks"""
    
    @card.subcommand()
    @option(
        description = "The exported hash of the deck",
    )
    @option(
        description = "The site to link the deck to",
        choices = [
            Choice(
                name = "Dev site",
                value = "https://hc-tcg.online/?deck=",
            ),
            Choice(
                name = "Xisumaverse",
                value = "https://tcg.xisumavoid.com/?deck=",
            ),
            Choice(
                name = "Beef",
                value = "https://tcg.omegaminecraft.com/?deck=",
            ),
            Choice(
                name = "Balanced",
                value = "https://tcg.prof.ninja/?deck=",
            ),
        ],
    )
    async def deck(self, ctx:CommandContext, deck:str, site:str="https://hc-tcg.online/?deck="):
        """Get information about a deck"""
        deckList = hashToDeck(deck, universe)
        im, hic, typeCounts = self.getStats(deckList)
        col = typeColors[self.longest(typeCounts)[0]]
        e = Embed(
            title = "Deck stats",
            description = f"Hash: {deck}",
            url = site + deck,
            timestamp = dt.now(),
            color = (col[0] << 16) + (col[1] << 8) + (col[2]),
        )
        e.set_image("attachment://deck.png")
        e.add_field("Token cost", str(hashToStars(deck)), True)
        e.add_field("HEI ratio", f"{hic[0]}:{hic[1]}:{hic[2]}", True)
        e.add_field("Types", len([typeList for typeList in typeCounts.values() if typeList != 0]), True)
        with BytesIO() as im_binary:
            im.save(im_binary, 'PNG')
            im_binary.seek(0)
            await ctx.send(embeds=e, files=File(fp=im_binary, filename="deck.png"))

    @card.subcommand(
        name = "hermit",
    )
    @option(
        name = "hermit",
        description = "The hermit to get",
        autocomplete = True,
    )
    @option(
        description = "The rarity of the hermit",
        choices = [
            Choice(name = "Common", value = "common"),
            Choice(name = "Rare", value = "rare"),
            Choice(name = "Ultra rare", value = "ultra_rare"),
        ]
    )
    async def info(self, ctx:CommandContext, card:str, rarity:str = None,):
        """Get information about a hermit"""
        embeds = []
        images = []
        imObjs = []
        if card.capitalize() in self.cards.keys():
            for im, e, _id in self.hermitCards(self.cards[card.capitalize()], rarity):
                embeds.append(e)
                imBytes = BytesIO()
                im.save(imBytes, "PNG")
                imBytes.seek(0)
                images.append(File(fp=imBytes, filename=f"{_id}.png"))
                imObjs.append(imBytes)
            if len(embeds) == 0:
                await ctx.send("That hermit doesn't have a card of that rarity", ephemeral = True)
                return
            await ctx.send(embeds = embeds, files = images)
            for image in imObjs:
                image.close()
        else:
            await ctx.send("Hermit not found, allowed hermits are: " + ", ".join(self.cards.keys()), ephemeral=True)
    
    @card.autocomplete("hermit")
    async def autocompleteCard(self, ctx:CommandContext, name:str=None):
        if not name:
            await ctx.populate([{"name": n, "value": n} for n in list(self.cards.keys())[0:25]])
            return
        await ctx.populate([{"name": n, "value": n} for n in self.cards.keys() if name.lower() in n.lower()][0:25])

def setup(client:Client, slash:str):
    cardExt(client, slash)
