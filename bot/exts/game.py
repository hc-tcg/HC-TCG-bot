"""Commands for matches."""

from __future__ import annotations

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
    PartialEmoji,
    SlashContext,
    component_callback,
    slash_command,
    slash_option,
)

from bot.util import QueueGame, Server, ServerManager


class GameExt(Extension):
    """Commands linked to games."""

    def __init__(
        self: GameExt,
        client: Client,
        manager: ServerManager,
        scheduler: AsyncIOScheduler,
    ) -> None:
        """Commands linked to games.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        scheduler (AsyncIOScheduler): Event scheduler
        """
        self.client: Client = client
        self.manager: ServerManager = manager
        self.scheduler: AsyncIOScheduler = scheduler

        self.scheduler.add_job(self.update_status, IntervalTrigger(minutes=1))

        self.games: dict[str, QueueGame] = {}

    @slash_command()
    async def game(self: GameExt, _: SlashContext) -> None:
        """Commands linked to games."""

    @game.subcommand()
    @slash_option("spectators", "Should the spectator code be shown", OptionType.BOOLEAN)
    async def create(self: GameExt, ctx: SlashContext, *, spectators: bool = False) -> None:
        """Create a match for someone to join."""
        server: Server = self.manager.get_server(ctx.guild_id)

        game: QueueGame | None = await server.create_game()
        if not game:
            await ctx.send("Failed to create a game, seems to be a server problem.")
            return

        cancel_button = Button(
            style=ButtonStyle.GRAY, label="Cancel", emoji="🚫", custom_id="cancel_game"
        )

        join_button = Button(style=ButtonStyle.URL, label="Join", emoji="▶️", url=game.join_url)

        spectate_button: Button = Button(
            style=ButtonStyle.URL,
            label="Spectate",
            emoji="🔎",
            url=game.spectate_url,
            disabled=not spectators,
        )

        message: Message = await ctx.send(
            embed=game.create_embed(spectators=spectators),
            components=[cancel_button, join_button, spectate_button],
        )
        self.games[str(message.id)] = game

    @component_callback("cancel_game")
    async def cancel_game(self: GameExt, ctx: ComponentContext) -> None:
        """Cancel a game."""
        server: Server = self.manager.get_server(ctx.guild_id)
        if not (server.authorize_user(ctx.member) or ctx.message.author.id == ctx.author):
            await ctx.send("You are not allowed to cancel this game!", ephemeral=True)
            return
        if str(ctx.message_id) not in self.games.keys():
            await ctx.send("Couldn't find game.", ephemeral=True)
            return

        target_game = self.games[str(ctx.message_id)]
        self.games.pop(str(ctx.message_id))
        if not await server.cancel_game(target_game):
            await ctx.send("Server couldn't cancel game!", ephemeral=True)
            return
        await ctx.send("Cancelled game")

    @game.subcommand()
    async def count(self: GameExt, ctx: ComponentContext) -> None:
        """Get the number of games being played on this server."""
        server: Server = self.manager.get_server(ctx.guild_id)

        game_count = await server.get_game_count()

        if game_count == 1:
            game_message = "is 1 game"
        else:
            game_message = f"are {game_count} games"

        await ctx.send(f"There {game_message} on this server")

    async def update_status(self: GameExt) -> None:
        """Update the bots status."""
        game_count: int = 0
        queue_length: int = 0

        for server in self.manager.servers:
            game_count += await server.get_game_count()
            queue_length += await server.get_queue_length()

        if game_count == 1:
            game_word = "game"
        else:
            game_word = "games"

        if queue_length == 1:
            queue_word = "player queued"
        else:
            queue_word = "players queued"

        if queue_length != 0 and game_count != 0:
            message = f"{game_count} {game_word}, {queue_length} {queue_word}"
        else:
            message = f"{game_count} {game_word}"

        await self.client.change_presence(
            activity=Activity(
                message,
                ActivityType.CUSTOM,
                self.manager.servers[0].server_url,
                state=message,
                emoji=PartialEmoji("1075864519399706754", "bdubs"),
            )
        )


def setup(
    client: Client,
    manager: ServerManager,
    scheduler: AsyncIOScheduler,
) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord bot client
    manager (ServerManager): The server connection manager
    scheduler (AsyncIOScheduler): Event scheduler
    """
    return GameExt(client, manager, scheduler)
