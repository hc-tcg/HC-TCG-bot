"""Generation of card images."""

from base64 import b64decode
from collections import defaultdict
from io import BytesIO
from re import sub
from typing import Any, Optional

from github import ContentFile, Github, Repository
from numpy import array
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFilter import GaussianBlur
from pyjson5 import decode
from requests import get

from .card_palettes import Palette, palettes


def get_func_return(js: str, function_name: str) -> str:
    """Get the return string of a function from a js snippet.

    Args:
    ----
    js (str): The javascript snippet
    function_name (str): The name of the target function
    """
    return js.split(f"{function_name}() " + "{")[1].split("return '")[1].split("'")[0]


def get_json(js: str) -> dict:
    """Get json from a javascript snippet.

    Args:
    ----
    js (str): The javascript snippet
    """
    js = js.replace("`", '"').replace("\t", "")
    try:
        res = ""
        for line in js.split("super(", 1)[1].split("})\n}", 1)[0].split("\n"):
            if not line.startswith("//"):
                res += line.rstrip("\n")
        res = sub(r"\/\*\*[^\*]*\*\/", "", res)  # Remove @satisfies comment
        res = sub(r"[\(\)]", "", res)  # Remove brackets
        data = decode(res + "}")
        data["palette"] = "base"
        if len(js.split("getPalette() {")) > 1:
            data["palette"] = get_func_return(js, "getPalette")
        if data["palette"] == "FAILURE_INVALID_DATA":
            print(data)
            print(js.split("getPalette() {")[1].split("return '")[1])
        data["custom_bg"] = None
        if len(js.split("getBackground() {")) > 1:
            data["custom_bg"] = get_func_return(js, "getBackground")
        return data
    except Exception as e:
        print(e)
        return {}


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
    image: Image.Image, radius: int, color: tuple[int, int, int, 0]
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
    base = Image.new(
        "RGBA", (image.width + radius * 2, image.height + radius * 2), color
    )
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
}


class Card:
    """Basic image generator for a card."""

    def __init__(self: "Card", data: dict, generator: "DataGenerator") -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self._raw_data: dict = data
        self.generator: "DataGenerator" = generator

        self.text_id: str = data["id"]
        self.numeric_id: int = data["numericId"]

        self.name: str = data["name"]

        self.cost: int = data["tokens"]
        self.rarity: str = data["rarity"]

        self.palette: Palette = palettes[data["palette"]]
        self.star: Optional[Image.Image] = None
        self.image = self.render()

    def render(self: "Card") -> Image.Image:
        """Create an image for the card."""
        raise NotImplementedError

    def background(self: "Card") -> Image.Image:
        """Get the background for a card."""

    def get_star(
        self: "Card", color: tuple[int, int, int] = Colors.WHITE
    ) -> Image.Image:
        """Get a star image in any color."""
        im = Image.new("RGBA", (1057, 995))
        im_draw = ImageDraw.Draw(im)
        points = (
            self.generator.repository.get_contents(
                f"client/public/images/star_white.svg", self.generator.branch
            )
            .decoded_content.decode()
            .split('points="')[1]
            .split('"')[0]
            .split(" ")
        )
        im_draw.polygon(
            [
                (round(float(points[i])), round(float(points[i + 1])))
                for i in range(0, len(points), 2)
            ],
            color,
        )
        im = im.resize((400, round((400 / 1057) * 995)), Image.Resampling.NEAREST)
        self.star = im
        return im


