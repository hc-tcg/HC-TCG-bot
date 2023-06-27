from interactions import Extension, Client, SlashContext, Status, slash_command


class utilExt(Extension):
    def __init__(self, client: Client) -> None:
        self.client: Client = client

    @slash_command()
    async def util(self, ctx: SlashContext):
        pass

    @util.subcommand()
    async def ping(self, ctx: SlashContext):
        """Get the latency of the bot"""
        await ctx.send(f"Pong!\nLatency:{round(self.client.latency, 3)}ms", ephemeral=True)

    @util.subcommand()
    async def stop(self, ctx: SlashContext):
        """Gracefully shutdown the bot"""
        if ctx.author_id == self.client.owner.id:
            await self.client.change_presence(Status.OFFLINE)
            await ctx.send("Stopping!", ephemeral=True)
            await self.client.stop()
        else:
            await ctx.send(f"You aren't allowed to this ||{self.client.owner.mention}||")


def setup(client):
    utilExt(client)
