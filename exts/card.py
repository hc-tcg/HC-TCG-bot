from interactions import (
    Extension,
    Client,
    SlashContext,
    File,
    Embed,
    SlashCommandChoice,
    AutocompleteContext,
    OptionType,
    Button,
    ButtonStyle,
    ComponentContext,
    slash_option,
    global_autocomplete,
    slash_command,
    component_callback,
    spread_to_rows,
)
from matplotlib import pyplot as plt
from datetime import datetime as dt
from re import compile as reCompile
from collections import Counter
from urllib.parse import quote
from io import BytesIO
from PIL import Image
from time import time

from util import hashToStars, hashToDeck, probability, dataGetter

beige = (226, 202, 139)
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
    "farm": (124, 204, 12),
}


def rgbToInt(rgb: tuple[int, int, int]) -> int:
    return (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]


def count(s: str) -> str:
    final = []
    for k, v in Counter(s).most_common():
        final.append(f"{v}x {k}")
    return ", ".join(final)


def longest(typeCounts: dict[str, dict]) -> list:
    return [
        key
        for key in typeCounts.keys()
        if typeCounts.get(key) == max([num for num in typeCounts.values()])
    ]


def getBestFactors(number: int) -> tuple[int, int]:
    a, b, i = 1, number, 0
    while a < b:
        i += 1
        if number % i == 0:
            a = i
            b = number // i
    return b, a


