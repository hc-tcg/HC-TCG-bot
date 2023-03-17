#Manages tournament guilds
from interactions import Client, ChannelType, Guild, Channel, Role, Member, Permissions, Overwrite, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tournament import tournament

message = """Welcome to the tournament announcement channel, here you will find announcements of tournaments. To participate, simply go to any tournament channel and press the join button. To play:
1. When the tournament starts, you will be pinged in a message and you or your opponent will be told to create a game.
2. After playing the game, take a screenshot of the game win/loss screen and send it to the channel.
3. AFter all players have played their games, the next set of games will be announced."""

class tournamentGuild:
    setupReason = "Setup server for tournaments"

    def __init__(self, bot:Client, guild:Guild, scheduler:AsyncIOScheduler,) -> None:
        self.bot = bot
        self.guild:Guild = guild
        self.tournaments:list[tournament] = []
        self.scheduler:AsyncIOScheduler = scheduler

    async def setup(self, botMember:Member): #Create required channels and category
        self.host = await self.guild.create_role(
            "Tournament host",
            color = 0x18b9d9,
            reason = self.setupReason,
        )
        self.hostOnly = [Overwrite(id = str((await self.guild.get_all_roles())[0].id), deny = Permissions.SEND_MESSAGES), Overwrite(id = str(self.host.id), allow = Permissions.SEND_MESSAGES)]

        self.cat = await self.guild.create_channel(
        "tournaments",
        ChannelType.GUILD_CATEGORY,
        reason = self.setupReason,
        )
        if self.guild.rules_channel_id != None: #Checks if server is community
            self.announcement = await self.guild.create_channel(
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

        await botMember.add_role(self.host)
        msg = await self.announcement.send(message)
        await msg.pin()

    async def createTournament(self, name:str, startTime:int, description:str):
        newTournament = tournament(name, startTime, description, self, self.scheduler)
        await newTournament.updateEmbed()
        self.tournaments.append(newTournament)
        return newTournament
        
    def serialize(self,):
        return {
            "guild": int(self.guild.id),
            "host": int(self.host.id),
            "cat": int(self.cat.id),
            "announcement": int(self.announcement.id),
            "tournaments": [tournament.serialize() for tournament in self.tournaments],
        }

    async def deserialize(bot:Client, scheduler:AsyncIOScheduler, data:dict,):
        guildObj = tournamentGuild(bot, await get(bot, Guild, object_id = data["guild"]), scheduler)
        guildObj.host = await get(bot, Role, object_id = data["host"], guild_id = guildObj.guild.id)
        guildObj.cat, guildObj.announcement = await get(bot, list[Channel], object_ids=[data["cat"], data["announcement"]])

        for tournamentDict in data["tournaments"]:
            tournamentObj = await tournament.deserialize(bot, guildObj, guildObj.scheduler, tournamentDict)
            guildObj.tournaments.append(tournamentObj)

        guildObj.hostOnly = [Overwrite(id = str(guildObj.guild.id), deny = Permissions.SEND_MESSAGES), Overwrite(id = str(guildObj.host.id), allow = Permissions.SEND_MESSAGES)]
        return guildObj
