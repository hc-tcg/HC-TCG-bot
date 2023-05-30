from interactions import Extension, Client, SlashContext, slash_command


class utilExt(Extension):
    def __init__(self, client: Client) -> None:
        self.client: Client = client

    @slash_command()
    async def ping(self, ctx: SlashContext):
        """Get the latency of the bot"""
        await ctx.send(
            f"Pong!\nLatency:{round(self.client.latency, 3)}ms", ephemeral=True
        )


def setup(client):
    utilExt(client)
