from interactions import Client, CommandContext, Intents, Permissions, Snowflake, Button, Embed, Choice, ButtonStyle, Member, Choice, File, option, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pickle import Pickler, Unpickler, UnpicklingError
from dateutil.parser.isoparser import isoparse
from io import BytesIO
from PIL import Image
from json import load
from time import time
from os import listdir
from datetime import datetime as dt
from collections import Counter
from os import name as OSname

from tournamentGuild import tournamentGuild
from deck import hashToStars, hashToDeck, universe

slash = "\\" if OSname == "nt" else "/"

bot = Client(intents=Intents.GUILD_VOICE_STATES)
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
    print("Ready")

def checkSetup(_id:int):
    return any(int(x.guild.id) == _id for x in guilds)

@bot.command(
    name = "setup",
    description = "Prepare a server for hosting tournaments",
    default_member_permissions = Permissions.ADMINISTRATOR,
)
@bot.component(setupServerButton)
async def setupServer(ctx: CommandContext,):
    if checkSetup(int(ctx.guild_id)):
        await ctx.send("Already setup!", ephemeral = True)
        return
    tournamentObj = tournamentGuild(bot, (await ctx.get_guild()), scheduler)
    await tournamentObj.setup()
    guilds.append(tournamentObj)
    await ctx.author.add_role(tournamentObj.host)
    botMember:Member = await get(bot, Member, object_id = bot.me.id, guild_id = ctx.guild_id)
    await botMember.add_role(tournamentObj.host)
    await ctx.send("Server setup!", ephemeral=True)

@bot.command(
    name = "card",
    description = "all about cards",
)
async def card(ctx:CommandContext):
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
        "xbcrafted_common",
        "zombiecleo_rare"
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
        "welsknight_common",
        "zombiecleo_common"
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