class cardExt(Extension):
    def __init__(self, client: Client, dataGenerator: dataGetter) -> None:
        self.dataGenerator = dataGenerator
        self.lastReload = time()
        self.namedUniverse = [
            {
                "name": v["name"]
                if not "health" in v.keys()
                else f"{v['name']} {v['rarity'].replace('_', ' ')}",
                "value": k,
            }
            for k, v in list(self.dataGenerator.universeData.items())
        ]

    def getStats(
        self, deck: list
    ) -> tuple[Image.Image, tuple[int, int, int], dict[str, int]]:
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
                if card in self.dataGenerator.universeData.keys():
                    typeCounts[self.dataGenerator.universeData[card]["hermitType"]] += 1
            else:
                effects.append(card)

        hermits.sort()
        items.sort()
        effects.sort()
        width, height = getBestFactors(len(deck))
        im = Image.new("RGBA", (width * 200, height * 200))
        for i, card in enumerate(hermits + effects + items):
            toPaste = (
                self.dataGenerator.universeImage[card]
                .resize((200, 200))
                .convert("RGBA")
            )
            im.paste(toPaste, ((i % width) * 200, (i // width) * 200), toPaste)
        return im, (len(hermits), len(effects), len(items)), typeCounts

    @global_autocomplete("card")
    async def card_autocomplete(self, ctx: AutocompleteContext):
        if not ctx.input_text:
            await ctx.send(self.namedUniverse[0:25])
            return
        await ctx.send(
            [
                card
                for card in self.namedUniverse
                if ctx.input_text.lower() in card["name"].lower()
            ][0:25]
        )

    @slash_command()
    async def card(self, ctx: SlashContext):
        """Get information about cards and decks"""

    @card.subcommand()
    @slash_option("deck", "The exported hash of the deck", OptionType.STRING, True)
    @slash_option("name", "The name of your deck", OptionType.STRING)
    @slash_option(
        "show_hash",
        "If the deck should be shown - defaults to true",
        OptionType.BOOLEAN,
    )
    @slash_option(
        "site",
        "The site to link the deck to",
        OptionType.STRING,
        choices=[
            SlashCommandChoice(
                name="Dev site",
                value="https://hc-tcg.fly.dev",
            ),
            SlashCommandChoice(
                name="Xisumaverse",
                value="https://tcg.xisumavoid.com",
            ),
            SlashCommandChoice(
                name="Beef",
                value="https://tcg.omegaminecraft.com",
            ),
            SlashCommandChoice(
                name="Beta",
                value="https://hc-tcg-beta.fly.dev",
            ),
        ],
    )
    async def deck(
        self,
        ctx: SlashContext,
        deck: str,
        name: str = None,
        show_hash: str = True,
        site: str = "https://hc-tcg.fly.dev/",
    ):
        """Get information about a deck"""
        if not name:
            name = f"{ctx.author.display_name}'s deck"

        deckList = hashToDeck(deck, self.dataGenerator.universe)
        if not deckList:
            await ctx.send(
                "Invalid deck: Perhaps you're looking for /card info ||Niko||"
            )
            return
        im, hic, typeCounts = self.getStats(deckList)
        col = typeColors[longest(typeCounts)[0]]
        e = (
            Embed(
                title=name,
                description=f"Hash: {deck}" if show_hash else None,
                timestamp=dt.now(),
                color=rgbToInt(col),
            )
            .set_image(
                "attachment://deck.png",
            )
            .add_field(
                "Token cost",
                str(
                    hashToStars(
                        deck, self.dataGenerator.rarities, self.dataGenerator.universe
                    )
                ),
                True,
            )
            .add_field(
                "HEI ratio",
                f"{hic[0]}:{hic[1]}:{hic[2]}",
                True,
            )
            .add_field(
                "Types",
                len([typeList for typeList in typeCounts.values() if typeList != 0]),
                True,
            )
            .set_footer(
                "Bot by Tyrannicodin16",
            )
        )
        with BytesIO() as im_binary:
            im.save(im_binary, "PNG")
            im_binary.seek(0)
            deleteButton = Button(
                style=ButtonStyle.DANGER,
                label="Delete",
                emoji=":wastebasket:",
                custom_id=f"delete_deck:{ctx.author_id}",
            )
            copyButton = Button(
                style=ButtonStyle.LINK,
                label="Copy",
                emoji=":clipboard:",
                url=f"{site}/?deck={deck}&name={quote(name)}",
                disabled=True,  # (not show_hash) - this is temporarily disabled as there's a critical bug atm,
            )
            await ctx.send(
                embeds=e,
                files=File(im_binary, "deck.png"),
                components=spread_to_rows(
                    deleteButton,
                    copyButton,
                ),
            )

    @component_callback(reCompile("delete_deck:[0-9]"))
    async def handleDelete(self, ctx: ComponentContext):
        if str(ctx.author_id) == ctx.custom_id.split(":")[-1]:
            await ctx.message.delete()
            await ctx.send("Deleted!", ephemeral=True)
        else:
            await ctx.send("You can't delete this deck message!", ephemeral=True)

    @card.subcommand()
    @slash_option(
        "card", "The card id to get", OptionType.STRING, True, autocomplete=True
    )
    async def info(self, ctx: SlashContext, card: str):
        """Get information about a card"""
        card = card.casefold()  # Ensure all lowercase
        if card in self.dataGenerator.universeData.keys():
            if card in self.dataGenerator.universes["hermits"]:  # Special for hermits
                dat = self.dataGenerator.universeData[card]
                col = typeColors[dat["hermitType"]]
                e = (
                    Embed(
                        title=dat["name"],
                        description=f"{dat['rarity'].capitalize().replace('_', ' ')} {dat['name']} - {self.dataGenerator.rarities[card]} tokens",
                        timestamp=dt.now(),
                        color=rgbToInt(col),
                    )
                    .add_field(
                        "Rarity",
                        "Ultra rare"
                        if dat["rarity"] == "ultra_rare"
                        else dat["rarity"].capitalize(),
                        True,
                    )
                    .add_field(
                        "Primary attack",
                        dat["primary"]["name"]
                        if dat["primary"]["power"] == None
                        else dat["primary"]["name"] + " - " + dat["primary"]["power"],
                        False,
                    )
                    .add_field("Attack damage", dat["primary"]["damage"], True)
                    .add_field("Items required", count(dat["primary"]["cost"]), True)
                    .add_field(
                        "Secondary attack",
                        dat["secondary"]["name"]
                        if dat["secondary"]["power"] == None
                        else dat["secondary"]["name"]
                        + " - "
                        + dat["secondary"]["power"].replace("\n\n", "\n"),
                        False,
                    )
                    .add_field("Attack damage", dat["secondary"]["damage"], True)
                    .add_field("Items required", count(dat["secondary"]["cost"]), True)
                )
            else:
                dat = self.dataGenerator.universeData[card]
                e = Embed(
                    title=dat["name"],
                    description=dat["description"]
                    if "description" in dat.keys()
                    else f"{dat['hermitType']} item card",
                    timestamp=dt.now(),
                    color=rgbToInt(typeColors[dat["hermitType"]])
                    if "hermitType" in dat.keys()
                    else rgbToInt(beige),
                ).add_field(
                    "Rarity",
                    "Ultra rare"
                    if dat["rarity"] == "ultra_rare"
                    else dat["rarity"].capitalize(),
                    True,
                )
            e.set_thumbnail(f"attachment://{dat['id']}.png")
            e.set_footer("Bot by Tyrannicodin16")
            with BytesIO() as im_binary:
                self.dataGenerator.universeImage[card].save(im_binary, "PNG")
                im_binary.seek(0)
                await ctx.send(embeds=e, files=File(im_binary, f"{dat['id']}.png"))
        else:
            await ctx.send("Couldn't find that card!", ephemeral=True)

    @card.subcommand()
    async def reload(self, ctx: SlashContext):
        """Reload the card data and images"""
        if (
            self.lastReload + 60 * 30 < time()
        ):  # Limit reloading to every 30 minutes as it's quite slow
            await ctx.send("Reloading...", ephemeral=True)
            startTime = time()
            self.dataGenerator.reload()
            self.namedUniverse = [
                {
                    "name": v["name"]
                    if not "health" in v.keys()
                    else f"{v['name']} {v['rarity'].replace('_', ' ')}",
                    "value": k,
                }
                for k, v in list(self.dataGenerator.universeData.items())
            ]
            await ctx.send(
                f"Reloaded! Took {round(time()-startTime)} seconds", ephemeral=True
            )
            self.lastReload = time()
            return
        await ctx.send(
            "Reloaded within the last 10 minutes, please try again later.",
            ephemeral=True,
        )

    @card.subcommand()
    @slash_option(
        "hermits", "The number of hermits in your deck", OptionType.INTEGER, True
    )
    @slash_option(
        "desired_chance",
        "Looks for the number of turns to get this chance of having the desired number of cards",
        OptionType.INTEGER,
    )
    @slash_option(
        "desired_hermits", "The number of hermits you want", OptionType.INTEGER
    )
    async def twohermits(
        self,
        ctx: SlashContext,
        hermits: int,
        desired_chance: int = 50,
        desired_hermits: int = 2,
    ):
        """View probability to have a number of hermits in your hand after a certain number of draws"""
        if hermits < 1 or hermits > 36:
            await ctx.send("Invalid hermit count (1-36)", ephemeral=True)
            return
        plt.figure()
        xs = [i for i in range(35)]
        ys = [probability(hermits, i, desired_hermits) * 100 for i in xs]
        surpass = next(
            (idx[0] for idx in enumerate(ys) if idx[1] >= desired_chance), None
        )
        plt.plot(xs, [round(y) for y in ys])
        plt.xlabel("Draws")
        plt.ylabel("Probability")
        plt.title(
            f"Chance of having {desired_hermits} hermits in your hand after x draws for {hermits} hermits"
        )
        plt.grid(True)
        e = Embed(
            title=f"Chance of having {desired_hermits} hermits in your hand after x draws for {hermits} hermits",
            timestamp=dt.now(),
            color=rgbToInt((178, 178, 255)),
        ).add_field("Initial draw chance", f"{ys[0]}%", inline=True)
        if surpass or surpass == 0:
            e.add_field(f"Hits {desired_chance}%", f"{surpass} draw(s)", inline=True)
        else:
            e.add_field(f"Hits {desired_chance}%", "Never", inline=True)
        e.set_footer("Bot by Tyrannicodin | Probability calculations by Allophony")
        e.set_image("attachment://graph.png")
        with BytesIO() as figBytes:
            plt.savefig(figBytes, format="png")
            figBytes.seek(0)
            await ctx.send(embeds=e, files=File(figBytes, "graph.png"))
        plt.close()

    @card.subcommand()
    async def chart(self, ctx: SlashContext):
        """Displays the type chart by u/itsNizart"""
        e = (
            Embed(
                title="Type chart",
                timestamp=dt.now(),
            )
            .set_image(
                "attachment://typechart.png",
            )
            .set_author(
                "u/itsNizart",
                "https://www.reddit.com/user/itsNizart",
                "https://styles.redditmedia.com/t5_2efni5/styles/profileIcon_jzv50kvrvlb71.png",
            )
            .set_footer("Bot by Tyrannicodin")
        )
        await ctx.send(embeds=e, files=File("typechart.png"))


def setup(client: Client, dataGenerator: dataGetter):
    cardExt(client, dataGenerator)
