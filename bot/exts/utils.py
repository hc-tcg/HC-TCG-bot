"""Commands for the bot."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import Client, Extension, SlashContext, Status, User, slash_command

from bot.util import DataGenerator, ServerManager


class UtilExt(Extension):
    """Commands for the bot."""

    def __init__(
        self: UtilExt,
        client: Client,
        _manager: ServerManager,
        _scheduler: AsyncIOScheduler,
        _generator: DataGenerator,
    ) -> None:
        """Commands for the bot.

        Args:
        ----
        client (Client): The discord bot client
        _manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        _generator (DataGenerator): Card data generator
        """
        self.client: Client = client

    @slash_command()
    async def util(self: UtilExt, _: SlashContext) -> None:
        """Commands for the bot."""

    @util.subcommand()
    async def ping(self: UtilExt, ctx: SlashContext) -> None:
        """Get the latency of the bot."""
        await ctx.send(f"Pong!\nLatency:{round(self.client.latency, 3)}ms", ephemeral=True)

    @util.subcommand()
    async def stop(self: UtilExt, ctx: SlashContext) -> None:
        """Gracefully shutdown the bot."""
        owner: User | None = self.client.owner
        if not owner:
            await ctx.send("You aren't allowed to do this.", ephemeral=True)
            return
        if ctx.author_id == owner.id:
            await self.client.change_presence(Status.OFFLINE)
            await ctx.send("Stopping!", ephemeral=True)
            await self.client.stop()
        else:
            await ctx.send(f"You aren't allowed to do this ||{owner.mention}||")


def setup(
    client: Client,
    manager: ServerManager,
    scheduler: AsyncIOScheduler,
    generator: DataGenerator,
) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord bot client
    manager (ServerManager): The server connection manager
    scheduler (AsyncIOScheduler): Event scheduler
    generator (DataGenerator): Card data generator
    """
    return UtilExt(client, manager, scheduler, generator)
