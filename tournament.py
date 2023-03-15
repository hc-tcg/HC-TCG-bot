#Tournament classes
from interactions import Member, Client, Embed, File, Message, Channel, Role, ChannelType, get, search_iterable
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
except ImportError:
    pass

class colors:
    YELLOW = (255, 225, 0)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)

def rgbToInt(col:tuple[int, int, int]) -> int:
    return (col[0] << 16) + (col[1] << 8) + col[2]

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
        self.voiceChannels = None

        if self.startTime - 60*5 > time():
            self.scheduler.add_job(self.warn, DateTrigger(dt.fromtimestamp(self.startTime - 60*5)), name = "warn")
        if self.startTime > time():
            self.scheduler.add_job(self.start, DateTrigger(dt.fromtimestamp(self.startTime)), name = "start")
            self.scheduler.add_job(self.updateEmbed, IntervalTrigger(minutes=5), next_run_time = dt.fromtimestamp(time()+1), name="update")

    def createEmbed(self):
        e = Embed(
            title = self.name,
            description = self.description if self.description != None else f"{self.host.mention} is hosting a tournament!",
            color = rgbToInt(colors.YELLOW if not self.inPlay else colors.GREEN)
        )
        e.add_field("Start time", f"<t:{round(self.startTime)}:R>")
        e.add_field("Players", f"{len(self.participants)}/{self.maxPlayers}")
        e.set_image("attachment://bracket.png")

        imBytes = BytesIO()
        if self.bracket:
            self.bracket.render().save(imBytes, "PNG")
            imBytes.seek(0)
            return e, imBytes
        return e, None

    def searchPlayers(self, playerId:int) -> Member:
        return next((x for x in self.participants if int(x.id) == playerId), None)

    async def addUser(self, user:Member) -> Union[None, str]:
        self.participants.append(user)
        await user.add_role(self.role)
        if self.thread:
            await self.thread.add_member(user)
        return True
    
    async def removeUser(self, user:Member) -> bool:
        try:
            if self.inPlay:
                self.bracket.declareLoser(int(user.id))
            if self.thread:
                await self.thread.remove_member(user)
            await user.remove_role(self.role)
            self.participants.remove(user)
            return True
        except ValueError:
            return False

    async def updateEmbed(self):
        e, imObj = self.createEmbed()
        args = {"embeds": e, "files": File("bracket.png", imObj) if imObj else []}
        if self.message == None:
            self.message = await self.parent.announcement.send(**args)
            self.thread = await self.message.create_thread(self.name, 4320, reason = self.name)
            self.role = await self.parent.guild.create_role(f"{self.name} participant", reason=self.name)
        else:
            await self.message.edit(**args)
        if imObj:
            imObj.close()

    async def warn(self):
        await self.thread.send(f"{self.role.mention} - you must be in {self.parent.vc.mention} <t:{round(self.startTime)}:R> to compete.")
    
    async def start(self):
        zipped = [list(newList) for newList in zip(*[(int(member.id), member.name) for member in self.participants if self.parent.vc.voice_states])]
        if self.scheduler.get_job("update"):
            self.scheduler.remove_job("update")
        if len(zipped) == 0:
            await self.cleanUp()
            return
        self.inPlay = True
        try:
            self.bracket = brackets(*zipped)
        except NotImplementedError:
            await self.cleanUp()
            return
        await self.updatePlay()
    
    async def updatePlay(self):
        if type(self.bracket.layer[0]) == int:
            self.inPlay = False
            e, imObj = self.createEmbed()
            e.color = rgbToInt(colors.RED)
            args = {"embeds": e, "files": File("bracket.png", imObj) if imObj else []}
            await self.message.edit(**args)
            await self.thread.send(f"Congratulations to {[p for p in self.participants if int(p.id) == self.bracket.layer[0]][0].mention}, you have won!")
            self.parent.tournaments.remove(self)
            if imObj:
                imObj.close()
            await self.cleanUp()
        else:
            await self.updatePlayers()

    async def updatePlayers(self):
        if not self.voiceChannels:
            self.voiceChannels = search_iterable(await self.parent.guild.get_all_channels(), lambda c: c.parent_id == self.parent.cat.id and c.name.startswith("tournament vc"))
        for i, pair in enumerate(self.bracket.layer):
            vc = search_iterable(self.voiceChannels, lambda c: c.name.endswith(str(i+1)))
            if len(vc) == 0:
                vc = [await self.parent.guild.create_channel(f"tournament vc {i+1}", ChannelType.GUILD_VOICE, user_limit=2, parent_id=self.parent.cat, reason=self.name)]
            vc = vc[0]
            p1 = self.searchPlayers(pair[0])
            p2 = self.searchPlayers(pair[2])
            
            for state in vc.voice_states:
                if not (state.member == p1 or state.member == p2):
                    await state.move_member(self.parent.vc)

            await p1.modify(channel_id=vc.id)
            await p2.modify(channel_id=vc.id)
        await self.updateEmbed()

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
            "inPlay": self.inPlay,
            "bracket": self.bracket,
        }
    
    async def deserialize(bot:Client, tournamentManager, scheduler:AsyncIOScheduler, data:dict,):
        host = await get(bot, Member, object_id=data["host"], guild_id=tournamentManager.guild.id)
        tournamentObj = tournament(data["name"], host, int(data["startTime"]), data["maxPlayers"], data["description"], tournamentManager, scheduler)
        tournamentObj.scheduler.pause()
        if len(data["participants"]) > 0:
            tournamentObj.participants = await get(bot, list[Member], object_ids=data["participants"], guild_id=tournamentManager.guild.id)
        tournamentObj.inPlay = data["inPlay"]
        tournamentObj.bracket = data["bracket"]

        if data["thread"]:
            tournamentObj.thread = await get(bot, Channel, object_id=data["thread"])
        if data["message"]:
            tournamentObj.message = await get(bot, Message, object_id=data["message"], channel_id=tournamentObj.parent.announcement.id)
        if data["role"]:
            tournamentObj.role = await get(bot, Role, object_id=data["role"], guild_id=tournamentManager.guild.id)

        tournamentObj.scheduler.resume()

        return tournamentObj

    async def cleanUp(self):
        if self.scheduler.get_job("update"):
            self.scheduler.remove_job("update")
        if self.scheduler.get_job("start"):
            self.scheduler.remove_job("start")
        if self.scheduler.get_job("warn"):
            self.scheduler.remove_job("warn")
        await self.thread.lock()
        await self.thread.archive()
        e, image = self.createEmbed()
        e.color = rgbToInt(colors.RED)
        await self.message.edit(embeds=e, files=File("bracket.png", image) if image else [])
        if image:
            image.close()
        await self.role.delete(self.parent.guild)
        self.role = None