class HermitCard(Card):
    """Image creator for a hermit card."""

    def __init__(self: Card, data: dict, generator: "DataGenerator") -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self.custom_bg: str = data["custom_bg"]
        self.hermit_type: str = data["hermitType"]
        self.health: int = data["health"]
        self.attacks: list[dict[str, Any]] = [data["primary"], data["secondary"]]

        super().__init__(data, generator)

    def render(self: "HermitCard") -> Image.Image:
        """Create an image for the card."""
        im = self.background()
        im_draw = ImageDraw.Draw(im)

        feature_image = self.hermit_feature_image()
        im.paste(feature_image, (55, 70), feature_image)  # The hermit background
        font = self.generator.font.font_variant(size=39)  # Two font sizes used in image
        damage_font = self.generator.font.font_variant(size=45)

        for i, attack in enumerate(self.attacks):  # Attacks
            y_coord = 272 if i == 0 else 342

            items = Image.new("RGBA", (84, 28))
            for a, cost in enumerate(attack["cost"]):  # Generate centralised cost image
                item_image = (
                    self.generator.type_images[cost]
                    .resize((28, 28), Image.Resampling.NEAREST)
                    .convert("RGBA")
                )
                items.paste(item_image, (a * 28, 0), item_image)
            items = items.crop(items.getbbox())
            im.paste(items, (round(62 - items.width / 2), y_coord), items)

            im_draw.text(
                (200, y_coord),
                attack["name"].upper(),
                self.palette.SPECIAL_ATTACK
                if attack["power"]
                else self.palette.BASIC_ATTACK,
                font,
                "mt",
            )
            im_draw.text(
                (380, y_coord),
                f"{attack['damage']:02d}",
                self.palette.SPECIAL_DAMAGE
                if attack["power"]
                else self.palette.BASIC_DAMAGE,
                damage_font,
                "rt",
            )  # Ensures always at least 2 digits and is blue if attack is special

        type_image = (
            self.generator.type_images[self.hermit_type]
            .resize((68, 68), Image.Resampling.NEAREST)
            .convert("RGBA")
        )
        im.paste(type_image, (327, 12), type_image)  # The type in top right
        if self.cost > 0:  # No star if it is 0 rarity
            im.paste(
                self.generator.token_stars[self.cost],
                (60, 70),
                self.generator.token_stars[self.cost],
            )

        im_draw.text((45, 20), self.name.upper(), self.palette.NAME, damage_font, "lt")
        im_draw.text(
            (305, 20), str(self.health), self.palette.HEALTH, damage_font, "rt"
        )

        im = im.resize((200, 200), Image.Resampling.NEAREST)
        return im

    def background(self: "HermitCard") -> Image.Image:
        """Get the background for a card."""
        im = Image.new("RGBA", (400, 400), Colors.WHITE)
        im_draw = ImageDraw.Draw(im, "RGBA")
        im_draw.rounded_rectangle(
            (10, 10, 390, 390), 15, self.palette.BACKGROUND
        )  # Creates beige centre with white outline

        im_draw.ellipse((305, -5, 405, 95), self.palette.TYPE_BACKGROUND)  # Type circle
        im_draw.rectangle(
            (20, 315, 380, 325), Colors.WHITE
        )  # White bar between attacks
        im_draw.rectangle((45, 60, 355, 256), Colors.WHITE)  # White border for image

        return im

    def hermit_feature_image(self: "HermitCard") -> Image.Image:
        """Generate a background and character image for a hermit."""
        bg = self.generator.get_image(
            self.text_id.split("_")[0], "backgrounds"
        ).convert("RGBA")
        if bg.size == (0, 0):  # Set background
            bg = self.generator.get_image(self.custom_bg, "backgrounds").convert("RGBA")
        bg = bg.resize(
            (290, int(bg.height * (290 / bg.width))), Image.Resampling.NEAREST
        )
        skin = self.generator.get_image(
            self.text_id.split("_")[0], "hermits-nobg"
        ).convert("RGBA")
        skin = skin.resize(
            (290, int(skin.height * (290 / skin.width))), Image.Resampling.NEAREST
        )
        shadow = drop_shadow(skin, 8, Colors.SHADOW)
        bg.paste(shadow, (-8, -8), shadow)
        bg.paste(skin, (0, 0), skin)
        return bg


class EffectCard(Card):
    """Image creator for an effect card."""

    def __init__(self: "ItemCard", data: dict, generator: "DataGenerator") -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self.description = data["description"]

        super().__init__(data, generator)

    def render(self: "EffectCard") -> Image.Image:
        """Create an image for the card."""
        im = self.background()
        im_draw = ImageDraw.Draw(im)
        if self.cost > 0:
            im_draw.ellipse((0, 302, 100, 402), self.palette.BACKGROUND)  # Rarity icon
            im.paste(
                self.generator.token_stars[self.cost],
                (15, 315),
                self.generator.token_stars[self.cost],
            )
        effect_image = (
            self.generator.get_image(self.text_id, "effects")
            .resize((220, 220), Image.Resampling.NEAREST)
            .convert("RGBA")
        )
        im.paste(effect_image, (90, 132), effect_image)

        im = im.resize((200, 200), Image.Resampling.NEAREST)
        return im

    def background(self: "EffectCard") -> Image.Image:
        """Get the background for a card."""
        im = Image.new("RGBA", (400, 400), self.palette.BACKGROUND)
        im_draw = ImageDraw.Draw(im, "RGBA")
        im_draw.rounded_rectangle((10, 10, 390, 390), 15, Colors.WHITE)

        to_paste = (
            self.get_star(self.palette.BACKGROUND)
            .resize(
                (390, int(self.star.height * (390 / self.star.width))),
                Image.Resampling.NEAREST,
            )
            .convert("RGBA")
        )  # The background star
        im.paste(to_paste, (-15, 65), to_paste)

        im_draw.rounded_rectangle(
            (20, 20, 380, 95), 15, self.palette.BACKGROUND
        )  # The effect header
        font = self.generator.font.font_variant(size=72)
        im_draw.text((200, 33), "EFFECT", Colors.WHITE, font, "mt")

        return im


