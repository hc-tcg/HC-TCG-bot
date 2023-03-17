from interactions import Extension, Client, CommandContext, Snowflake, Member, ComponentContext, Button, ButtonStyle, extension_component, extension_command, extension_listener, option, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pickle import Unpickler, Pickler, UnpicklingError
from dateutil.parser.isoparser import isoparse
from time import time

from tournamentGuild import tournamentGuild

async def doNothing(*args, **kwargs):
    """Literally does nothing, used to bypass auto sending"""

class tournamentExt(Extension):
    def __init__(self, client:Client, scheduler:AsyncIOScheduler,) -> None:
        self.client:Client = client
        self.scheduler:AsyncIOScheduler = scheduler
    
    deleteChannelButton = Button(
        style = ButtonStyle.PRIMARY,
        label = "Delete channel",
        custom_id = "delete_channel",
    )

    @extension_component("delete_channel")
    async def deleteChannel(self, ctx:ComponentContext):
        valid, guild, tourney = await self.getSetup(ctx.send, ctx.guild_id, (await ctx.get_channel()).topic)
        channel = await ctx.get_channel()
        if valid:
            guild.tournaments.remove(tourney)
        await channel.delete()

    @extension_component("join_leave")
    async def joinOrLeave(self, ctx:ComponentContext,):
        channel = await ctx.get_channel()
        guild = await ctx.get_guild()
        valid, _, tourney = await self.getSetup(ctx.send, guild.id, channel.topic)
        if valid:
            if not await tourney.addUser(ctx.author):
                await tourney.removeUser(ctx.author)
                await tourney.updateEmbed()
                await ctx.send("Removed you!", ephemeral = True)
                return
            await tourney.updateEmbed()
            await ctx.send("Added you!", ephemeral = True)

    @extension_listener
    async def on_start(self):
        self.guilds = []
        try:
            with open("save.pkl", "rb",) as f:
                self.guilds = [await tournamentGuild.deserialize(self.client, self.scheduler, tournament,) for tournament in Unpickler(f,).load()]
        except (UnpicklingError, FileNotFoundError, EOFError,):
            pass
        print("Ready!")
    
    @extension_listener
    async def on_disconnect(self):
        toSave = [guild.serialize() for guild in self.guilds]
        if len(toSave) != 0:
            with open("save.pkl", "wb") as f:
                Pickler(f).dump(toSave)
        print("Saved data")

    async def getSetup(self, sendFunc, gId:Snowflake, name:str=None,):
        guild = next((x for x in self.guilds if x.guild.id == gId), None,)
        if guild:
            tourney = next((x for x in guild.tournaments if x.name == name), None,)
            if tourney or tourney == name:
                return True, guild, tourney,
            await sendFunc("Tournament not found", ephemeral=True,)
            return False, guild, None,
        else:
            await sendFunc("Server not setup for tournaments", ephemeral = True,)
            return False, None, None,

    @extension_command()
    async def tournament(self, ctx:CommandContext,):
        """Manage tournaments"""

    @tournament.subcommand()
    @option(
        description = "The name of the tournament",
    )
    @option(
        description = "The date and time of the tournament start in ISO 8601 format",
    )
    @option(
        description = "The description text of the tournament",
    )
    async def create(self, ctx:CommandContext, name:str, datetime:str, description:str = "",):
        """Create a tournament"""
        allowed, guild, _ = await self.getSetup(ctx.send, ctx.guild_id, None)
        if not allowed:
            return
        if int(guild.host.id) in ctx.author.roles:
            try:
                timeStamp = isoparse(datetime).timestamp()
                if timeStamp < time():
                    await ctx.send("Start time is in the past", ephemeral = True)
                    return
            except ValueError:
                await ctx.send("Invalid ISO 8601 date format", ephemeral = True)
                return
            
            tournament = await guild.createTournament(name, timeStamp, description)

            await ctx.send(f"Tournament created, {tournament.channel.mention}", ephemeral = True)
            return
        await ctx.send("You must have the tournament host role to start a tournament", ephemeral = True)

    @tournament.subcommand()
    async def end(self, ctx:CommandContext,):
        """End a tournament""" #TO_DO: add confirmation
        valid, guild, tourney = await self.getSetup(ctx.send, ctx.guild_id, (await ctx.get_channel()).topic)
        if valid:
            if guild.host.id in ctx.author.roles:
                await ctx.send("Removed tournament", components = [self.deleteChannelButton], ephemeral = True)
                await tourney.cleanUp()
            else:
                await ctx.send("You do not have authentication to do this", ephemeral=True)
    
    @tournament.subcommand()
    @option(
        description = "The player to declare as a winner",
    )
    async def winner(self, ctx:CommandContext, player:Member,):
        valid, _, tourney = await self.getSetup(ctx.send, ctx.guild_id, (await ctx.get_channel()).topic)
        if valid:
            if tourney.inPlay:
                res = tourney.bracket.declareWinner(int(player.id))
                if res:
                    await ctx.send(f"Winner declared: {player.mention}")
                    await tourney.updatePlay()
                    return
                await ctx.send("Couldn't find that opponent (you can't declare winners for a fight you are not in)", ephemeral = True)
            else:
                await ctx.send("You can't declare a winner for a tournament that hasn't started yet", ephemeral = True)
                return

    @tournament.subcommand()
    async def setup(self, ctx:CommandContext):
        """Prepare a server for hosting tournaments"""
        setup, _, _ = await self.getSetup(doNothing, ctx.guild_id,)
        if setup:
            await ctx.send("Already setup", ephermal = True,)
        settingUp = tournamentGuild(self.client, (await ctx.get_guild()), self.scheduler)
        await settingUp.setup(await get(self.client, Member, object_id = self.client.me.id, guild_id = ctx.guild_id))
        await ctx.send("Successfully setup", ephemeral = True,)
        self.guilds.append(settingUp)
        await ctx.author.add_role(settingUp.host)

def setup(client:Client, scheduler:AsyncIOScheduler):
    tournamentExt(client, scheduler)
