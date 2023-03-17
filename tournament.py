#Tournament classes
from interactions import Member, Client, Embed, File, Message, Channel, Role, ChannelType, Button, ButtonStyle, get
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
    def __init__(self, name:str, startTime:int, description:str, tournamentManager, scheduler:AsyncIOScheduler,) -> None:
        self.name:str = name
        self.startTime:int = startTime
        self.description:str = description
        self.scheduler:AsyncIOScheduler = scheduler
        self.parent:tournamentGuild = tournamentManager
        self.participants:list[Member] = []
        self.message:Message = None
        self.channel:Channel = None
        self.role:Role = None
        self.inPlay:bool = False
        self.bracket:brackets = None

        self.joinLeaveButton = Button(
            style = ButtonStyle.PRIMARY,
            label = "Join/Leave tournament",
            custom_id = "join_leave",
        )

        if self.startTime - 60*5 > time():
            self.scheduler.add_job(self.warn, DateTrigger(dt.fromtimestamp(self.startTime - 60*5)), name = "warn")
        if self.startTime > time():
            self.scheduler.add_job(self.start, DateTrigger(dt.fromtimestamp(self.startTime)), name = "start")

    def embed(self):
        e = Embed(
            title = self.name,
            description = self.description if self.description != None else "",
            color = rgbToInt(colors.YELLOW if not self.inPlay else colors.GREEN)
        )
        e.add_field("Start time", f"<t:{round(self.startTime)}:R>")
        e.add_field("Players", str(len(self.participants)))
        e.set_image("attachment://bracket.png")

        imBytes = BytesIO()
        if self.bracket:
            self.bracket.render().save(imBytes, "PNG")
            imBytes.seek(0)
            return e, imBytes
        return e, None

    def searchPlayers(self, playerId:int) -> Member:
        return next((x for x in self.participants if int(x.id) == playerId), None)

    async def addUser(self, user:Member) -> bool:
        if not user in self.participants:
            self.participants.append(user)
            await user.add_role(self.role)
            return True
        return False
    
    async def removeUser(self, user:Member) -> bool:
        try:
            if self.inPlay:
                self.bracket.declareLoser(int(user.id))
            await user.remove_role(self.role)
            self.participants.remove(user)
            return True
        except ValueError:
            return False

    async def updateEmbed(self):
        e, imObj = self.embed()
        args = {"embeds": e, "files": File("bracket.png", imObj) if imObj else [], "components": [self.joinLeaveButton]}
        if self.channel == None:
            self.channel = await self.parent.guild.create_channel(self.name, ChannelType.GUILD_TEXT, topic = self.name, parent_id = self.parent.cat.id)
            await self.parent.announcement.send(f"New tournament - {self.channel.mention}")
            self.message = await self.channel.send(**args)
            self.role = await self.parent.guild.create_role(f"{self.name} participant", reason=self.name)
        else:
            await self.message.edit(**args)
        if imObj:
            imObj.close()

    async def warn(self):
        await self.channel.send(f"{self.role.mention} - competition starts in <t:{round(self.startTime)}:R>.")
    
    async def start(self):
        zipped = [list(newList) for newList in zip(*[(int(member.id), member.name) for member in self.participants])]
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
            e, imObj = self.embed()
            e.color = rgbToInt(colors.RED)
            args = {"embeds": e, "files": File("bracket.png", imObj) if imObj else [], "components": [self.joinLeaveButton]}
            await self.message.edit(**args)
            await self.channel.send(f"Congratulations to {[p for p in self.participants if int(p.id) == self.bracket.layer[0]][0].mention}, you have won!")
            if imObj:
                imObj.close()
            await self.cleanUp()
        else:
            if len([num for num in self.bracket.nextPlayers if num != 0]) > 0:
                await self.updatePlayers()

    async def updatePlayers(self):
        msg = "New matches list:\n"
        for pair in self.bracket.layer:
            p1 = self.searchPlayers(pair[0])
            p2 = self.searchPlayers(pair[1])
            msg += f"{p1.mention} - create a match and send the code to {p2.mention}\n" if p2 else f"{p1.mention} - moved straight to the next round"
        await self.channel.send(msg)
        await self.updateEmbed()

    def serialize(self,):
        return {
            "name": self.name,
            "startTime": self.startTime,
            "description": self.description,
            "participants": [int(participant.id) for participant in self.participants],
            "role": int(self.role.id) if self.role else None,
            "message": int(self.message.id) if self.message else None,
            "channel": int(self.channel.id) if self.channel else None,
            "inPlay": self.inPlay,
            "bracket": self.bracket,
        }
    
    async def deserialize(bot:Client, tournamentManager, scheduler:AsyncIOScheduler, data:dict,):
        tournamentObj = tournament(data["name"], int(data["startTime"]), data["description"], tournamentManager, scheduler)
        tournamentObj.scheduler.pause()
        if len(data["participants"]) > 0:
            tournamentObj.participants = await get(bot, list[Member], object_ids=data["participants"], guild_id=tournamentManager.guild.id)
        tournamentObj.inPlay = data["inPlay"]
        tournamentObj.bracket = data["bracket"]

        if data["channel"]:            
            tournamentObj.channel = await get(bot, Channel, object_id=data["channel"])
            if data["message"]:
                tournamentObj.message = await get(bot, Message, object_id=data["message"], channel_id=tournamentObj.channel.id)
        if data["role"]:
            tournamentObj.role = await get(bot, Role, object_id=data["role"], guild_id=tournamentManager.guild.id)

        tournamentObj.scheduler.resume()

        return tournamentObj

    async def cleanUp(self):
        self.inPlay = False
        if self.scheduler.get_job("update"):
            self.scheduler.remove_job("update")
        if self.scheduler.get_job("start"):
            self.scheduler.remove_job("start")
        if self.scheduler.get_job("warn"):
            self.scheduler.remove_job("warn")

        if self.channel:
            await self.channel.add_permission_overwrites(self.parent.hostOnly)
            self.channel = None
        
        if self.message:
            e, imObj = self.embed()
            args = {"embeds": e, "files": File("bracket.png", imObj) if imObj else [], "components": [self.joinLeaveButton]}
            e.color = rgbToInt(colors.RED)
            await self.message.edit(**args)
            if imObj:
                imObj.close()
            self.message = None

        if self.role:
            await self.role.delete(self.parent.guild)
            self.role = None
