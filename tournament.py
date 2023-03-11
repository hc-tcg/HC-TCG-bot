#Tournament classes
from interactions import Member, Client, Embed, File, Message, Channel, Role, ChannelType, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime as dt
from typing import Union
from io import BytesIO
from time import time

from brackets import brackets

try:
    from tournamentGuild import tournamentGuild
except RecursionError:
    pass

def tournamentEmbed(name:str, host:Member, startTime:int, description:str, players:int, maxPlayers:int, bracket:brackets=None):
    e = Embed(
        title = name,
        description = description if description != None else f"{host.mention} is hosting a tournament!"
    )
    e.add_field("Start time", f"<t:{round(startTime)}:R>")
    e.add_field("Players", f"{players}/{maxPlayers}")
    imBytes = BytesIO()
    if bracket:
        bracket.render().save(imBytes, "PNG")
        imBytes.seek(0)
    return e, imBytes

class tournament:
    def __init__(self, name:str, host:Member, startTime:int, maxPlayers:int, description:str, tournamentManager, scheduler:AsyncIOScheduler,) -> None:
        self.name:str = name
        self.startTime:int = startTime
        self.maxPlayers:int = maxPlayers
        self.host:Member = host
        self.description:str = description
        self.scheduler:AsyncIOScheduler = scheduler
        self.parent:tournamentGuild = tournamentManager
        self.participants:list[Member] = []
        self.message:Message = None
        self.thread:Channel = None
        self.role:Role = None
        self.inPlay:bool = False
        self.bracket:brackets = None

        self.scheduler.add_job(self.warn, DateTrigger(dt.fromtimestamp(self.startTime - 60*5)))
        self.scheduler.add_job(self.updateEmbed, IntervalTrigger(minutes=5), next_run_time = dt.fromtimestamp(time()+1))

    async def addUser(self, user:Member) -> Union[None, str]:
        if user in self.participants: return "You are already participating in this competition"
        if self.inPlay: return "This tournament has already started"
        if self.maxPlayers == len(self.participants): return "This tournament is full"
        self.participants.append(user)
        await user.add_role(self.role)
        return True
    
    async def removeUser(self, user:Member) -> bool:
        try:
            if self.inPlay:
                self.bracket.declareLoser()
            self.participants.remove(user)
            await user.remove_role(self.role)
            return True
        except ValueError:
            return False

    async def updateEmbed(self):
        e, imObj = tournamentEmbed(self.name, self.host, self.startTime, self.description, len(
            self.participants), self.maxPlayers, self.bracket)
        if self.message == None:
            self.message = await self.parent.announcement.send(embeds = e, files = File(fp=imObj))
            self.thread = await self.message.create_thread(self.name, 4320, reason = self.name)
            self.role = await self.parent.guild.create_role(f"{self.name} participant", reason=self.name)
        else:
            await self.message.edit(embeds = tournamentEmbed(self.name, self.host, self.startTime, self.description, len(self.participants), self.maxPlayers), components = [])

    async def warn(self):
        await self.thread.send(f"{self.role.mention} - you must be in {self.parent.vc.mention} <t:{self.startTime}:R> to compete.")
    
    async def start(self):
        self.inPlay = True
        self.bracket = brackets([member.id for member in self.participants], [member.name for member in self.participants])
        players = self.bracket.layer
        for player in players:
            if not (player.voice_state and player.voice_state.channel.parent_id == self.parent.cat.id): players.remove(player)
        self.expectedReults = []
        for i in range(len(players)/2):
            vc = await self.parent.guild.create_channel(f"{self.name} - {i}", ChannelType.GUILD_VOICE, user_limit = 2, parent_id = self.parent.cat, reason = self.name)
            players[i*2].modify(channel_id = vc)
            players[i*2+1].modify(channel_id=vc)
            self.expectedReults.append((players[i*2], players[i*2+1]))

        for pair in self.bracket.layer:
            pass

    def serialize(self,):
        return {
            "name": self.name,
            "startTime": self.startTime,
            "maxPlayers": self.maxPlayers,
            "description": self.description,
            "host": int(self.host.id),
            "participants": [int(participant.id) for participant in self.participants],
            "role": int(self.role.id) if self.role else None,
            "message": int(self.message.id) if self.message else None,
            "thread": int(self.thread.id) if self.thread else None,
            "inPlay": self.inPlay
        }
    
    async def deserialize(bot:Client, tournamentManager, scheduler:AsyncIOScheduler, data:dict,):
        host = await get(bot, Member, object_id=data["host"], guild_id=tournamentManager.guild)
        tournamentObj = tournament(data["name"], host, data["startTime"], data["maxPlayers"], data["description"], tournamentManager, scheduler)
        tournamentObj.participants = await get(bot, Member, object_ids=data["participants"], guild_id=tournamentManager.guild)

        return tournamentObj
