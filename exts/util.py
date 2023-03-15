from interactions import Extension, Client, CommandContext, Embed, Role, extension_command, get
from json import load

class utilExt(Extension):
    def __init__(self, client:Client) -> None:
        self.client:Client = client

        with open("help.json") as f:
            helpData:dict[str, dict[str, str]] = load(f)

        utilEmbed = Embed(
            title = "Utility commands",
            description = "Useful commands",
            color=14674416,
        )
        for command, desc in helpData["util"].items():
            utilEmbed.add_field(command, desc)
        tournamentEmbed = Embed(
            title = "Tournament commands",
            description = "Commands to manage and play tournaments",
            color=7971543,
        )
        for command, desc in helpData["tournament"].items():
            tournamentEmbed.add_field(command, desc)
        cardEmbed = Embed(
            title = "Card commands",
            description = "Information about cards",
            color = 5198205,
        )
        for command, desc in helpData["card"].items():
            cardEmbed.add_field(command, desc)

    @extension_command()
    async def util(self):
        """Useful commands"""

    @util.subcommand
    async def help(self, ctx:CommandContext):
        """Information about the bot and its commands"""
        embeds = [self.cardEmbed, self.utilEmbed]
        if [True for role in await get(self.client, list[Role], object_ids = ctx.member.roles, guild_id = ctx.guild_id) if role.name == "Tournament host"]:
            embeds.append(self.tournamentEmbed)
        await ctx.send(embeds = embeds, ephemeral = True)
    
    @util.subcommand
    async def ping(self, ctx:CommandContext):
        """Get the latency of the bot"""
        await ctx.send(f"Pong!\nLatency:{round(self.client.latency, 3)}ms", ephemeral = True)


def setup(client):
    utilExt(client)