from interactions import Embed, Client, CommandContext, Guild, Channel, Role, Member, EntityType, Permissions, ScheduledEvents, Button, ButtonStyle, option
from datetime import datetime as dt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pickle import Pickler, Unpickler, UnpicklingError

from tournamentGuild import tournamentGuild
from deck import hashToStrength

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
    tournamentObj = tournamentGuild(ctx.guild, scheduler)
    await tournamentObj.setup()
    guilds.append(tournamentObj)
    await ctx.author.add_role(tournamentObj.host)
    await ctx.send("Server setup!", ephemeral=True)

@bot.command(
    name = "check_deck",
    description = "Get the strength of a deck",
    scope = test_guild,
)
@option("The exported deck")
async def checkDeck(ctx:CommandContext, deck:str):
    strength = hashToStrength(deck)
    await ctx.send(f"Deck strength: {strength}")

@bot.command(
    name = "tournament",
    description = "Base command for tournament",
    scope = test_guild,
)
async def tournament(ctx:CommandContext):
    await ctx.send("You shouldn't be here... ")

@tournament.subcommand(
    name = "start",
    description = "Start a tournament",
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
async def start(ctx:CommandContext, name:str, datetime:str, max_players:int):
    guild = next((x for x in guilds if x.guild.id == ctx.guild.id), None)
    if not guild:
        await ctx.send("Server not setup for tournaments", components = [setupServerButton], ephemeral = True)
        return
    try:
        timeStamp = dt.fromisoformat(datetime).timestamp()
    except ValueError:
        await ctx.send("Invalid ISO date format", ephemeral = True)
    

scheduler.start()

with open("token.txt", "r") as f:
    bot.start(f.readlines()[0].rstrip("\n"))

toSave = [guild.serialize() for guild in guilds]
with open("save.pkl", "wb") as f:
    Pickler(f).dump(toSave)
