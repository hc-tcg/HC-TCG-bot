"""Commands for matches."""

from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from interactions import (
    Activity,
    ActivityType,
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Extension,
    Message,
    OptionType,
    SlashContext,
    component_callback,
    slash_command,
    slash_option,
)

from bot.util import DataGenerator, QueueGame, Server, ServerManager


class GameExt(Extension):
    """Commands linked to games."""

    def __init__(
        self: "GameExt",
        client: Client,
        manager: ServerManager,
        data_generator: DataGenerator,
        scheduler: AsyncIOScheduler,
        **_1: dict[str, Any],
    ) -> None:
        """Commands linked to games.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The manager for all servers the bot is in
        data_generator (DataGenerator): The card data generator
        scheduler (AsyncIOScheduler): The job scheduler
        """
        self.client: Client = client
        self.manager: ServerManager = manager
        self.data_generator: DataGenerator = data_generator
        self.scheduler: AsyncIOScheduler = scheduler

        self.scheduler.add_job(self.update_status, IntervalTrigger(minutes=1))

        self.games: dict[str, QueueGame] = {}

    @slash_command()
    async def game(self: "GameExt", _: SlashContext) -> None:
        """Commands linked to games."""

    @game.subcommand()
    @slash_option(
        "spectators", "Should the spectator code be shown", OptionType.BOOLEAN
    )
    async def create(
        self: "GameExt", ctx: SlashContext, *, spectators: bool = False
    ) -> None:
        """Create a match for someone to join."""
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send(
                "Couldn't find an online server for this discord!", ephemeral=True
            )
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]

        game: QueueGame = server.create_game()

        cancel_button = Button(
            style=ButtonStyle.GRAY, label="Cancel", emoji="🚫", custom_id="cancel_game"
        )

        message: Message = await ctx.send(
            embed=game.create_embed(spectators=spectators), components=cancel_button
        )
        self.games[str(message.id)] = game

    @component_callback("cancel_game")
    async def cancel_game(self: "GameExt", ctx: ComponentContext) -> None:
        """Cancel a game."""
        if str(ctx.message_id) not in self.games.keys():
            await ctx.send("Couldn't find game.", ephemeral=True)
            return

        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send(
                "Couldn't find an online server for this discord!", ephemeral=True
            )
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]

        target_game = self.games[str(ctx.message_id)]
        server.cancel_game(target_game)
        await ctx.send("Cancelled game")

    @game.subcommand()
    async def count(self: "GameExt", ctx: ComponentContext) -> None:
        """Get the number of games being played on this server."""
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send(
                "Couldn't find an online server for this discord!", ephemeral=True
            )
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]

        await ctx.send(f"There are {server.get_game_count()} games on this server")

    async def update_status(self: "GameExt") -> None:
        """Update the bots status."""
        server: int = sum(server.get_game_count() for server in self.manager.servers)
        await self.client.change_presence(
            activity=Activity(
                f"{server} games", ActivityType.WATCHING, self.data_generator.url
            )
        )
