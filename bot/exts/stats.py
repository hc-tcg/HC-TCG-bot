"""Get information about cards and decks."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from math import floor

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import (
    Client,
    Embed,
    Extension,
    File,
    OptionType,
    SlashContext,
    slash_command,
    slash_option,
)
from PIL import Image, ImageDraw

from bot.util import ServerManager, rgb_to_int

RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (0, 255, 0)


class StatsExt(Extension):
    """Get game and player stats."""

    def __init__(
        self: StatsExt,
        client: Client,
        manager: ServerManager,
        _scheduler: AsyncIOScheduler,
    ) -> None:
        """Get game and player stats.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        """
        self.client: Client = client
        self.manager: ServerManager = manager

    @slash_command()
    async def stats(self: StatsExt, _ctx: SlashContext) -> None:
        """Get game and player stats."""

    @stats.subcommand()
    @slash_option(
        "uuid",
        "Target players uuid",
        OptionType.STRING,
        required=True,
        min_length=36,
        max_length=36,
    )
    @slash_option("forfeits", "Include forfeit stats", OptionType.BOOLEAN)
    @slash_option("hide_uuid", "If the players's uuid should be hidden", OptionType.BOOLEAN)
    async def player(
        self: StatsExt,
        ctx: SlashContext,
        uuid: str,
        *,
        forfeits: bool = True,
        hide_uuid: bool = False,
    ) -> None:
        """Get a player's stats from their uuid."""
        server = self.manager.get_server(ctx.guild_id)

        stats = await server.get_player_stats(uuid)
        if stats is None:
            await ctx.send("Couldn't find a player with that uuid", ephemeral=True)
            return

        if hide_uuid:
            await ctx.send("This message handily obscures your uuid!", ephemeral=True)

        games = stats["gamesPlayed"] - (
            0 if forfeits else stats["forfeitWins"] + stats["forfeitLosses"]
        )
        wins = stats["wins"] + stats["forfeitWins"] if forfeits else 0
        losses = stats["losses"] + stats["forfeitLosses"] if forfeits else 0
        ties = stats["ties"]

        win_rate = wins / games
        tie_rate = ties / games
        loss_rate = losses / games

        color: tuple[int, int, int]
        if win_rate > tie_rate and win_rate > loss_rate:
            color = BLUE
        elif tie_rate > loss_rate:
            color = GRAY
        else:
            color = RED

        bar = Image.new("RGBA", (200, 30), RED)
        drawer = ImageDraw.Draw(bar)
        drawer.rectangle((0, 0, floor(bar.width * win_rate), bar.height), BLUE)
        if tie_rate != 0:
            drawer.rectangle(
                (
                    floor(bar.width * win_rate),
                    0,
                    floor(bar.width * (win_rate + tie_rate)),
                    bar.height,
                ),
                GRAY,
            )

        embed = (
            Embed(
                "Player stats",
                f"{games} game{"" if games == 1 else "s"} played.",
                rgb_to_int(color),
                timestamp=datetime.now(tz=timezone.utc),
            )
            .set_footer("Bot by Tyrannicodin")
            .add_field("Win rate", f"{win_rate:.2%}")
            .add_field("Loss rate", f"{loss_rate:.2%}")
            .set_image("attachment://bar.png")
        )
        with BytesIO() as im_binary:
            bar.save(im_binary, "PNG")
            im_binary.seek(0)
            await ctx.send(embed=embed, file=File(im_binary, "bar.png"))


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
    return StatsExt(client, manager, scheduler)
