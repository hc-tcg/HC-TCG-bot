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


def hex_to_int(hex_str: str) -> int:
    """Convert an hex string to an integer.

    Args:
    ----
    hex_str (tuple): hex color to convert
    """
    return int(hex_str.lstrip("#"), 16)


class Card:
    """Card data."""

    def __init__(self: Card, data: dict) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        """
        self._raw_data: dict = data

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
    """Hermit card data."""

    def __init__(self: HermitCard, data: dict) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        super().__init__(data)

        self.hermit_type: str = data["type"]
        self.health: int = data["health"]
        self.attacks: list[dict[str, Any]] = [data["primary"], data["secondary"]]


class EffectCard(Card):
    """Effect card data."""

    def __init__(self: EffectCard, data: dict) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        super().__init__(data)

        self.description = data["description"]


class ItemCard(Card):
    """Item card data."""

    def __init__(self: ItemCard, data: dict) -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self.energy: list[str] = data["energy"]

        super().__init__(data)


class Achievement:
    """Achievement data."""

    def __init__(self: Achievement, data: dict) -> None:
        """Init achievement.

        Args:
        ----
        data (dict): achievement informtaion
        generator (dict): generator this achievement is part of
        """
        self._raw_data: dict = data

        self.achievement_id: str = data["achievementId"]
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.steps: int = data["steps"]

        self.index: int = data["index"]
        self.max_level: int = data["maxIndex"]
        self.image_url: str | None = None
        self.border_color: str | None = None
        if data["preview"]:
            self.image_url = data["preview"]["image"]
            self.border_color = (
                data["preview"]["borderColor"] if "borderColor" in data["preview"].keys() else None
            )


def get_card(data: dict) -> Card:
    """Create a card class of the correct type."""
    if data["category"] == "hermit":
        return HermitCard(data)
    if data["category"] == "attach" or data["category"] == "single_use":
        return EffectCard(data)
    if data["category"] == "item":
        return ItemCard(data)
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
        self.card_universe: dict[str, Card] = {}
        self.achievement_universe: list[Achievement] = []

        for card in await self.load_cards():
            self.card_universe[card.text_id] = card
        for achievement in await self.load_achievements():
            self.achievement_universe.append(achievement)

    async def get_image(self: DataGenerator, path: str) -> Image.Image:
        """Get an image from the server.

        Args:
        ----
        path (str): The path to the image
        """
        try:
            url = self.http_session._base_url
            if url:
                path = path.removeprefix(str(url.origin())).removeprefix(
                    str(url.origin()).replace("https", "http")
                )
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

    async def load_cards(self: DataGenerator) -> list[Card]:
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
            cards.append(get_card(card))
        return cards

    async def load_achievements(self: DataGenerator) -> list[Achievement]:
        """Load all achievement data."""
        achievements = []
        async with self.http_session.get("achievements") as response:
            content = await response.content.read()
            if not response.ok:
                return []

        iterator = loads(content.decode())
        if has_progression:
            iterator = tqdm(iterator, "Loading achievements")

        for achievement in iterator:
            achievements.append(Achievement(achievement))
        return achievements
