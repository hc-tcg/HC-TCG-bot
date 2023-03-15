#Manages tournament guilds
from interactions import Client, CommandContext, ChannelType, Guild, Channel, Role, Member, EntityType, Permissions, ScheduledEvents, Overwrite, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tournament import tournament

class tournamentGuild:
    setupReason = "Setup server for tournaments"

    def __init__(self, bot:Client, guild:Guild, scheduler:AsyncIOScheduler,) -> None:
        self.bot = bot
        self.guild:Guild = guild
        self.tournaments:list[tournament] = []
        self.scheduler:AsyncIOScheduler = scheduler

    async def setup(self,): #Create required channels and category
        self.host = await self.guild.create_role(
        "tournament host",
        color = 0x18b9d9,
        reason = self.setupReason,
        )
        self.hostOnly = [Overwrite(id = str((await self.guild.get_all_roles())[0].id), deny = Permissions.SEND_MESSAGES), Overwrite(id = str(self.host.id), allow = Permissions.SEND_MESSAGES)]

        self.cat = await self.guild.create_channel( #Category called tournaments, anything to do with tournaments should be here
        "tournaments",
        ChannelType.GUILD_CATEGORY,
        reason = self.setupReason,
        )
        if self.guild.rules_channel_id != None: #Checks if server is community
            self.announcement = await self.guild.create_channel( #Channel to send announcements, eg. game starting
                "tournament-announcements",
                ChannelType.GUILD_ANNOUNCEMENT,
                "Here you will find information abount tournaments",
                permission_overwrites = self.hostOnly,
                parent_id = self.cat,
                reason = self.setupReason,
            )
        else:
            self.announcement = await self.guild.create_channel(
                "tournament-announcements",
                ChannelType.GUILD_TEXT,
                "Here you will find information abount tournaments",
                permission_overwrites = self.hostOnly,
                parent_id = self.cat,
                reason = self.setupReason,
            )
        
        self.vc = await self.guild.create_channel( #Voice channel players will be moved from
            "tournament-voice",
            ChannelType.GUILD_VOICE,
            "Join this channel to be moved into your tournament games",
            parent_id = self.cat,
            reason = self.setupReason,
        )

    async def createTournament(self, name:str, host:Member, startTime:int, maxPlayers:int, description:str):
        newTournament = tournament(name, host, startTime, maxPlayers, description, self, self.scheduler)
        self.tournaments.append(newTournament)
        return newTournament
        
    def serialize(self,):
        return {
            "guild": int(self.guild.id),
            "host": int(self.host.id),
            "cat": int(self.cat.id),
            "announcement": int(self.announcement.id),
            "vc": int(self.vc.id),
            "tournaments": [tournament.serialize() for tournament in self.tournaments],
        }

    async def deserialize(bot:Client, scheduler:AsyncIOScheduler, data:dict,):
        guildObj = tournamentGuild(bot, await get(bot, Guild, object_id = data["guild"]), scheduler)
        guildObj.host = await get(bot, Role, object_id = data["host"], guild_id = guildObj.guild.id)
        guildObj.cat, guildObj.announcement, guildObj.vc = await get(bot, list[Channel], object_ids=[data["cat"], data["announcement"], data["vc"]])
        for tournamentDict in data["tournaments"]:
            tournamentObj = await tournament.deserialize(bot, guildObj, guildObj.scheduler, tournamentDict)
            guildObj.tournaments.append(tournamentObj)

        return guildObj
