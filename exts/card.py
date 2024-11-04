"""Get information about cards and decks."""

from collections import Counter
from datetime import datetime as dt
from datetime import timezone
from io import BytesIO
from itertools import islice
from math import ceil, sqrt
from re import compile as re_compile
from time import time
from typing import Iterable, Optional
from urllib.parse import quote

from interactions import (
    AutocompleteContext,
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Embed,
    Extension,
    File,
    OptionType,
    SlashCommandChoice,
    SlashContext,
    component_callback,
    global_autocomplete,
    slash_command,
    slash_option,
    spread_to_rows,
)
from matplotlib import pyplot as plt
from PIL import Image

from util import TYPE_COLORS, Card, EffectCard, HermitCard, hash_to_deck, hash_to_stars, probability


def take(items: int, iterable: Iterable) -> list:
    """Return first `items` items of the iterable as a list."""
    return list(islice(iterable, items))


beige = (226, 202, 139)


def rgb_to_int(rgb: tuple[int, int, int]) -> int:
    """Convert an rgb tuple to an integer.

    Args:
    ----
    rgb (tuple): RGB color to convert
    """
    return (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]


def count(s: str) -> str:
    """Count the number of items required."""
    final = []
    for k, v in Counter(s).most_common():
        final.append(f"{v}x {k}")
    return ", ".join(final) if len(final) else "None"


def best_factors(number: int) -> tuple[int, int]:
    """Get as close to being square as possible."""
    x = sqrt(number) // 1
    return ceil(x), ceil(x if number - x**2 == 0 else (number - x**2) / x + x)