class ItemCard(Card):
    """Image creator for an item card."""

    def __init__(self: "ItemCard", data: dict, generator: "DataGenerator") -> None:
        """Init card.

        Args:
        ----
        data (dict): card informtaion
        generator (dict): generator this card is part of
        """
        self.hermit_type: str = data["hermitType"]

        super().__init__(data, generator)

    def render(self: "ItemCard") -> Image.Image:
        """Create an image for the card."""
        im = self.background()
        if self.rarity == "rare":
            overlay = self.overlay_x2()
            im.paste(overlay, (0, 302), overlay)
        im = change_color(im, Colors.REPLACE, TYPE_COLORS[self.hermit_type])
        item_image = (
            self.generator.type_images[self.hermit_type]
            .resize((220, 220), Image.Resampling.NEAREST)
            .convert("RGBA")
        )
        im.paste(item_image, (90, 132), item_image)

        im = im.resize((200, 200), Image.Resampling.NEAREST)
        return im

    def background(self: "ItemCard") -> Image.Image:
        """Get the background for a card."""
        im = Image.new("RGBA", (400, 400), Colors.WHITE)
        draw_no_fade(
            im,
            "rounded_rectangle",
            TYPE_COLORS[self.hermit_type],
            (10, 10, 390, 390),
            15,
        )  # This is replaced by the type color

        star_image = (
            self.get_star()
            .resize(
                (390, int(self.get_star().height * (390 / self.get_star().width))),
                Image.Resampling.NEAREST,
            )
            .convert("RGBA")
        )  # The background star
        im.paste(star_image, (-15, 65), star_image)

        draw_no_fade(
            im, "rounded_rectangle", Colors.WHITE, (20, 20, 380, 95), 15
        )  # The item header
        font = self.generator.font.font_variant(size=72)
        draw_no_fade(
            im, "text", self.palette.NAME, (200, 33), "ITEM", font=font, anchor="mt"
        )
        return im

    def overlay_x2(self: "ItemCard") -> Image.Image:
        """Create an image that contains the rarity star and 2x text for a 2x item."""
        im = Image.new(
            "RGBA", (400, 100)
        )  # Only 100 tall as it's just the two bottom circles
        im_draw = ImageDraw.Draw(im, "RGBA")

        im_draw.ellipse((0, 0, 100, 100), Colors.WHITE)  # Rarity star circle
        im.paste(self.generator.token_stars[2], (15, 15), self.generator.token_stars[2])

        im_draw.ellipse((302, 0, 402, 100), Colors.WHITE)  # x2 text
        font = self.generator.font.font_variant(size=55)
        im_draw.text((351, 50), "X2", self.palette.NAME, font, "mm")

        return im


def get_card(data: dict, data_generator: "DataGenerator", folder_name: str) -> Card:
    """Create a card class of the correct type."""
    if folder_name == "hermits":
        return HermitCard(data, data_generator)
    if folder_name == "effects" or folder_name == "single-use":
        return EffectCard(data, data_generator)
    if folder_name == "items":
        return ItemCard(data, data_generator)
    invalid_folder = "Invalid folder name: " + folder_name
    raise ValueError(invalid_folder)


