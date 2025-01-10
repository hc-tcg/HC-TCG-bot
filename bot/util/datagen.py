"""Generation of card images."""

from __future__ import annotations

from io import BytesIO
from json import loads
from ssl import SSLContext
from typing import Any

from aiohttp import ClientSession
from PIL import Image

try:
    has_progression = True
    from tqdm import tqdm
except ImportError:
    has_progression = False


TYPE_COLORS = {
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
    "any": (0, 0, 0),
}


def rgb_to_int(rgb: tuple[int, int, int]) -> int:
    """Convert an rgb tuple to an integer.

    Args:
    ----
    rgb (tuple): RGB color to convert
    """
    return (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]


class Card:
    """Basic image generator for a card."""

    def __init__(self: Card, data: dict, generator: DataGenerator) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self._raw_data: dict = data
        self.generator: DataGenerator = generator

        self.text_id: str = data["id"]
        self.category: str = data["category"]

        self.cost: int = data["tokens"]
        self.image_url: str = data["images"]["default"]
        self.token_image_url: str = data["images"]["with-token-cost"]

        self.rarity: str = (
            "Ultra rare" if data["rarity"] == "ultra_rare" else data["rarity"].capitalize()
        )
        self.name: str = data["name"]
        self.rarityName: str = f"{data['name']} ({self.rarity})"


class HermitCard(Card):
    """Image creator for a hermit card."""

    def __init__(self: HermitCard, data: dict, generator: DataGenerator) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        super().__init__(data, generator)

        self.hermit_type: str = data["type"]
        self.health: int = data["health"]
        self.attacks: list[dict[str, Any]] = [data["primary"], data["secondary"]]


class EffectCard(Card):
    """Image creator for an effect card."""

    def __init__(self: EffectCard, data: dict, generator: DataGenerator) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        super().__init__(data, generator)

        self.description = data["description"]


class ItemCard(Card):
    """Image creator for an item card."""

    def __init__(self: ItemCard, data: dict, generator: DataGenerator) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self.energy: list[str] = data["energy"]

        super().__init__(data, generator)


def get_card(data: dict, data_generator: DataGenerator) -> Card:
    """Create a card class of the correct type."""
    if data["category"] == "hermit":
        return HermitCard(data, data_generator)
    if data["category"] == "attach" or data["category"] == "single_use":
        return EffectCard(data, data_generator)
    if data["category"] == "item":
        return ItemCard(data, data_generator)
    invalid_folder = "Invalid category: " + data["category"]
    raise ValueError(invalid_folder)


class DataGenerator:
    """Generate card images for hc-tcg."""

    def __init__(self: DataGenerator, session: ClientSession) -> None:
        """Init generator."""
        self.http_session = session

        self.exclude: list[int] = []

    async def reload_all(self: DataGenerator) -> None:
        """Reload all card information."""
        self.cache: dict[str, Image.Image] = {}
        self.universe: dict[str, Card] = {}

        for card in await self.load_data():
            self.universe[card.text_id] = card

    async def get_image(self: DataGenerator, path: str) -> Image.Image:
        """Get an image from the server.

        Args:
        ----
        path (str): The path to the image
        """
        try:
            url = self.http_session._base_url
            if url:
                path = path.removeprefix(str(url.origin()))
            if not path.startswith("/"):
                path = "/" + path

            if path in self.cache.keys():
                return self.cache[path]
            async with self.http_session.get(path) as response:
                self.cache[path] = Image.open(BytesIO(await response.content.read()))
                if not response.ok:
                    return Image.new("RGBA", (0, 0))
            return self.cache[path]
        except Image.UnidentifiedImageError:
            return Image.new("RGBA", (0, 0))

    async def load_data(self: DataGenerator) -> list[Card]:
        """Load all card data."""
        cards = []
        async with self.http_session.get("cards") as response:
            content = await response.content.read()
            if not response.ok:
                return []

        iterator = loads(content.decode())
        if has_progression:
            iterator = tqdm(iterator, "Loading cards")

        for card in iterator:
            cards.append(get_card(card, self))
        return cards
