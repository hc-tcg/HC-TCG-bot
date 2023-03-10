from math import log2
from typing import Callable, Iterable
from PIL import Image, ImageDraw, ImageFont

Color = tuple[int, int, int]

def mean(values:Iterable) -> float:
    return sum(values)/len(values)

class colors:
    GRAY = (72, 72, 72, 255)
    CYAN = (30, 126, 133, 255)
    WHITE = (255, 255, 255, 255)

class brackets:
    FONT = ImageFont.truetype("Helvetica.ttf", size=10)

    boxHeight = 50
    boxWidth = 100
    paddingY = 20
    paddingX = 20

    def __init__(self, players: list[str]):
        n = len(players)
        self.layerCount = log2(n)
        if not self.layerCount.is_integer():
            raise NotImplementedError("Players must be a power of 2")
        self.layerCount = int(self.layerCount)

        self.layer = [(players[i], players[i + 1]) for i in range(0, n, 2)]
        self.nextPlayers = ["" for _ in range(len(self.layer))]
        self.layers = []

    def declareWinner(self, winner: int):
        for i, tup in enumerate(self.layer):
            if winner in tup:
                self.nextPlayers[i] = winner
                break

        completedPlayers = len([num for num in self.nextPlayers if num != ""])
        if len(self.layer) == completedPlayers:
            if completedPlayers == 1:
                self.layers.append(self.layer)
                self.layer = winner
                self.layers.append([self.layer])
                return
            self.layers.append(self.layer)
            self.layer = [(self.nextPlayers[i], self.nextPlayers[i + 1])
                                        for i in range(0, len(self.nextPlayers), 2)]
            self.nextPlayers = [0 for _ in range(len(self.layer))]

    def newLineText(self, text:str):
        line = ""
        final = ""
        for char in text:
            if self.FONT.getsize(line + char)[0] > self.boxWidth:
                final += line + "\n"
                line = ""
            else:
                line += char
        return final + line
    
    def createRect(self, text:str, color:Color, textCol:Color) -> Image.Image:
        im = Image.new("RGBA", (self.boxWidth, self.boxHeight))
        imDraw = ImageDraw.Draw(im)
        imDraw.rounded_rectangle(((0,0), im.size), 15, color)
        imDraw.multiline_text((im.width//2, im.height//2), self.newLineText(text), textCol, self.FONT, "mm", align="center")
        return im

    def render(self, bg:Color = colors.GRAY, fg:Color = colors.CYAN, text:Color = colors.WHITE, lines:Color = colors.WHITE, converter:Callable[..., str] = lambda x: str(x)) -> Image.Image:
        im = Image.new("RGBA", ((self.layerCount+1)*(self.boxWidth+self.paddingX), 2**self.layerCount*(self.boxHeight+self.paddingY)), bg)
        imDraw = ImageDraw.Draw(im, "RGBA")
        layers = [self.layers[i] if i < len(self.layers) else ["" for _ in range(2**i)] for i in range(self.layerCount+1)]
        connections = []
        for l, layer in enumerate(layers):
            if l == self.layerCount:
                toPaste = self.createRect(converter(layer[0]), fg, text)
                im.paste(toPaste, (l*(self.boxWidth+self.paddingX), connections[0]), toPaste)
                continue
            for i, pair in enumerate(layer):
                toPaste = self.createRect(converter(pair[0]), fg, text)
                toPaste2 = self.createRect(converter(pair[1]), fg, text)

                tl1 = i*2*(self.boxHeight+self.paddingY) if len(connections)/2 != len(layer) else connections[i]
                tl2 = (i*2+1)*(self.boxHeight+self.paddingY) if len(connections)/2 != len(layer) else connections[i+1]
                avgPos = int(mean((tl1, tl2)))
                if i == 0: connections = []
                connections.append(avgPos)

                imDraw.line((l*(self.boxWidth+self.paddingX)+self.boxWidth, tl1+self.boxHeight//2,
                             l*(self.boxWidth+self.paddingX)+self.boxWidth+self.paddingX//2, tl1+self.boxHeight//2,
                             l*(self.boxWidth+self.paddingX)+self.boxWidth+self.paddingX//2, tl2+self.boxHeight//2,
                             l*(self.boxWidth+self.paddingX)+self.boxWidth, tl2+self.boxHeight//2), lines, 5, "curve")
                imDraw.line((l*(self.boxWidth+self.paddingX)+self.boxWidth+self.paddingX//2, avgPos+self.boxHeight//2,
                             (l+1)*(self.boxWidth+self.paddingX), avgPos+self.boxHeight//2), lines, 5, "curve")
                im.paste(toPaste, (l*(self.boxWidth+self.paddingX), tl1), toPaste)
                im.paste(toPaste2, (l*(self.boxWidth+self.paddingX), tl2), toPaste2)
        finalIm = Image.new("RGBA", ((self.layerCount+1)*(self.boxWidth+self.paddingX)+self.paddingX, 2**self.layerCount*(self.boxHeight+self.paddingY)+self.paddingY), bg)
        finalIm.paste(im, (self.paddingX, self.paddingY), im)
        return finalIm


bracket = brackets(
        [str(547104418131083285), str(653597113401212960), str(171689337954500608), str(805585561376784434)])
bracket.declareWinner(str(547104418131083285))
bracket.declareWinner(str(171689337954500608))
bracket.declareWinner(str(547104418131083285))

bracket.render().save("image.png")