class CardExt(Extension):
    """Get information about cards and decks."""

    def __init__(self: "CardExt", _: Client, universe: dict[str, Card]) -> None:
        """Get information about cards and decks.

        Args:
        ----
        universe (dict): Dictionary that converts card ids to Card objects
        """
        self.universe = universe
        self.lastReload = time()

    def get_stats(
        self: "CardExt", deck: list[Card]
    ) -> tuple[Image.Image, tuple[int, int, int], dict[str, int]]:
        """Get information and an image of a deck.

        Args:
        ----
        deck (list): List of card ids in the deck
        """
        type_counts = {
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
        hermits, items, effects = ([] for _ in range(3))
        for card in deck:
            if card.text_id.startswith("item"):
                items.append(card)
            elif card.text_id.endswith(("rare", "common")):
                hermits.append(card)
                if card in self.universe.keys():
                    type_counts[card.hermit_type] += 1
            else:
                effects.append(card)

        hermits.sort(key=lambda x: x.numeric_id)
        items.sort(key=lambda x: x.numeric_id)
        effects.sort(key=lambda x: x.numeric_id)
        width, height = best_factors(len(deck))
        im = Image.new("RGBA", (width * 200, height * 200))
        for i, card in enumerate(hermits + effects + items):
            new_card = card.image.resize((200, 200)).convert("RGBA")
            im.paste(new_card, ((i % width) * 200, (i // width) * 200), new_card)
        return im, (len(hermits), len(effects), len(items)), type_counts

    @global_autocomplete("card_name")
    async def card_autocomplete(self: "CardExt", ctx: AutocompleteContext) -> None:
        """Autocomplete a card name."""
        if not ctx.input_text:
            await ctx.send([card.rarityName for card in take(25, self.universe.values())])
            return
        await ctx.send(
            [
                card.rarityName
                for card in self.universe.values()
                if ctx.input_text.lower() in card.rarityName.lower()
            ][0:25]
        )

    @slash_command()
    async def card(self: "CardExt", _: SlashContext) -> None:
        """Get information about cards and decks."""

    @card.subcommand()
    @slash_option("deck_hash", "The exported hash of the deck", OptionType.STRING, required=True)
    @slash_option("name", "The name of your deck", OptionType.STRING)
    @slash_option(
        "hide_hash", "If the deck's hash should be hidden - defaults to False", OptionType.BOOLEAN
    )
    async def deck(
        self: "CardExt",
        ctx: SlashContext,
        deck_hash: str,
        name: Optional[str] = None,
        *,
        hide_hash: bool = False,
    ) -> None:
        """Get information about a deck."""
        if not name:
            name = f"{ctx.author.display_name}'s deck"

        deck_list = hash_to_deck(deck_hash, self.universe)
        if len(deck_list) > 100:
            await ctx.send(f"A deck of {len(deck_list)} cards is too large!", ephemeral=True)
            return
        if not deck_list:
            await ctx.send("Invalid deck: Perhaps you're looking for /card info")
            return
        im, card_type_counts, hermit_type_counts = self.get_stats(deck_list)
        col = TYPE_COLORS[Counter(hermit_type_counts).most_common()[0][0]]

        e = (
            Embed(
                title=name,
                description=None if hide_hash else f"Hash: {deck_hash}",
                timestamp=dt.now(tz=timezone.utc),
                color=rgb_to_int(col),
            )
            .set_image("attachment://deck.png")
            .add_field("Token cost", str(hash_to_stars(deck_hash, self.universe)), inline=True)
            .add_field(
                "HEI ratio",
                f"{card_type_counts[0]}:{card_type_counts[1]}:{card_type_counts[2]}",
                inline=True,
            )
            .add_field(
                "Types",
                len([typeList for typeList in hermit_type_counts.values() if typeList != 0]),
                inline=True,
            )
            .set_footer("Bot by Tyrannicodin16")
        )
        with BytesIO() as im_binary:
            im.save(im_binary, "PNG")
            im_binary.seek(0)
            delete_button = Button(
                style=ButtonStyle.DANGER,
                label="Delete",
                emoji=":wastebasket:",
                custom_id=f"delete_deck:{ctx.author_id}",
            )
            copy_button = Button(
                style=ButtonStyle.LINK,
                label="Copy",
                emoji=":clipboard:",
                url=f"https://hc-tcg.fly.dev/?deck={quote(deck_hash)}&name={quote(name)}",
                disabled=hide_hash,
            )
            if hide_hash:
                await ctx.send("This message handily obscures your deck hash!", ephemeral=True)
            await ctx.send(
                embeds=e,
                files=File(im_binary, "deck.png"),
                components=spread_to_rows(delete_button, copy_button),
            )

    @component_callback(re_compile("delete_deck:[0-9]"))
    async def handle_delete(self: "CardExt", ctx: ComponentContext) -> None:
        """Handle the delete button being pressed on the deck info."""
        if str(ctx.author_id) == ctx.custom_id.split(":")[-1]:
            await ctx.message.delete()
            await ctx.send("Deleted!", ephemeral=True)
        else:
            await ctx.send("You can't delete this deck message!", ephemeral=True)

    @card.subcommand()
    @slash_option(
        "card_name", "The card to get", OptionType.STRING, required=True, autocomplete=True
    )
    async def info(self: "CardExt", ctx: SlashContext, card_name: str) -> None:
        """Get information about a card."""
        cards = [
            card for card in self.universe.values() if card_name.lower() in card.rarityName.lower()
        ]
        cards.sort(key=lambda val: val.rarityName)
        if len(cards) > 0:
            card = cards[0]
            if type(card) is HermitCard:  # Special for hermits
                card: HermitCard
                col = TYPE_COLORS[card.hermit_type]
                e = (
                    Embed(
                        title=f"{card.name} ({card.rarity})",
                        description=f"{card.name} ({card.rarity}) - {card.cost} tokens",
                        timestamp=dt.now(tz=timezone.utc),
                        color=rgb_to_int(col),
                    )
                    .add_field("Rarity", card.rarity, inline=True)
                    .add_field(
                        "Primary attack",
                        card.attacks[0]["name"]
                        if card.attacks[0]["power"] is None
                        else card.attacks[0]["name"] + " - " + card.attacks[0]["power"],
                        inline=False,
                    )
                    .add_field("Attack damage", card.attacks[0]["damage"], inline=True)
                    .add_field("Items required", count(card.attacks[0]["cost"]), inline=True)
                    .add_field(
                        "Secondary attack",
                        card.attacks[1]["name"]
                        if card.attacks[1]["power"] is None
                        else card.attacks[1]["name"]
                        + " - "
                        + card.attacks[1]["power"].replace("\n\n", "\n"),
                        inline=False,
                    )
                    .add_field("Attack damage", card.attacks[1]["damage"], inline=True)
                    .add_field("Items required", count(card.attacks[1]["cost"]), inline=True)
                )
            else:
                e = Embed(
                    title=card.name,
                    description=card.description
                    if type(card) is EffectCard
                    else f"{card.hermit_type} item card",
                    timestamp=dt.now(tz=timezone.utc),
                    color=rgb_to_int(TYPE_COLORS[card.hermit_type])
                    if type(card) is not EffectCard
                    else rgb_to_int(beige),
                ).add_field("Rarity", card.rarity, inline=True)
            e.set_thumbnail(f"attachment://{card.text_id}.png")
            e.set_footer("Bot by Tyrannicodin16")
            with BytesIO() as im_binary:
                card.full_image.save(im_binary, "PNG")
                im_binary.seek(0)
                await ctx.send(embeds=e, files=File(im_binary, f"{card.text_id}.png"))
        else:
            await ctx.send("Couldn't find that card!", ephemeral=True)

    @card.subcommand()
    async def reload(self: "CardExt", ctx: SlashContext) -> None:
        """Reload the card data and images."""
        if (
            self.lastReload + 60 * 30 < time()
        ):  # Limit reloading to every 30 minutes as it's quite slow
            await ctx.send("Reloading...", ephemeral=True)
            start_time = time()
            next(self.universe.values()).reload()
            await ctx.send(f"Reloaded! Took {round(time()-start_time)} seconds", ephemeral=True)
            self.lastReload = time()
            return
        await ctx.send(
            "Reloaded within the last 30 minutes, please try again later.", ephemeral=True
        )

    @card.subcommand()
    @slash_option(
        "hermits", "The number of hermits in your deck", OptionType.INTEGER, required=True
    )
    @slash_option(
        "desired_chance",
        "The chance of getting a number of hermits (default 2) on a turn",
        OptionType.INTEGER,
    )
    @slash_option("desired_hermits", "The number of hermits you want", OptionType.INTEGER)
    async def two_hermits(
        self: "CardExt",
        ctx: SlashContext,
        hermits: int,
        desired_chance: int = 50,
        desired_hermits: int = 2,
    ) -> None:
        """View probability to have a number of hermits in your hand after a certain number of draws."""  # noqa: E501
        if hermits < 1 or hermits > 36:
            await ctx.send("Invalid hermit count (1-36)", ephemeral=True)
            return
        plt.figure()
        xs = list(range(35))
        ys = [probability(hermits, i, desired_hermits) * 100 for i in xs]
        surpass = next((idx[0] for idx in enumerate(ys) if idx[1] >= desired_chance), None)
        plt.plot(xs, list(ys))
        plt.xlabel("Draws")
        plt.ylabel("Probability")
        plt.title(
            f"Chance of having {desired_hermits} hermits in your hand after x draws for {hermits} hermits"  # noqa: E501
        )
        plt.grid(visible=True)
        e = Embed(
            title=f"Chance of having {desired_hermits} hermits in your hand after x draws for {hermits} hermits",  # noqa: E501
            timestamp=dt.now(tz=timezone.utc),
            color=rgb_to_int((178, 178, 255)),
        ).add_field("Initial draw chance", f"{ys[0]}%", inline=True)
        if surpass or surpass == 0:
            e.add_field(f"Hits {desired_chance}%", f"{surpass} draw(s)", inline=True)
        else:
            e.add_field(f"Hits {desired_chance}%", "Never", inline=True)
        e.set_footer("Bot by Tyrannicodin | Probability calculations by Allophony")
        e.set_image("attachment://graph.png")
        with BytesIO() as figure_bytes:
            plt.savefig(figure_bytes, format="png")
            figure_bytes.seek(0)
            await ctx.send(embeds=e, files=File(figure_bytes, "graph.png"))
        plt.close()

    @card.subcommand()
    async def chart(self: "CardExt", ctx: SlashContext) -> None:
        """Display the type chart by u/itsNizart."""
        e = (
            Embed(title="Type chart", timestamp=dt.now(tz=timezone.utc))
            .set_image("attachment://typechart.png")
            .set_author(
                "u/itsNizart",
                "https://www.reddit.com/user/itsNizart",
                "https://styles.redditmedia.com/t5_2efni5/styles/profileIcon_jzv50kvrvlb71.png",
            )
            .set_footer("Bot by Tyrannicodin")
        )
        await ctx.send(embeds=e, files=File("typechart.png"))


def setup(client: Client, **kwargs: dict) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord client
    **kwargs (dict): Dictionary containing additional arguments
    """
    return CardExt(client, **kwargs)
