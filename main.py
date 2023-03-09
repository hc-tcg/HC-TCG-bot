from interactions import Client, CommandContext, Permissions, Button, Embed, ButtonStyle, Member, Color, File, option, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pickle import Pickler, Unpickler, UnpicklingError
from dateutil.parser.isoparser import isoparse
from io import BytesIO
from PIL import Image
from time import time

from tournamentGuild import tournamentGuild
from deck import hashToStars, hashToDeck, universe

bot = Client()
scheduler = AsyncIOScheduler()

setupreason = "Setup server for tournaments"

test_guild = 1080579441790566450

guilds:list[tournamentGuild] = []

setupServerButton = Button(
    style = ButtonStyle.PRIMARY,
    label = "Setup server",
    custom_id = "setupServerButton",
)

@bot.event
async def on_start():
    global guilds
    try:
        with open("save.pkl", "rb") as f:
            guilds = [await tournamentGuild.deserialize(bot, scheduler, tournament) for tournament in Unpickler(f).load()]
    except (UnpicklingError, FileNotFoundError, EOFError):
        pass

#event = await self.guild.create_scheduled_event(
#            name,
#            EntityType.EXTERNAL,
#            dt.fromtimestamp(startTime).isoformat(),
#            channel_id = self.announement,
#            description = f"{host.name} is hosting a tournament: {name}\nMax players: {maxPlayers}",)

def checkSetup(_id:int):
    return any(int(x.guild.id) == _id for x in guilds)

@bot.command(
    name = "setup",
    description = "Prepare a server for hosting tournaments",
    default_member_permissions = Permissions.ADMINISTRATOR,
    scope = test_guild,
)
@bot.component(setupServerButton)
async def setupServer(ctx: CommandContext,):
    if checkSetup(int(ctx.guild.id)):
        await ctx.send("Already setup!", ephemeral = True)
        return
    tournamentObj = tournamentGuild(bot, ctx.guild, scheduler)
    await tournamentObj.setup()
    guilds.append(tournamentObj)
    await ctx.author.add_role(tournamentObj.host)
    botMember:Member = await get(bot, Member, object_id = bot.me.id, guild_id = ctx.guild.id)
    await botMember.add_role(tournamentObj.host)
    await ctx.send("Server setup!", ephemeral=True)

@bot.command(
    name = "deck",
    description = "All about decks!",
    scope = test_guild,
)
async def deck(ctx:CommandContext):
    pass

