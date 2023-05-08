from interactions import Extension, Client, CommandContext, File, Embed, Choice, extension_command, option
from datetime import datetime as dt
from collections import Counter
from os import listdir
from io import BytesIO
from json import load
from PIL import Image
from time import time

from datagen import dataGetter
from deck import hashToStars, hashToDeck, getData, universe

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
    def __init__(self, client:Client, token:str) -> None:
        self.dataGenerator = dataGetter(token)

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
        e.add_field("Token cost", str(hashToStars(deck, self.cardData)), True)
        e.add_field("HEI ratio", f"{hic[0]}:{hic[1]}:{hic[2]}", True)
        e.add_field("Types", len([typeList for typeList in typeCounts.values() if typeList != 0]), True)
        with BytesIO() as im_binary:
            im.save(im_binary, 'PNG')
            im_binary.seek(0)
            await ctx.send(embeds=e, files=File(fp=im_binary, filename="deck.png"))

    @card.subcommand(
        name = "info",
    )
    @option(
        name = "card",
        description = "The card id to get",
        autocomplete = True,
    )
    async def info(self, ctx:CommandContext, card:str):
        """Get information about a hermit"""
        if card in self.dataGenerator.universeData.keys():
            if card in self.dataGenerator.universes["hermits"]: #Special for hermits
                pass
            elif card in self.dataGenerator.universes["items"]: #Simplified for items
                pass
            else: #Items 

        else:
            ctx.send("Couldn't find that card!", ephemeral=True)
    
    @card.subcommand()
    async def reload(self, ctx:CommandContext):
        if self.lastReload + 60*5 > time(): #Limit reloading to every 5 minutes as it's quite intensive
            msg = await ctx.send("Reloading...", ephemeral=True)
            startTime = time()
            self.dataGenerator.reload()
            await msg.edit(f"Reloaded! Took {round(time()-startTime)}")

def setup(client:Client, slash:str):
    cardExt(client, slash)