def getStats(deck:list) -> tuple[Image.Image, tuple[int,int,int], dict[str, int]]:
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
        if card.startswith("item"):
            items += 1
        elif card.endswith(("rare", "common")):
            hermits += 1
            for cardType, hermitList in hermitTypes.items():
                if card in hermitList:
                    typeCounts[cardType] += 1
                    break
        else:
            effects += 1

        toPaste = Image.open(f"staticImages{slash}{card}.png").resize((200, 200)).convert("RGBA")
        im.paste(toPaste, ((i%6)*200,(i//6)*200), toPaste)
    return im, (hermits, items, effects), typeCounts

def getLongest(x:dict):
    return [k for k in x.keys() if x.get(k)==max([n for n in x.values()])]

@card.subcommand(
    name = "deck",
    description = "sends an embed with information about the deck",
)
@option(
    description = "The deck hash"
)
@option(
    description = "The server the link directs to",
    choices = [
        Choice(
            name = "Dev site",
            value = "https://hc-tcg.online/?deck=",
        ),
        Choice(
            name = "Xisumaverse",
            value = "https://tcg.xisumavoid.com/?deck=",
        ),
        Choice(
            name = "Balanced",
            value = "https://tcg.prof.ninja/?deck="
        )
    ]
)
async def showDeck(ctx:CommandContext, deck:str, server:str):
    deckList = hashToDeck(deck, universe)
    im, hic, typeCounts = getStats(deckList)
    col = typeColors[getLongest(typeCounts)[0]]
    e = Embed(
        title = "Deck stats",
        description = f"Hash: {deck}",
        url = server + deck,
        timestamp = dt.now(),
        color = (col[0] << 16) + (col[1] << 8) + (col[2]),
    )
    e.set_image("attachment://deck.png")
    e.add_field("Token cost", str(hashToStars(deck)), True)
    e.add_field("HEI ratio", f"{hic[0]}:{hic[2]}:{hic[1]}", True)
    e.add_field("Types", len([typeList for typeList in typeCounts.values() if typeList != 0]), True)
    with BytesIO() as im_binary:
        im.save(im_binary, 'PNG')
        im_binary.seek(0)
        await ctx.send(embeds=e, files=File(fp=im_binary, filename="deck.png"))

def countString(toCount):
    final = ""
    for k, v in Counter(toCount).most_common():
        final += f"{v}x {k}, "
    return final.rstrip(", ")

def getHermitCards(file, rarity=None):
    with open(file, "r") as f:
        data = load(f)
    for card in data:
        if rarity != None and card["rarity"] != rarity: continue
        col = typeColors[card["hermitType"]]
        e = Embed(
            title = card["name"],
            description = card["rarity"].capitalize().replace("_", " ") + " " + card["name"],
            timestamp = dt.now(),
            color = (col[0] << 16) + (col[1] << 8) + (col[2]),
        )
        e.set_thumbnail(f"attachment://{card['id']}.png")

        e.add_field("Primary attack", card["primary"]["name"] if card["primary"]["power"] == None else card["primary"]["name"] + " - " + card["primary"]["power"], False)
        e.add_field("Attack damage", card["primary"]["damage"], True)
        e.add_field("Items required", countString(card["primary"]["cost"]), True)

        e.add_field("Secondary attack", card["secondary"]["name"] if card["secondary"]["power"] == None else card["secondary"]["name"] + " - " + card["secondary"]["power"].replace("\n\n", "\n"), False)
        e.add_field("Attack damage", card["secondary"]["damage"], True)
        e.add_field("Items required", countString(card["secondary"]["cost"]), True)

        im = Image.open(f"staticImages{slash}{card['id']}.png")
        yield im, e, card["id"]

choices = {}
for file in [f for f in listdir("data") if not f.startswith(".")]:
    with open(f"data{slash}{file}", "r") as f:
        choices[load(f)[0]["name"].capitalize()] = f"data{slash}{file}"

@card.subcommand(
    name = "hermit",
    description = "get information about a hermit, other cards coming soon",
)
@option(
    description = "The hermit",
    autocomplete = True,
)
@option(
    description = "Select the rarity",
    choices = [
        Choice(name = "Common", value = "common"),
        Choice(name = "Rare", value = "rare"),
        Choice(name = "Ultra rare", value = "ultra_rare"),
    ]
)
async def info(ctx:CommandContext, card:str, rarity:str=None):
    embeds = []
    images = []
    imObjs = []
    if card.capitalize() in choices.keys():
        for im, e, _id in getHermitCards(choices[card.capitalize()], rarity):
            embeds.append(e)
            imBytes = BytesIO()
            im.save(imBytes, "PNG")
            imBytes.seek(0)
            images.append(File(fp=imBytes, filename=f"{_id}.png"))
            imObjs.append(imBytes)
        if len(embeds) == 0:
            await ctx.send("That hermit doesn't have a card of that rarity", ephemeral = True)
            return
        await ctx.send(embeds = embeds, files = images)
        for image in imObjs:
            image.close()
    else:
        await ctx.send("Hermit not found, allowed hermits are : " + ", ".join(choices.keys()), ephemeral=True)

@info.autocomplete("card")
async def autocompleteHermit(ctx:CommandContext, name:str=None):
    if not name:
        await ctx.populate([{"name": n, "value": n} for n in list(choices.keys())[0:25]])
        return
    results = [{"name": n, "value": n} for n in choices.keys() if name.lower() in n.lower()][0:25]
    await ctx.populate(results)

async def checkRunnable(sendFunc, gId:Snowflake, name:str=None):
    guild = next((x for x in guilds if x.guild.id == gId), None)
    if guild:
        tourney = next((x for x in guild.tournaments if x.name == name), None)
        if tourney or tourney == name:
            return True, guild, tourney
        await sendFunc("Tournament not found", ephemeral=True,)
        return False, guild, None
    else:
        await sendFunc("Server not setup for tournaments", components = [setupServerButton], ephemeral = True,)
        return False, None, None

@bot.command(
    name = "tournament",
    description = "Base command for tournament",
)
async def tournament(ctx:CommandContext):
    pass

timeRange = 3*60*60

def timeCheck(time1, time2):
    return time1 - timeRange > time2 and time1 + timeRange < time2

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
async def create(ctx:CommandContext, name:str, datetime:str, max_players:int, description:str = ""):
    allowed, guild, _ = await checkRunnable(ctx.send, ctx.guild_id, None)
    if not allowed:
        return
    if int(guild.host.id) in ctx.author.roles:
        try:
            timeStamp = isoparse(datetime).timestamp()
            if timeStamp < time():
                await ctx.send("Start time is in the past", ephemeral = True)
                return
            close = [True for tourney in guild.tournaments if timeCheck(timeStamp, tourney.startTime)]
            if len(close) > 0:
                await ctx.send("Tournament is too close to another (3 hour limit)", ephemeral = True)
        except ValueError:
            await ctx.send("Invalid ISO date format", ephemeral = True)
            return
        await guild.createTournament(name, ctx.member, timeStamp, max_players, description)
        await ctx.send("Creating tournament", ephemeral = True)
        return
    await ctx.send("You must have the tournament host role to start a tournament", ephemeral = True)

@tournament.subcommand()
@option(
    description = "The name of the tournament",
    autocomplete = True,
)
async def remove(ctx:CommandContext, name:str):
    """Remove a tournament from the server"""
    valid, guild, tourney = await checkRunnable(ctx.send, ctx.guild_id, name)
    if valid:
        if guild.host.id in ctx.author.roles:
            guild.tournaments.remove(tourney)
            await ctx.send("Removed tournament", ephemeral = True)
            await tourney.cleanUp()
        else:
            await ctx.send("You do not have authentication to do this", ephemeral=True)

@tournament.subcommand(
        name = "list"
)
async def listTournaments(ctx:CommandContext):
    """List all tournaments in the server"""
    valid, guild, _ = await checkRunnable(ctx.send, ctx.guild_id)
    if valid:
        await ctx.send("Current tournaments: " + ", ".join((t.name for t in guild.tournaments)), ephemeral = True)

@tournament.subcommand(
    name = "join",
    description = "join a tournament"
)
@option(
    description = "The name of the tournament",
    autocomplete = True,
)
async def joinTournament(ctx:CommandContext, name:str):
    valid, _, tourney = await checkRunnable(ctx.send, ctx.guild_id, name)
    
    if valid:
        errMessage = "You are already in this tournament" if ctx.author in tourney.participants else ("Tournament is full" if len(tourney.participants)+1 > tourney.maxPlayers else ("The tournament has already started" if tourney.inPlay else ""))
        if errMessage != "":
            await ctx.send(errMessage, ephemeral = True,)
            return
        await tourney.addUser(ctx.member)
        await ctx.send("Successfully added", ephemeral = True)

@tournament.subcommand(
    name = "leave",
    description = "leave a tournament"
)
@option(
    description = "The name of the tournament",
    autocomplete = True,
)
async def leaveTournament(ctx:CommandContext, name:str):
    valid, _, tourney = await checkRunnable(ctx.send, ctx.guild_id, name)
    if valid:
        await tourney.removeUser(ctx.member)
        await ctx.send("Successfully removed", ephemeral = True)

@tournament.subcommand(
    name = "show",
    description="Send an image of the tournament brackets",
)
@option(
    description="The name of the tournament",
    autocomplete=True,
)
async def show(ctx:CommandContext, name:str):
    """Render an image of the tournament brackets"""
    valid, _, tourney = await checkRunnable(ctx.send, ctx.guild_id, name)
    if valid and tourney.bracket:
        with BytesIO() as imBytes:
            tourney.bracket.render().save(imBytes, "PNG")
            imBytes.seek(0)
            await ctx.send("Rendered tournament:", files = File("bracket.png", imBytes))
    elif valid:
        await ctx.send("Tournament not started yet", ephemeral = True)

@tournament.subcommand(
    name = "winner",
    description = "declare a winner in your match",
)
@option(
    description = "The name of the tournament",
    autocomplete = True,
)
@option(
    description = "The winning player"
)
async def winner(ctx:CommandContext, name:str, player:Member):
    valid, _, tourney = await checkRunnable(ctx.send, ctx.guild_id, name)
    if valid:
        if tourney.inPlay:
            res = tourney.bracket.declareWinner(int(player.id))
            if res:
                await ctx.send(f"Winner declared: {player.mention}")
                await tourney.updatePlay()
                return
        else:
            await ctx.send("You can't declare a winner for a tournament that hasn't started yet", ephemeral = True)
            return
        await ctx.send("Couldn't find that opponent (you can't declare winners for a fight you are not in)", ephemeral = True)
    pass

@winner.autocomplete("name") #For some reason this works for all tournaments??
async def tournamentAutocomplete(ctx:CommandContext, name:str=None):
    guild = next((x for x in guilds if x.guild.id == ctx.guild_id), None)
    if not guild and not name:
        await ctx.populate([])
        return
    if not name and guild:
        await ctx.populate([{"name":tourney.name, "value":tourney.name} for tourney in guild.tournaments][0:25])
        return
    if name and guild:
        await ctx.populate([{"name":tourney.name, "value":tourney.name} for tourney in guild.tournaments if name in tourney.name][0:25])

@bot.command()
async def ping(ctx:CommandContext):
    """Get the latency of the bot"""
    await ctx.send(f"Pong!\nLatency:{round(bot.latency, 3)}ms", ephemeral = True)

utilEmbed = Embed(
    title = "Utility commands",
    description = "Useful commands",
    color=14674416,
)
utilEmbed.add_field("/setup", "Must be run to setup the tournament. Creates a tournament category, along with an announcement and voice channel. Administrator only")
utilEmbed.add_field("/ping", "Get the latency of the bot.", True)
utilEmbed.add_field("/help", "Show this help message.", True)
tournamentEmbed = Embed(
    title = "Tournament commands",
    description = "Commands to manage and play tournaments",
    color=7971543,
)
tournamentEmbed.add_field("/tournament create (name) (datetime) (maximum players) [description]", "Create a tournament called (name) that starts at (dateime) written in ISO 8601 and has at most (maximum players) players which is a power of two. It is optionally described as [description].\nRequires the tournament host role.")
tournamentEmbed.add_field("/tournament remove (name)", "Remove a previously created tournament called (name).\nRequires the tournament host role.")
tournamentEmbed.add_field("/tournament join (name)", "Join the tournament called (name).")
tournamentEmbed.add_field("/tournament leave (name)", "Leave the tournament called (name).")
tournamentEmbed.add_field("/tournament winner (name), (player)", "Declare the winner of your match in the tournament (name) as (player).")
tournamentEmbed.add_field("/tournament show (name)", "Show the tournament bracket of the tournament (name).")
cardEmbed = Embed(
    title = "Card commands",
    description = "Information about cards",
    color = 5198205,
)
cardEmbed.add_field("/card deck (hash)", "Create an image of the deck, (hash) is the exported deck hash")
cardEmbed.add_field("/card hermit (hermit) [rarity]", "Get information about a (hermit)'s card, optionally only of rarity [rarity].")


@bot.command()
async def help(ctx:CommandContext):
    """Information about the bot and its commands"""   
    await ctx.send(embeds = [tournamentEmbed, cardEmbed, utilEmbed])

scheduler.start()

with open("token.txt", "r") as f:
    bot.start(f.readlines()[0].rstrip("\n"))

toSave = [guild.serialize() for guild in guilds]
if len(toSave) != 0:
    with open("save.pkl", "wb") as f:
        Pickler(f).dump(toSave)
