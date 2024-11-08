"""Commands for the bot."""

from interactions import Client, Extension, SlashContext, Status, slash_command

from util.server import ServerManager


class UtilExt(Extension):
    """Commands for the bot."""

    def __init__(self: "UtilExt", client: Client, manager: ServerManager) -> None:
        """Commands for the bot."""
        self.client: Client = client
        self.manager: ServerManager = manager

    @slash_command()
    async def util(self: "UtilExt", _: SlashContext) -> None:
        """Commands for the bot."""

    @util.subcommand()
    async def ping(self: "UtilExt", ctx: SlashContext) -> None:
        """Get the latency of the bot."""
        await ctx.send(
            f"Pong!\nLatency:{round(self.client.latency, 3)}ms", ephemeral=True
        )

    @util.subcommand()
    async def update_updates(self: "UtilExt", ctx: SlashContext) -> None:
        """Update the updates endpoint."""
        try:
            server = self.manager.server_links[ctx.guild_id]
        except KeyError:
            if ctx.author_id == self.client.owner.id:
                await self.manager.update_announcements()
                await ctx.send("Updated updates.")
            else:
                await ctx.send("You aren't allow to do this.", ephemeral=True)
            return
        if server.authorize_user(ctx.author):
            await self.manager.update_announcements()
            await ctx.send("Updated updates.", ephemeral=True)
        else:
            await ctx.send("You aren't allow to do this.", ephemeral=True)

    @util.subcommand()
    async def stop(self: "UtilExt", ctx: SlashContext) -> None:
        """Gracefully shutdown the bot."""
        if ctx.author_id == self.client.owner.id:
            await self.client.change_presence(Status.OFFLINE)
            await ctx.send("Stopping!", ephemeral=True)
            await self.client.stop()
        else:
            await ctx.send(
                f"You aren't allowed to this ||{self.client.owner.mention}||"
            )


def setup(client: Client, **kwargs: dict) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord client
    **kwargs (dict): Dictionary containing additional arguments
    """
    UtilExt(client, **kwargs)
