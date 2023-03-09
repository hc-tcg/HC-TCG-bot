from interactions import Client, CommandContext, Permissions, Button, ButtonStyle, Member, File, option, get
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

def createImage(deck):
    im = Image.new("RGBA", (6*200, 7*200))
    for i, card in enumerate(deck):
        toPaste = Image.open(f"staticImages\\{card}.png").resize((200, 200)).convert("RGBA")
        im.paste(toPaste, ((i%6)*200,(i//6)*200), toPaste)
    return im

@deck.subcommand(
    name = "show",
    description = "sends an embed with information about the hash",
)
@option("The deck hash")
@option("If the deck image should be a gif or static")
async def showDeck(ctx:CommandContext, deck:str, animate_deck:bool=False):
    deck = hashToDeck(deck, universe)
    image = createImage(deck)
    with BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(files=File(fp=image_binary, filename='deck.png'))

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