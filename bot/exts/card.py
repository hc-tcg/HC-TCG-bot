"""Get information about cards and decks."""

from __future__ import annotations

from asyncio import gather
from collections import Counter
from collections.abc import Iterable
from datetime import datetime as dt
from datetime import timezone
from io import BytesIO
from itertools import islice
from math import ceil, sqrt
from re import compile as re_compile

from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
    SlashContext,
    component_callback,
    global_autocomplete,
    slash_command,
    slash_option,
    spread_to_rows,
)
from matplotlib import pyplot as plt
from PIL import Image

from bot.util import TYPE_COLORS, Card, EffectCard, HermitCard, Server, ServerManager, probability
from bot.util.datagen import ItemCard


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

    def __init__(
        self: CardExt,
        _: Client,
        manager: ServerManager,
        _scheduler: AsyncIOScheduler,
    ) -> None:
        """Get information about cards and decks.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        """
        self.manager: ServerManager = manager

    async def get_stats(
        self: CardExt, server: Server, deck: list[Card]
    ) -> tuple[Image.Image, tuple[int, int, int], dict[str, int], int]:
        """Get information and an image of a deck.

        Args:
        ----
        server (Server): The server the deck comes from
        deck (list): List of card ids in the deck
        """
        type_counts: dict[str, int] = {
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
        cost: int = 0
        hermits, items, effects = ([] for _ in range(3))
        for card in deck:
            if card.category == "item":
                items.append(card)
            elif isinstance(card, HermitCard):
                hermits.append(card)
                if card.text_id in server.data_generator.universe.keys():
                    type_counts[card.hermit_type] += 1
            else:
                effects.append(card)
            cost += card.cost

        hermits.sort(key=lambda x: x.text_id)
        items.sort(key=lambda x: x.text_id)
        effects.sort(key=lambda x: x.text_id)

        width, height = best_factors(len(deck))
        im = Image.new("RGBA", (width * 200, height * 200))

        card_images = await gather(
            *(
                server.data_generator.get_image(card.token_image_url)
                for card in hermits + effects + items
            )
        )
        for i, card_image in enumerate(card_images):
            card_image = card_image.resize((200, 200)).convert("RGBA")
            im.paste(card_image, ((i % width) * 200, (i // width) * 200), card_image)
        return im, (len(hermits), len(effects), len(items)), type_counts, cost

    @global_autocomplete("card_name")
    async def card_autocomplete(self: CardExt, ctx: AutocompleteContext) -> None:
        """Autocomplete a card name."""
        server = self.manager.get_server(ctx.guild_id)
        if not ctx.input_text:
            await ctx.send(
                [card.rarityName for card in take(25, server.data_generator.universe.values())]
            )
            return
        await ctx.send(
            [
                card.rarityName
                for card in server.data_generator.universe.values()
                if ctx.input_text.lower() in card.rarityName.lower()
            ][0:25]
        )

    @slash_command()
    async def card(self: CardExt, _: SlashContext) -> None:
        """Get information about cards and decks."""

    @card.subcommand()
    @slash_option("code", "The deck's export code", OptionType.STRING, required=True)
    @slash_option("hide_hash", "If the deck's hash should be hidden", OptionType.BOOLEAN)
    async def deck(self: CardExt, ctx: SlashContext, code: str, *, hide_hash: bool = False) -> None:
        """Get information about a deck."""
        server = self.manager.get_server(ctx.guild_id)

        deck = await server.get_deck(code)
        if not deck:
            await ctx.send("Invalid deck: Perhaps you're looking for /card info")
            return
        if len(deck["cards"]) > 100:
            await ctx.send(f"A deck of {len(deck["cards"])} cards is too large!", ephemeral=True)
            return

        if hide_hash:
            await ctx.send("This message handily obscures your deck hash!", ephemeral=True)

        col = 0 if len(deck["tags"]) == 0 else int(deck["tags"][0]["color"].lstrip("#"), 16)
        e = Embed(
            title=deck["name"],
            description=None if hide_hash else f"Code: {deck["code"]}",
            timestamp=dt.now(tz=timezone.utc),
            color=col,
        ).add_field("Deck loading", "Please wait")
        message = await ctx.send(embed=e)

        im, card_type_counts, hermit_type_counts, cost = await self.get_stats(
            server, [server.data_generator.universe[card["props"]["id"]] for card in deck["cards"]]
        )
        if len(deck["tags"]) == 0:
            e.color = rgb_to_int(TYPE_COLORS[Counter(hermit_type_counts).most_common()[0][0]])

        e.fields.clear()
        e = (
            e.set_image("attachment://deck.png")
            .add_field("Token cost", str(cost), inline=True)
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
            await message.edit(
                embed=e,
                file=File(im_binary, "deck.png"),
                components=spread_to_rows(delete_button),
            )

    @component_callback(re_compile("delete_deck:[0-9]"))
    async def handle_delete(self: CardExt, ctx: ComponentContext) -> None:
        """Handle the delete button being pressed on the deck info."""
        if str(ctx.author_id) == ctx.custom_id.split(":")[-1]:
            await ctx.message.delete()
            await ctx.send("Deleted!", ephemeral=True)
        else:
            await ctx.send("You can't delete this deck message!", ephemeral=True)

    @card.subcommand()
    @slash_option(
        "card_name",
        "The card to get",
        OptionType.STRING,
        required=True,
        autocomplete=True,
    )
    async def info(self: CardExt, ctx: SlashContext, card_name: str) -> None:
        """Get information about a card."""
        server = self.manager.get_server(ctx.guild_id)
        cards = [
            card
            for card in server.data_generator.universe.values()
            if card_name.lower() in card.rarityName.lower()
        ]
        cards.sort(key=lambda val: val.rarityName)
        if len(cards) > 0:
            card = cards[0]
            if isinstance(card, HermitCard):  # Special for hermits
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
                description: str
                color: tuple[int, int, int]
                if isinstance(card, ItemCard):
                    description = (
                        card.energy[0] + f" x{len(card.energy)}"
                        if len(card.energy)
                        else "" + " item card"
                    )
                    color = TYPE_COLORS[card.energy[0]]
                elif isinstance(card, EffectCard):
                    description = card.description
                    color = beige
                e = Embed(
                    title=card.name,
                    description=description,
                    timestamp=dt.now(tz=timezone.utc),
                    color=rgb_to_int(color),
                ).add_field("Rarity", card.rarity, inline=True)
            e.set_thumbnail(card.token_image_url)
            e.set_footer("Bot by Tyrannicodin16")
            await ctx.send(embeds=e)
        else:
            await ctx.send("Couldn't find that card!", ephemeral=True)

    @card.subcommand()
    @slash_option(
        "hermits",
        "The number of hermits in your deck",
        OptionType.INTEGER,
        required=True,
    )
    @slash_option(
        "desired_chance",
        "The chance of getting a number of hermits (default 2) on a turn",
        OptionType.INTEGER,
    )
    @slash_option("desired_hermits", "The number of hermits you want", OptionType.INTEGER)
    async def two_hermits(
        self: CardExt,
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
    async def chart(self: CardExt, ctx: SlashContext) -> None:
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
        await ctx.send(embeds=e, files=File("resources/typechart.png"))


def setup(
    client: Client,
    manager: ServerManager,
    scheduler: AsyncIOScheduler,
) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord bot client
    manager (ServerManager): The server connection manager
    scheduler (AsyncIOScheduler): Event scheduler
    """
    return CardExt(client, manager, scheduler)
