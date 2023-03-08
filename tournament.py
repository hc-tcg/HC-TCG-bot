#Tournament classes
from interactions import Member, Client, Embed, ChannelType, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime as dt
from time import time

#from tournamentGuild import tournamentGuild #COMMENT WHEN RUNNING, CIRCULAR

def tournamentEmbed(name:str, host:Member, startTime:int, description:str, players:int, maxPlayers:int):
    tournamentEmbed = Embed(
        title = name,
        description = description if description != None else f"{host.mention} is hosting a tournament!"
    )
    tournamentEmbed.add_field("Start time", f"<t:{round(startTime)}:R>")
    tournamentEmbed.add_field("PLayers", f"{players}/{maxPlayers}")
    return tournamentEmbed



class tournament:
    def __init__(self, name:str, host:Member, startTime:int, maxPlayers:int, description:str, tournamentManager, scheduler:AsyncIOScheduler,) -> None:
        self.name = name
        self.startTime = startTime
        self.maxPlayers = maxPlayers
        self.host = host
        self.description = description
        self.scheduler = scheduler
        self.parent = tournamentManager
        #self.parent:tournamentGuild = tournamentManager
        self.participants:list[Member] = []
        self.message = None
        self.thread = None
        self.role = None

        self.scheduler.add_job(self.warn, DateTrigger(dt.fromtimestamp(self.startTime - 60*5)))
        self.scheduler.add_job(self.updateEmbed, IntervalTrigger(minutes=5), next_run_time = dt.fromtimestamp(time()+1))

    async def addUser(self, user:Member) -> bool:
        if user in self.participants: return False
        self.participants.append(user)
        await user.add_role(self.role)
        return True
    
    async def removeUser(self, user:Member) -> bool:
        try:
            self.participants.remove(user)
            await user.remove_role(self.role)
            return True
        except ValueError:
            return False

    async def updateEmbed(self):
        if self.message == None:
            self.message = await self.parent.announcement.send(embeds = tournamentEmbed(self.name, self.host, self.startTime, self.description, len(self.participants), self.maxPlayers), components = [])
            self.thread = await self.message.create_thread(self.name, 4320, reason = self.name)
            self.role = await self.parent.guild.create_role(f"{self.name} participant", reason=self.name)
        else:
            await self.message.edit(embeds = tournamentEmbed(self.name, self.host, self.startTime, self.description, len(self.participants), self.maxPlayers), components = [])

    async def warn(self):
        await self.thread.send(f"{self.role.mention} - you must be in {self.parent.vc.mention} <t:{self.startTime}:R> to compete.")
    
    async def start(self):
        startMessage = await self.thread.send(f"Setting up tournament")
        players = self.participants
        for player in players:
            if not (player.voice_state and player.voice_state.channel == self.parent.vc): players.remove(player)
        self.expectedReults = []
        for i in range(len(players)/2):
            vc = await self.parent.guild.create_channel(f"{self.name} - {i}", ChannelType.GUILD_VOICE, user_limit = 2, parent_id = self.parent.cat, reason = self.name)
            players[i*2].modify(channel_id = vc)
            players[i*2+1].modify(channel_id=vc)
            self.expectedReults.append((players[i*2], players[i*2+1]))
        startMessage.edit("Games in progress")

    def serialize(self,):
        return {
            "name": self.name,
            "startTime": self.startTime,
            "maxPlayers": self.maxPlayers,
            "description": self.description,
            "host": int(self.host.id),
            "participants": [int(participant.id) for participant in self.participants]
        }
    
    async def deserialize(bot:Client, tournamentManager, scheduler:AsyncIOScheduler, data:dict,):
        host = await get(bot, Member, object_id=data["host"], guild_id=tournamentManager.guild)
        tournamentObj = tournament(data["name"], host, data["startTime"], data["maxPlayers"], data["description"], tournamentManager, scheduler)
        tournamentObj.participants = await get(bot, Member, object_ids=data["participants"], guild_id=tournamentManager.guild)

        return tournamentObj