class DataGenerator:
    """Generate card images for hc-tcg."""

    def __init__(
        self: "DataGenerator",
        github_token: str,
        repository: str = "martinkadlec0/hc-tcg",
        branch: str = "master",
        font: ImageFont.FreeTypeFont = None,
    ) -> None:
        """Init generator.

        Args:
        ----
        github_token (str): The token to access the github repository
        repository (str): Optional, the repository to access
        branch (str): Optional, the branch on the repository to use
        font (FreeTypeFont): Optional, the font to use for cards
        """
        if font is None:
            font = ImageFont.truetype("BangersBold.otf")
        self.token: str = github_token
        self.github: Github = Github(github_token)
        self.repository: Repository.Repository = self.github.get_repo(repository)
        self.branch: str = branch
        self.font: ImageFont.FreeTypeFont = font

        self.exclude: list[int] = []

        self.reload_all()

    def reload_all(self: "DataGenerator") -> None:
        """Reload all card information."""
        self.cache: dict[str, Any] = {}
        self.universe: dict[str, Card] = {}

        self.token_costs, self.token_stars = self.load_tokens()
        self.type_images = self.load_types()
        self.healths = self.get_health_cards()

        for card in self.load_data():
            self.universe[card.text_id] = card

    def get_image(self: "DataGenerator", name: str, sub_dir: str = "") -> Image.Image:
        """Get an image from the github source.

        Args:
        ----
        name (str): The image name
        sub_dir (str): Optional, the sub directory the image is in
        """
        if sub_dir not in self.cache.keys():
            self.cache[sub_dir] = self.repository.get_contents(
                f"client/public/images/{sub_dir}", self.branch
            )
        found_file = next(
            (file for file in self.cache[sub_dir] if file.name == f"{name}.png"), None
        )
        return (
            Image.open(BytesIO(found_file.decoded_content))
            if found_file
            else Image.new("RGBA", (0, 0))
        )

    def load_tokens(self: "DataGenerator") -> (defaultdict, list[Image.Image]):
        """Get token costs and token star images."""
        token_costs: defaultdict = defaultdict(
            int,
            decode(
                self.repository.get_contents(
                    "common/config/ranks.json", self.branch
                ).decoded_content.decode()
            ),
        )
        token_stars: list[Image.Image] = [0 for _ in range(len(token_costs["ranks"]))]
        for star, token_value in token_costs.pop("ranks").items():
            token_stars[token_value[0]] = self.get_image(star, "ranks").resize(
                (70, 70), Image.Resampling.NEAREST
            )
        return token_costs, token_stars

    def load_types(self: "DataGenerator") -> dict[str, Image.Image]:
        """Get all type images."""
        type_images: dict[str, Image.Image] = {}
        for file in self.repository.get_contents(
            f"client/public/images/types", self.branch
        ):
            file: ContentFile.ContentFile = file
            type_images[file.name.split("-")[1].split(".")[0]] = Image.open(
                BytesIO(file.decoded_content)
            )
        return type_images

    def load_data(self: "DataGenerator") -> list[Card]:
        """Load all card data."""
        cards = []
        for card_dir in self.repository.get_contents("common/cards", self.branch):
            card_dir: ContentFile.ContentFile
            if card_dir.type != "dir" or card_dir.name == "base":
                continue  # Ignore if file
            cards += self.process_git_url(card_dir.git_url, card_dir.name)
        return cards

    def process_git_url(self: "DataGenerator", url: str, name: str) -> list[Card]:
        """Get cards and folders from a git page.

        Args:
        ----
        url (str): The url to process
        name (str): The name of the folder this page is in, for getting card types
        """
        dir_data = get(
            url, headers={"Authorization": f"Bearer {self.token}"}, timeout=5
        ).json()
        cards = []
        for file in dir_data["tree"]:
            file: dict
            if file["path"] == "index.ts":
                continue
            if file["type"] == "tree":
                cards += self.process_git_url(file["url"], file["path"])
            elif file["type"] == "blob":
                file_data: dict = get_json(
                    b64decode(
                        get(
                            file["url"],
                            headers={"Authorization": f"Bearer {self.token}"},
                            timeout=5,
                        ).json()["content"]
                    ).decode()
                )
                if file_data["numericId"] in self.exclude:
                    continue
                file_data["tokens"] = self.token_costs[file_data["id"]]
                cards.append(get_card(file_data, self, name))
        return cards

    def get_health_cards(self: "DataGenerator") -> list[Image.Image]:
        """Get health cards for red, orange and green health."""
        base = Image.new("RGBA", (400, 400), Colors.WHITE)

        draw_no_fade(base, "ellipse", Colors.REPLACE, (-5, 130, 405, 380))
        draw_no_fade(base, "rounded_rectangle", Colors.REPLACE, (20, 20, 380, 95), 15)
        font = self.font.font_variant(size=72)
        draw_no_fade(
            base,
            "text",
            palettes["base"].NAME,
            (200, 33),
            "HEALTH",
            font=font,
            anchor="mt",
        )
        base.resize((200, 200), Image.Resampling.NEAREST)

        health_cards: list[Image.Image] = []
        for color in [Colors.HEALTH_LOW, Colors.HEALTH_MID, Colors.HEALTH_HI]:
            health_cards.append(change_color(base, Colors.REPLACE, color))
        return health_cards
