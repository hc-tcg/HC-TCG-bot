"""Generation of card images."""

from __future__ import annotations

from io import BytesIO
from json import load, loads
from typing import Any, Literal

from aiohttp import ClientResponse, ClientSession
from numpy import array
from PIL import Image, ImageDraw
from PIL.ImageFilter import GaussianBlur

from .card_palettes import Palette, palettes

try:
    has_progression = True
    from tqdm import tqdm
except ImportError:
    has_progression = False


def change_color(
    im: Image.Image, origin: tuple[int, int, int], new: tuple[int, int, int]
) -> Image.Image:
    """Change one color to another in an image.

    Args:
    ----
    im (Image): The target image to change
    origin (tuple): The original color
    new (tuple): The new color
    """
    data = array(im)

    alpha = len(data.T) == 4
    if alpha:
        red, blue, green, _1 = data.T
    else:
        red, blue, green = data.T
    white_areas = (red == origin[0]) & (blue == origin[1]) & (green == origin[2])
    data[..., :3][white_areas.T] = new  # Transpose back needed
    return Image.fromarray(data)


def draw_no_fade(
    image: Image.Image,
    method: str,
    color: tuple[int, int, int],
    *args: tuple,
    **kwargs: dict,
) -> None:
    """Perform an image modification ensuring no fade is made between two colors.

    Args:
    ----
    image (Image): The image to modify
    method (str): The method to perform on the image
    color (tuple): The color of the modification
    *args (tuple): Other method arguments
    **kwargs (dict): Other keyword method arguments
    """
    bw_im = Image.new("1", image.size)
    bw_im_draw = ImageDraw.Draw(bw_im)

    getattr(bw_im_draw, method)(*args, **kwargs, fill=1)

    rgba = array(bw_im.convert("RGBA"))
    rgba[rgba[..., 0] == 0] = [0, 0, 0, 0]  # Convert black to transparrent
    rgba[rgba[..., 0] == 255] = (*color, 255)  # Convert white to desired colour
    image.paste(Image.fromarray(rgba), (0, 0), Image.fromarray(rgba))


def drop_shadow(
    image: Image.Image, radius: int, color: tuple[int, int, int, Literal[0]]
) -> Image.Image:
    """Generate a drop shadow for an image.

    Args:
    ----
    image (Image): The image to create the shaadow for
    radius (int): The size of the shadow in pixels
    color (tuple): The color of the shadow

    Returns:
    -------
    Image containg the drop shadow
    """
    base = Image.new("RGBA", (image.width + radius * 2, image.height + radius * 2), color)
    alpha = Image.new("L", (image.width + radius * 2, image.height + radius * 2))
    alpha.paste(image.getchannel("A"), (radius, radius))
    base.putalpha(alpha.filter(GaussianBlur(radius)))
    return base


class Colors:
    """Usefull colors."""

    WHITE = (255, 255, 255)
    REPLACE = (0, 172, 96)
    REPLACE_2 = (1, 172, 96)
    HEALTH_HI = (124, 205, 17)
    HEALTH_MID = (213, 118, 39)
    HEALTH_LOW = (150, 41, 40)
    SHADOW = (0, 0, 0)


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

        self.palette: Palette = palettes[data["palette"] if "palette" in data.keys() else "base"]


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
            if path not in self.cache.keys():
                async with self.http_session.get(path) as response:
                    self.cache[path] = Image.open(BytesIO(await response.content.read()))
            return self.cache[path]
        except Image.UnidentifiedImageError:
            return Image.new("RGBA", (0, 0))

    async def load_data(self: DataGenerator) -> list[Card]:
        """Load all card data."""
        cards = []
        async with self.http_session.get("cards") as response:
            content = await response.content.read()
        iterator = loads(content.decode())
        if has_progression:
            iterator = tqdm(iterator, "Loading cards")
        for card in iterator:
            cards.append(get_card(card, self))
        return cards
