from PIL import Image, ImageDraw, ImageFont
from os import listdir
from json import load
from time import time
import numpy as np
import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

dataPath = r"..\data"
basePath = r"..\base"
generatedPath = "generated"

bangersBold = ImageFont.truetype(f"{basePath}\\fonts\\BangersBold.otf")

class colors:
    WHITE = (255, 255, 255)
    BEIGE = (226, 202, 139)
    BLACK = (0, 0, 0)
    RED = (246, 4, 1)
    REPLACE = (26, 172, 96)

def changeColour(im, origin:tuple[int, int, int], new:tuple[int, int, int]):
    data = np.array(im)
    
    red, blue, green, alpha = data.T
    white_areas = (red == origin[0]) & (blue == origin[1]) & (green == origin[2])
    data[..., :-1][white_areas.T] = new # Transpose back needed
    return Image.fromarray(data)

def all() -> int:
    cards = 0
    for option in options.values():
        if option.__name__ != "all":
            cards += option()
            logging.info(f"Completed {option.__name__}")
    return cards

def base():
    for base in bases:
        base().save(f"{generatedPath}\\backgrounds\\{base.__name__.rsplit('_', 1)[1]}.png")
    return len(bases)

def base_hermit() -> Image.Image:
    im = Image.new("RGBA", (400, 400), colors.WHITE)
    imDraw = ImageDraw.ImageDraw(im, "RGBA")
    imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.BEIGE)
    imDraw.ellipse((305, -5, 405, 95), colors.WHITE)
    imDraw.rectangle((20, 315, 380, 325), colors.WHITE)
    imDraw.rectangle((45, 60, 355, 256), colors.WHITE)
    return im

def base_effect() -> Image.Image:
    im = Image.new("RGBA", (400, 400), colors.BEIGE)
    imDraw = ImageDraw.ImageDraw(im, "RGBA")
    imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.WHITE)

    toPaste = Image.open(f"{basePath}\\other\\star.png")
    toPaste = toPaste.resize((390, int(toPaste.height * (390 / toPaste.width)))).convert("RGBA")
    toPaste = changeColour(toPaste, colors.WHITE, colors.BEIGE)
    im.paste(toPaste, (-15, 65), toPaste)

    imDraw.rounded_rectangle((20, 20, 380, 95), 15, colors.BEIGE)
    font = bangersBold.font_variant(size = 72)
    imDraw.text((200, 33), "EFFECT", colors.WHITE, font, "mt")
    return im

def base_item() -> Image.Image:
    im = Image.new("RGBA", (400, 400), colors.WHITE)
    imDraw = ImageDraw.ImageDraw(im, "RGBA")
    imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.REPLACE) #This is replaced by the type color

    toPaste = Image.open(f"{basePath}\\other\\star.png")
    toPaste = toPaste.resize((390, int(toPaste.height * (390 / toPaste.width)))).convert("RGBA")
    toPaste = changeColour(toPaste, colors.BEIGE, colors.WHITE)
    im.paste(toPaste, (-15, 65), toPaste)

    imDraw.rounded_rectangle((20, 20, 380, 95), 15, colors.WHITE)
    font = bangersBold.font_variant(size = 72)
    imDraw.text((200, 33), "ITEM", colors.BLACK, font, "mt")
    return im

def base_x2() -> Image.Image:
    im = Image.new("RGBA", (100, 100))
    imDraw = ImageDraw.ImageDraw(im, "RGBA")
    imDraw.ellipse((0, 0, 100, 100), colors.WHITE)
    font = bangersBold.font_variant(size = 55)
    imDraw.text((50, 50), "X2", colors.BLACK, font, "mm")
    return im

bases = [base_hermit, base_effect, base_item, base_x2]

def hermits() -> int:
    cards = 0
    for file in listdir(f"{dataPath}\\hermits"):
        if file.startswith("."): continue
        with open(f"{dataPath}\\hermits\\{file}", "r") as f:
            data = load(f)
            cards += len(data)
            [card.save(f"{generatedPath}\\hermits\\{data[i]['id']}.png") for i, card in enumerate(hermit(data))]
    return cards

def hermit(data:dict) -> Image.Image:
    cards = []
    for card in data:
        im = Image.open(f"{generatedPath}\\backgrounds\\hermit.png")
        toPaste = hermit_background(card["id"].rsplit("_")[0])
        im.paste(toPaste, (55, 70), toPaste)

        toPaste = hermit_textOverlay(card)
        im.paste(toPaste, (0, 0), toPaste)
        cards.append(im)

    return cards

