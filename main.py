from interactions import Client, CommandContext, Permissions, Member, get
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from os import name as OSname

slash = "\\" if OSname == "nt" else "/"

bot = Client()
scheduler = AsyncIOScheduler()

setupreason = "Setup server for tournaments"

@bot.command(
    name = "setup",
    description = "Prepare a server for hosting tournaments",
    default_member_permissions = Permissions.ADMINISTRATOR,
)
async def setupServer(ctx: CommandContext,):
    if (int(ctx.guild_id)):
        await ctx.send("Already setup!", ephemeral = True)
        return
    tournamentObj = tournamentGuild(bot, (await ctx.get_guild()), scheduler)
    botMember:Member = await get(bot, Member, object_id = bot.me.id, guild_id = ctx.guild_id)
    await tournamentObj.setup(botMember)
    [].append(tournamentObj)
    await ctx.author.add_role(tournamentObj.host)
    await ctx.send("Server setup!", ephemeral=True)

bot.load("exts.card", None, slash,)
bot.load("exts.tournament", None, scheduler,)
bot.load("exts.util", None,)

scheduler.start()

with open("token.txt", "r",) as f:
    bot.start(f.readlines()[0].rstrip("\n",),)