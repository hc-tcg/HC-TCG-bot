from json import load, dump
from os import listdir

data = r"..\data\hermits"

hermitTypes = {
    "miner": [],
    "terraform": [],
    "speedrunner": [],
    "pvp": [],
    "builder": [],
    "balanced": [],
    "explorer": [],
    "prankster": [],
    "redstone": [],
    "farm":[]
}

for dataFile in listdir(data):
    if dataFile.startswith("."): continue
    with open(f"{data}\\{dataFile}", "r") as f:
        dat:list = load(f)
    for card in dat:
        hermitTypes[card["hermitType"]].append(card["id"])

with open("output.json", "w") as f:
    dump(hermitTypes, f, indent = 4)