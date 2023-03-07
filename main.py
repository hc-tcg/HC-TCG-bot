from interactions import Client, CommandContext, ChannelType, Guild, Channel, Role, Member, EntityType, Permissions, ScheduledEvents
from datetime import datetime as dt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

bot = Client()

setupreason = "Setup server for tournaments"

test_guild = 1080579441790566450

guilds = []

class tournamentGuild:
    def __init__(self, guild:Guild, category:Channel, announcement:Channel, general:Channel, host:Role,) -> None:
        self.guild = guild
        self.cat = category
        self.announement = announcement
        self.general = general
        self.host = host
        self.tournaments = []
        self.roles = []

    async def addTournament(self, name:str, startTime:int, maxPlayers:int, host:Member,):
        tournamentReason = f"{name} tournament hosted by {host.name}"
        event = await self.guild.create_scheduled_event(
            name,
            EntityType.EXTERNAL,
            dt.fromtimestamp(startTime).isoformat(),
            channel_id = self.announement,
            description = f"{host.name} is hosting a tournament: {name}\nMax players: {maxPlayers}",)
        participantRole = await self.guild.create_role(f"{name} competitor", reason = tournamentReason,)
        generalThread = await self.general.create_thread(f"{name} tournament", ChannelType.PRIVATE_THREAD, 10080, False, reason=tournamentReason,)
        announcementThread = await self.announement.create_thread(f"{name} tournament", ChannelType.PRIVATE_THREAD, 10080, False, reason=tournamentReason,)


class KOtournament:
    def __init__(self, event:ScheduledEvents, participantRole:Role, general:Channel, announcement:Channel, name:str, startTime:int, ) -> None:
        self.event = event
        self.name = name
        self.participantRole = participantRole
        self.general = general
        self.announcement = announcement
        self.participants = []
        
        trigger = CronTrigger()
        trigger.start_date = dt.fromtimestamp(startTime)
        scheduler.add_job(lambda: self.start(), trigger)
    
    def addMemeber(self, member:Member):
        member.add_role(self.participantRole)
        self.participants.append(member)

    def start(self):
        pass

def checkSetup(_id:int):
    return any(int(x.guild.id) == _id for x in guilds)

@bot.command(
    name = "setup",
    description = "Prepare a server for hosting a tournement, creates a host role for tournements and creates channels in their own category",
    default_member_permissions = Permissions.ADMINISTRATOR,
    scope = test_guild,
)
async def setupServer(ctx: CommandContext,):
    if checkSetup(int(ctx.guild.id)): await ctx.send("Already setup!", ephemeral = True)
    tournamentCat = await ctx.guild.create_channel(
        "tournaments",
        ChannelType.GUILD_CATEGORY,
        reason = setupreason,
    )
    if ctx.guild.rules_channel_id != None: #Checks if server is community
        announcementChan = await ctx.guild.create_channel(
            "tournament-announcements",
            ChannelType.GUILD_ANNOUNCEMENT,
            "Here you will find information abount tournaments",
            parent_id = tournamentCat,
            reason = setupreason,
        )
    else:
        announcementChan = await ctx.guild.create_channel(
            "tournament-announcements",
            ChannelType.GUILD_TEXT,
            "Here you will find information abount tournaments",
            parent_id=tournamentCat,
            reason=setupreason,
        )
    generalChan = await ctx.guild.create_channel(
        "tournament-general",
        ChannelType.GUILD_TEXT,
        "Discuss tournaments",
        reason = setupreason,
    )
    hostRole = await ctx.guild.create_role(
        "tournament host",
        color = 0x18b9d9,
        reason = setupreason,
    )
    guilds.append(tournamentGuild(ctx.guild, tournamentCat, announcementChan, generalChan, hostRole))
    ctx.author.add_role(hostRole)
    await ctx.send("Server setup!", ephemeral=True)

scheduler = AsyncIOScheduler()
scheduler.start()