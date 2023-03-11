from pyjson5 import decode
from json import dump
from os import listdir

output = "...\\data"
inp = "..\\datajs"

def getObject(data:str):
    return decode(data.split("super(", 1)[1].split(",\n\t\t})", 1)[0].replace("\n", "").replace("\t", "") + "}")

def main():
    previous = ""
    current = []
    for file in listdir(inp):
        if file.startswith("."): continue
        if not file.split("-", 1)[0] == previous:
            if current != []:
                with open(f"{output}\\{previous}.json", "w") as f:
                    dump(current, f, indent = 4)
            previous = file.split("-", 1)[0]
            current = []
        with open(f"{inp}\\{file}") as f:
            current.append(getObject(f.read()))
    with open(f"{output}\\{previous}.json", "w") as f:
        dump(current, f, indent = 4)

main()