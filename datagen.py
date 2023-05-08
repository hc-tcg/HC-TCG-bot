from pyjson5 import decode
from json import dump
from github import Github, Repository, ContentFile
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from numpy import array

def jsToJson(js:str):
    try:
        res = ""
        for line in js.split("super(", 1)[1].split(",\n\t\t})", 1)[0].split("\n"):
            line = line.replace("\t", "").replace("\n", "")
            if not line.startswith("//"):
                res += line
        return decode(res+"}")
    except:
        print(js)
        return {}

def changeColour(im, origin:tuple[int, int, int], new:tuple[int, int, int]):
    data = array(im)
    
    red, blue, green, alpha = data.T
    white_areas = (red == origin[0]) & (blue == origin[1]) & (green == origin[2])
    data[..., :-1][white_areas.T] = new #Transpose back needed
    return Image.fromarray(data)

class colors:
    WHITE = (255, 255, 255)
    BEIGE = (226, 202, 139)
    BLACK = (0, 0, 0)
    RED = (246, 4, 1)
    GREEN = (124, 205, 17)
    ORANGE = (213, 118, 39)
    RED_HEALTH = (150, 41, 40)
    REPLACE = (26, 172, 96)
    SPECIAL_BLUE = (23, 66, 234)

    RARITY_TEXT = [
        (114, 111, 109),
        (149, 142, 49),
        (52, 134, 71),
        (42, 124, 138),
        (177, 173, 169)]
    
    TYPES = {
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

RARITY_NAMES = ["iron", "gold", "emerald", "diamond", "netherite"]

def hexToRGB(hex:str) -> tuple:
    num = int(hex, 16)
    r = num >> 16
    g = (num - (r << 16)) >> 8
    b = (num - (r << 16) - (g << 8))
    return (r, g, b)

class dataGetter:
    def __init__(self,
                 token:str,
                 repo:str="martinkadlec0/hc-tcg",
                 #saveData:dict[str, str]={"root": "cardData", "cardData":"data"},
                 font:ImageFont.FreeTypeFont=ImageFont.truetype("BangersBold.otf"),
                 ) -> None:
        
        self.g = Github(token)
        self.repo:Repository.Repository = self.g.get_repo(repo)
        #self.saveLocations = saveData

        self.universes:dict[str, list] = {}
        self.universeData:dict[str, dict] = {}
        self.universeImage:dict[str, Image.Image] = {}
        self.tempImages:dict[str, Image.Image] = {}
        self.rarities = {}

        #Image stuff
        self.font = font
        self.reload()
    
    def get_rarities(self):
        self.rarities = decode(self.repo.get_contents("config/ranks.json").decoded_content.decode())
        self.rarities["dream_rare"] = 5
    
    def loadData(self) -> None:
        for card_dir in self.repo.get_contents("server/cards/card-plugins"):
            if "." in card_dir.name: continue #Ignore if file
            cards = []
            for file in self.repo.get_contents(f"server/cards/card-plugins/{card_dir.name}"):
                if file.name.startswith("_") or "index" in file.name: continue #Ignore index and class definition
                dat = jsToJson(file.decoded_content.decode())
                self.universeData[dat["id"]] = dat
                cards.append(dat["id"])
            self.universes[card_dir.name] = cards
    
    def getImage(self, name:str, subDir:str="") -> Image.Image:
        imBytes =  BytesIO(self.repo.get_contents(f"client/public/images/{subDir}{'/' if subDir else ''}{name}.png").decoded_content)
        return Image.open(imBytes)

    def getStar(self) -> Image.Image:
        im = Image.new("RGBA", (1057, 995))
        imDraw = ImageDraw.Draw(im)
        points = self.repo.get_contents(f"client/public/images/star_white.svg").decoded_content.decode().split("points=\"")[1].split("\"")[0].split(" ")
        imDraw.polygon([(round(float(points[i])), round(float(points[i+1]))) for i in range(0, len(points), 2)], colors.WHITE)
        return im

    def getRarityStars(self) -> list[Image.Image]:
        images = []
        font = self.font.font_variant(size=40)
        for i, rarity in enumerate(RARITY_NAMES):
            im = self.getImage(rarity, "ranks").resize((70, 70))
            imDraw = ImageDraw.Draw(im)
            imDraw.text((32, 39), str(i+1), colors.RARITY_TEXT[i], font, "mm")
            images.append(im)
        return images

    def reload(self) -> None:
        self.tempImages["star"] = self.getStar() #Run these before to get info and base images
        self.tempImages["rarity_stars"] = self.getRarityStars()
        self.get_rarities()
        self.type_images()
        self.loadData()

        self.tempImages.update({ #Base images
            "base_hermit": self.base_hermit(),
            "base_item": self.base_item(),
            "base_item_x2": self.base_item(),
            "base_effect": self.base_effect(),
        })
        x2Overlay = self.overlay_x2() #Add the overlay to x2 items
        self.tempImages["base_item_x2"].paste(x2Overlay, (0, 302), x2Overlay)

        for hermit in self.universes["hermits"]: #Go through each hermit and generate an image
            if not hermit.split("_")[0] in self.tempImages.keys():
                self.tempImages[hermit.split("_")[0]] = self.hermitFeatureImage(hermit.split("_")[0])
            dat = self.universeData[hermit]
            self.universeImage[hermit] = self.hermit(dat["name"], hermit.split("_")[0], dat["health"], self.rarities[hermit] if hermit in self.rarities.keys() else 0, dat["hermitType"], (dat["primary"], dat["secondary"]))
        
        for effect in self.universes["effects"]:
            self.universeImage[effect] = self.effect(effect, self.rarities[effect] if effect in self.rarities.keys() else 0)
        
        for single_use in self.universes["single-use"]:
            self.universeImage[single_use] = self.effect(single_use, self.rarities[single_use] if single_use in self.rarities.keys() else 0)
        
        for item in self.universes["items"]:
            self.universeImage[item] = self.item(item.split('_')[1], item.split('_')[2]=="rare")

    def base_hermit(self) -> Image.Image:
        im = Image.new("RGBA", (400, 400), colors.WHITE)
        imDraw = ImageDraw.Draw(im, "RGBA")
        imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.BEIGE) #Creates beige centre with white outline

        imDraw.ellipse((305, -5, 405, 95), colors.WHITE) #Type circle
        imDraw.rectangle((20, 315, 380, 325), colors.WHITE) #White bar between attacks
        imDraw.rectangle((45, 60, 355, 256), colors.WHITE) #White border for image

        return im

    def base_item(self) -> Image.Image: #Generates the background for all items, the icon is pasted on top
        im = Image.new("RGBA", (400, 400), colors.WHITE)
        imDraw = ImageDraw.Draw(im, "RGBA")
        imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.REPLACE) #This is replaced by the type color

        starImage = self.tempImages["star"].resize(
            (390, int(self.tempImages["star"].height * (390 / self.tempImages["star"].width)))).convert("RGBA") #The background star
        starImage = changeColour(starImage, colors.BEIGE, colors.WHITE)
        im.paste(starImage, (-15, 65), starImage)

        imDraw.rounded_rectangle((20, 20, 380, 95), 15, colors.WHITE) #The item header
        font = self.font.font_variant(size = 72)
        imDraw.text((200, 33), "ITEM", colors.BLACK, font, "mt")
        return im

    def overlay_x2(self) -> Image.Image: #Additional parts for a 2x item
        im = Image.new("RGBA", (400, 100)) #Only 100 tall as it's just the two bottom circles
        imDraw = ImageDraw.Draw(im, "RGBA")

        imDraw.ellipse((0, 0, 100, 100), colors.WHITE) #Rarity star circle
        im.paste(self.tempImages["rarity_stars"][1], (15, 15), self.tempImages["rarity_stars"][1])

        imDraw.ellipse((302, 0, 402, 100), colors.WHITE) #x2 text
        font = self.font.font_variant(size = 55)
        imDraw.text((351, 50), "X2", colors.BLACK, font, "mm")

        return im
    
    def base_effect(self) -> Image.Image: #Generates the background for all effects, the icon is pasted on top (could maybe be compacted with item bg)
        im = Image.new("RGBA", (400, 400), colors.BEIGE)
        imDraw = ImageDraw.Draw(im, "RGBA")
        imDraw.rounded_rectangle((10, 10, 390, 390), 15, colors.WHITE)

        toPaste = self.tempImages["star"].resize((390, int(self.tempImages["star"].height * (390 / self.tempImages["star"].width)))).convert("RGBA") #The background star
        toPaste = changeColour(toPaste, colors.WHITE, colors.BEIGE)
        im.paste(toPaste, (-15, 65), toPaste)

        imDraw.rounded_rectangle((20, 20, 380, 95), 15, colors.BEIGE) #The effect header
        font = self.font.font_variant(size = 72)
        imDraw.text((200, 33), "EFFECT", colors.WHITE, font, "mt")

        return im
    
    def type_images(self) -> None: #Gets all type images
        for file in self.repo.get_contents(f"client/public/images/types"):
            file:ContentFile.ContentFile = file
            self.tempImages[file.name.split('.')[0]] = Image.open(BytesIO(file.decoded_content))

    def hermitFeatureImage(self, hermitName:str) -> Image.Image:
        bg = self.getImage(hermitName, "backgrounds").convert("RGBA")
        bg = bg.resize((290, int(bg.height * (290 / bg.width))))
        skin = self.getImage(hermitName, "hermits-nobg").convert("RGBA")
        skin = skin.resize((290, int(skin.height * (290 / skin.width))))
        bg.paste(skin, (0, 10), skin)
        return bg

    def hermit(self,
               name:str, #Hermit name on top of card
               imageName:str, #Name of images related to hermit (id without the rarity)
               health:int, #Max health
               rarity:int,
               hermitType:str, #Type shown in 
               attacks:tuple[dict, dict], #Attack information
               ) -> Image.Image:
        im = self.tempImages["base_hermit"].copy()
        imDraw = ImageDraw.Draw(im)

        im.paste(self.tempImages[imageName], (55, 70), self.tempImages[imageName]) #The hermit background
        font = self.font.font_variant(size = 39) #Two font sizes used in image
        damageFont = self.font.font_variant(size = 45)

        for i in range(len(attacks)): #Attacks
            yCoord = 272 if i == 0 else 342

            toCenter = Image.new("RGBA", (84, 28))
            for a, cost in enumerate(attacks[i]["cost"]): #Generate centralised cost image
                costIm = self.tempImages[f"type-{cost}"].resize((28, 28)).convert("RGBA")
                toCenter.paste(costIm, (a*28, 0), costIm)
            toCenter = toCenter.crop(toCenter.getbbox())
            im.paste(toCenter, (round(62 - toCenter.width / 2), yCoord), toCenter)

            imDraw.text((200, yCoord), attacks[i]['name'].upper(), colors.BLACK, font, "mt")
            imDraw.text((380, yCoord), f"{attacks[i]['damage']:02d}", colors.SPECIAL_BLUE if attacks[i]['power'] else colors.RED, damageFont, "rt")
            #Ensures always at least 2 digits and is blue if attack is special

        cardTypeIm = self.tempImages[f"type-{hermitType}"].resize((68, 68)).convert("RGBA")
        im.paste(cardTypeIm, (327, 12), cardTypeIm) #The type in top right
        if rarity > 0: #No star if it is 0 rarity
            im.paste(self.tempImages["rarity_stars"][rarity-1], (60, 70), self.tempImages["rarity_stars"][rarity-1])
        
        imDraw.text((45, 20), name.upper(), colors.BLACK, damageFont, "lt")
        imDraw.text((305, 20), str(health), colors.RED, damageFont, "rt")

        return im
    
    def effect(self, imageName:str, rarity:int):
        im = self.tempImages["base_effect"].copy()
        imDraw = ImageDraw.Draw(im)
        if rarity > 0:
            imDraw.ellipse((0, 302, 100, 402), colors.BEIGE) #Rarity icon
            im.paste(self.tempImages["rarity_stars"][rarity-1], (15, 315), self.tempImages["rarity_stars"][rarity-1])
        effectImage = self.getImage(imageName, "effects").resize((220, 220)).convert("RGBA")
        im.paste(effectImage, (90, 132), effectImage)
        return im
    
    def item(self, typeName:str, x2:bool):
        im = self.tempImages["base_item"].copy()
        if x2:
            im = self.tempImages["base_item_x2"].copy()
        im = changeColour(im, colors.REPLACE, colors.TYPES[typeName])
        itemImage = self.getImage(f"type-{typeName}", "types").resize(
            (220, 220)).convert("RGBA")
        im.paste(itemImage, (90, 132), itemImage)
        return im