typeColors = {
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

hermitTypes = {
    "miner": [
        "hypnotizd_rare",
        "tinfoilchef_common",
        "tinfoilchef_rare",
        "tinfoilchef_ultra_rare"
    ],
    "terraform": [
        "geminitay_rare",
        "goodtimeswithscar_common",
        "keralis_rare",
        "pearlescentmoon_rare"
    ],
    "speedrunner": [
        "cubfan135_rare",
        "ijevin_rare"
    ],
    "pvp": [
        "ethoslab_ultra_rare",
        "falsesymmetry_common",
        "welsknight_rare",
        "xbcrafted_common"
    ],
    "builder": [
        "bdoubleo100_common",
        "falsesymmetry_rare",
        "geminitay_common",
        "goodtimeswithscar_rare",
        "grian_common",
        "keralis_common",
        "pearlescentmoon_common",
        "rendog_rare",
        "stressmonster101_common",
        "vintagebeef_rare",
        "welsknight_common"
    ],
    "balanced": [
        "bdoubleo100_rare",
        "cubfan135_common",
        "ethoslab_common",
        "hypnotizd_common",
        "iskall85_common",
        "rendog_common",
        "vintagebeef_common"
    ],
    "explorer": [
        "ijevin_common",
        "joehills_common",
        "vintagebeef_ultra_rare",
        "xbcrafted_rare",
        "zedaphplays_rare"
    ],
    "prankster": [
        "grian_rare",
        "mumbojumbo_rare",
        "stressmonster101_rare"
    ],
    "redstone": [
        "docm77_common",
        "ethoslab_rare",
        "impulsesv_rare",
        "mumbojumbo_common",
        "tangotek_common",
        "xisumavoid_rare",
        "zedaphplays_common"
    ],
    "farm": [
        "docm77_rare",
        "impulsesv_common",
        "iskall85_rare",
        "joehills_rare",
        "tangotek_rare",
        "xisumavoid_common"
    ]
}

def getStats(deck):
    typeCounts = {
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

    im = Image.new("RGBA", (6*200, 7*200))
    hermits = items = effects = 0
    for i, card in enumerate(deck):
        card:str = card
        cId:str = card.rstrip(".png")
        if cId.startswith("item"):
            items += 1
        elif cId.endswith(("rare", "common", "commo")): #"commo" is for tfc common card
            hermits += 1
            for cardType, hermitList in hermitTypes.items():
                if cId in hermitList:
                    typeCounts[cardType] += 1
                    break
        else:
            effects += 1

        toPaste = Image.open(f"staticImages\\{card}.png").resize((200, 200)).convert("RGBA")
        im.paste(toPaste, ((i%6)*200,(i//6)*200), toPaste)
    return im, (hermits, items, effects), typeCounts

def getLongest(x:dict):
    return [k for k in x.keys() if x.get(k)==max([n for n in x.values()])]

@deck.subcommand(
    name = "show",
    description = "sends an embed with information about the hash",
)
@option("The deck hash")
@option("If the deck image should be a gif or static")
async def showDeck(ctx:CommandContext, deck:str, animate_deck:bool=False):
    deckList = hashToDeck(deck, universe)
    image, hic, typeCounts = getStats(deckList)
    col = typeColors[getLongest(typeCounts)[0]]
    e = Embed(
        title = "Deck stats",
        description = f"Hash: {deck}",
        color = (col[0] << 4) + (col[1] << 2) + (col[2])
    )
    e.set_image("attachment://deck.png")
    e.add_field("Stars", str(hashToStars(deck)), True)
    e.add_field("HEI ratio", f"{hic[0]}:{hic[2]}:{hic[1]}", True)
    e.add_field("Types", len([typeList for typeList in typeCounts.values() if typeList != []]), True)
    with BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(embeds=e, files=File(fp=image_binary, filename='deck.png'))

@bot.command(
    name = "tournament",
    description = "Base command for tournament",
    scope = test_guild,
)
async def tournament(ctx:CommandContext):
    pass

@tournament.subcommand(
    name = "create",
    description = "Create a tournament",
)
@option(
    description = "The name of the tournament",
)
@option(
    description = "The date and time of the tournament start in ISO",
)
@option(
    description = "The maximum numbers of players in the tournament",
)
@option(
    description = "A description to display in the announcement channel"
)
async def start(ctx:CommandContext, name:str, datetime:str, max_players:int, description:str = ""):
    guild = next((x for x in guilds if x.guild.id == ctx.guild.id), None)
    if not guild:
        await ctx.send("Server not setup for tournaments", components = [setupServerButton], ephemeral = True)
        return
    if int(guild.host.id) in ctx.author.roles:
        try:
            timeStamp = isoparse(datetime).timestamp()
            if timeStamp < time():
                await ctx.send("Start time is in the past", ephemeral = True)
        except ValueError:
            await ctx.send("Invalid ISO date format", ephemeral = True)
            return
        await guild.createTournament(name, ctx.member, timeStamp, max_players, description)
        await ctx.send("Creating tournament", ephemeral = True)
        return
    await ctx.send("You must have the tournament host role to start a tournament", ephemeral = True)

@tournament.subcommand(
    name = "join",
    description = "join a tournament"
)
@option(
    description = "The name of the tournament"
)
async def joinTournament(ctx:CommandContext, name:str):
    guild = next((x for x in guilds if x.guild.id == ctx.guild.id), None)
    if guild:
        tournament = next((x for x in guild.tournaments if x.name == name), None)
        if tournament:
            await tournament.addUser(ctx.member)
            await ctx.send("Successfully added", ephemeral = True)
        else:
            await ctx.send("Tournament not found", ephemeral=True)
    else:
        await ctx.send("Server not setup for tournaments", components = [setupServerButton], ephemeral = True)

@tournament.subcommand(
    name = "leave",
    description = "leave a tournament"
)
@option(
    description = "The name of the tournament"
)
async def leaveTournament(ctx:CommandContext, name:str):
    guild = next((x for x in guilds if x.guild.id == ctx.guild.id), None)
    if guild:
        tournament = next((x for x in guild.tournaments if x.name == name), None)
        if tournament:
            await tournament.removeUser(ctx.member)
            await ctx.send("Successfully removed", ephemeral = True)
        else:
            await ctx.send("Tournament not found", ephemeral=True)
    else:
        await ctx.send("Server not setup for tournaments", components = [setupServerButton], ephemeral = True)

scheduler.start()

with open("token.txt", "r") as f:
    bot.start(f.readlines()[0].rstrip("\n"))

toSave = [guild.serialize() for guild in guilds]
with open("save.pkl", "wb") as f:
    Pickler(f).dump(toSave)

#TO_DO - turn guild check into decorator
#TO_DO - brackets
#TO_DO - further card details
#TO_DO - close tournaments after joining time