def hermit_background(name:str) -> Image.Image:
    im = Image.open(f"{basePath}\\backgrounds\\{name}.png")
    im = im.resize((290, int(im.height * (290 / im.width))), 1)
    toPaste = Image.open(f"{basePath}\\hermits-nobg\\{name}.png")
    toPaste = toPaste.resize((290, int(toPaste.height * (290 / toPaste.width))), 1)
    im.paste(toPaste, (0, 10), toPaste)
    return im

def hermit_textOverlay(data:dict) -> Image.Image:
    im = hermit_textOverlay_topBar(data["name"], data["health"], data["hermitType"], data["rarity"])
    toPaste = hermit_textOverlay_attack(
        [data["primary"].values(), data["secondary"].values()])
    im.paste(toPaste, (0, 0), toPaste)
    return im

def hermit_textOverlay_attack(attacks:list[list[str, list[str], int, object]]) -> Image.Image:
    im = Image.new("RGBA", (400, 400))
    imDraw = ImageDraw.Draw(im)
    font = bangersBold.font_variant(size = 39)
    damageFont = bangersBold.font_variant(size = 45)

    for i, (name, costs, damage, _) in enumerate(attacks):
        yCoord = 272 if i == 0 else 342

        toCenter = Image.new("RGBA", (84, 28))
        for i, cost in enumerate(costs):
            costIm = Image.open(f"{basePath}\\types\\type-{cost}.png").resize((28, 28)).convert("RGBA")
            toCenter.paste(costIm, (i*28, 0), costIm)
        toCenter = toCenter.crop(toCenter.getbbox())
        im.paste(toCenter, (round(62 - toCenter.width / 2), yCoord), toCenter)

        imDraw.text((200, yCoord), name.upper(), colors.BLACK, font, "mt")
        imDraw.text((380, yCoord), str(damage), colors.RED, damageFont, "rt")
    
    return im
    
def hermit_textOverlay_topBar(name:str, health:int, cardType:str, rarity:str) -> Image.Image:
    im = Image.new("RGBA", (400, 400))
    cardTypeIm = Image.open(f"{basePath}\\types\\type-{cardType}.png").resize((68, 68)).convert("RGBA")
    im.paste(cardTypeIm, (327, 12), cardTypeIm)

    if rarity != "common":
        rarityImage = Image.open(f"{basePath}\\rarities\\{rarity}.png").convert("RGBA").resize((60, 60))
        im.paste(rarityImage, (60, 70), rarityImage)

    imDraw = ImageDraw.Draw(im)
    font = bangersBold.font_variant(size = 45)
    imDraw.text((45, 20), name.upper(), colors.BLACK, font, "lt")
    imDraw.text((305, 20), str(health), colors.RED, font, "rt")
    return im

def effects():
    for effect in listdir(f"{basePath}\\effects"):
        im = Image.open(f"{generatedPath}\\backgrounds\\effect.png")
        toPaste = Image.open(f"{basePath}\\effects\\{effect}").convert("RGBA").resize((220, 220))
        im.paste(toPaste, (90, 132), toPaste)
        im.save(f"{generatedPath}\\effects\\{effect}")
    return len(listdir(f"{basePath}\\effects"))

type_colors = {
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

def items() -> int:
    x2 = Image.open(f"{generatedPath}\\backgrounds\\x2.png")
    for card in [typ for typ in listdir(f"{basePath}\\types") if not ("old" in typ or "any" in typ)]:
        cardType = card.split("-")[1].rsplit('.')[0]
        cardIm = Image.open(f"{basePath}\\types\\{card}").convert("RGBA").resize((220, 220))

        im = Image.open(f"{generatedPath}\\backgrounds\\item.png").convert("RGBA")
        im = changeColour(im, colors.REPLACE, type_colors[cardType])
        im.paste(cardIm, (90, 132), cardIm)
        im.save(f"{generatedPath}\\items\\item_{cardType}_common.png")

        im.paste(x2, (300, 300), x2)
        im.save(f"{generatedPath}\\items\\item_{cardType}_rare.png")

    return len(listdir(f"{basePath}\\types\\"))*2

def doNothing() -> int:
    return 0

options = {
    "a": all,
    "b": base,
    "h": hermits,
    "e": effects,
    "i": items,
    "q": doNothing
}

logging.info("Choose option: (a)ll, (h)ermits, (e)ffects, (i)tems, (b)ase, (q)uit")
option = input("> ")
if option in options.keys():
    s = time()
    cards = options[option]()
    logging.info(f"Completed, generated {cards} cards in {round(time() - s, 3)} seconds")
else:
    logging.info("Invalid option, quiting")
input()
