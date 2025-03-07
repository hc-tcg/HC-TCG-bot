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
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from numpy import ndarray
from PIL import Image, ImageDraw

from bot.util import TYPE_COLORS, Server, ServerManager, rgb_to_int

LOSS = (198, 43, 43)
WIN = (126, 196, 96)
TIE = (255, 234, 132)


def get_type_color(types: list[str]) -> tuple[float, float, float]:
    """Mix several type colors from a list together."""
    r = 0
    g = 0
    b = 0
    for hermit_type in types:
        try:
            color = TYPE_COLORS[hermit_type]
        except KeyError:
            color = (0, 0, 0)  # Black if type not found
        r += color[0]
        g += color[1]
        b += color[2]

    return (round(r / len(types)), round(g / len(types)), round(b / len(types)))


def reduce_rgb(color: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert a 0->255 rgb tuple into a 0->1 rgb tuple."""
    r = color[0] / 255
    g = color[1] / 255
    b = color[2] / 255
    return (r, g, b)


class StatsFailureError(Exception):
    """Failure in generating stats."""


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

        self.icons: dict[str, ndarray] | None = None
        self.small_icons: dict[str, ndarray] | None = None

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
            color = WIN
        elif tie_rate > loss_rate:
            color = TIE
        else:
            color = LOSS

        bar = Image.new("RGBA", (200, 30), LOSS)
        drawer = ImageDraw.Draw(bar)
        drawer.rectangle((0, 0, floor(bar.width * win_rate), bar.height), WIN)
        if tie_rate != 0:
            drawer.rectangle(
                (
                    floor(bar.width * win_rate),
                    0,
                    floor(bar.width * (win_rate + tie_rate)),
                    bar.height,
                ),
                TIE,
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

    @stats.group("type")
    async def types(self: StatsExt, _ctx: SlashContext) -> None:
        """Type stat commands."""

    @stats.subcommand(group_name="type")
    async def winrate(self: StatsExt, ctx: SlashContext) -> None:
        """Get win rate by type stats."""
        server = self.manager.get_server(ctx.guild_id)

        try:
            result = await self.generate_type_stat(
                server,
                "Win rate",
                "winrate",
                "the average win rate of all decks with at least 1 item card of that type.",
            )
        except StatsFailureError as e:
            await ctx.send(e.args[0], ephemeral=True)
            return
        file_bytes, image, embed = result

        await ctx.send(file=image, embed=embed)
        file_bytes.close()

    @stats.subcommand(group_name="type")
    async def usage(self: StatsExt, ctx: SlashContext) -> None:
        """Get usage by type stats."""
        server = self.manager.get_server(ctx.guild_id)

        try:
            result = await self.generate_type_stat(
                server,
                "Usage",
                "frequency",
                "the average win rate of all decks with at least 1 item card of that type.",
            )
        except StatsFailureError as e:
            await ctx.send(e.args[0], ephemeral=True)
            return
        file_bytes, image, embed = result

        await ctx.send(file=image, embed=embed)
        file_bytes.close()

    async def generate_type_stat(
        self: StatsExt, server: Server, name: str, key: str, description: str
    ) -> tuple[BytesIO, File, Embed]:
        """Generate a bar chart of either win rate or usage by type."""
        stats: list[dict] = (await server.get_type_distribution_stats())["types"]
        if self.icons is None or self.small_icons is None:
            self.icons = {}
            self.small_icons = {}
            icons = await server.get_type_icons()
            if not icons:
                err = "Couldn't find type images"
                raise StatsFailureError(err)
            for hermit_type, pil_icon in icons.items():
                with BytesIO() as image_bytes:
                    pil_icon.resize((25, 25), Image.Resampling.BILINEAR).save(image_bytes, "png")
                    image_bytes.seek(0)
                    img = plt.imread(image_bytes)
                    self.icons[hermit_type] = img
                with BytesIO() as image_bytes:
                    pil_icon.resize((12, 12), Image.Resampling.BILINEAR).save(image_bytes, "png")
                    image_bytes.seek(0)
                    img = plt.imread(image_bytes)
                    self.small_icons[hermit_type] = img

        if stats is None or self.icons is None or self.small_icons is None:
            err = "Couldn't find stats or type images"
            raise StatsFailureError(err)

        stats.sort(key=lambda stat: stat[key], reverse=True)
        plt.figure()
        xs = list(range(len(stats)))
        ys = [float(stat[key] * 100) for stat in stats]
        colors = [reduce_rgb(get_type_color(stat["type"])) for stat in stats]

        plt.bar(xs, ys, color=colors)

        gc = plt.gca()

        for i, types in enumerate(stat["type"] for stat in stats):
            y_offset = 0
            for hermit_type in types:
                ab = AnnotationBbox(
                    OffsetImage(self.small_icons[hermit_type]),
                    (i, 0),
                    xybox=(0, -8 + y_offset),
                    frameon=False,
                    xycoords="data",
                    boxcoords="offset points",
                    pad=0,
                )
                y_offset -= 15
                gc.add_artist(ab)

        if gc.axes is not None:
            gc.axes.get_xaxis().set_ticks([])
        gc.set_ylabel(f"{name} (%)")
        plt.grid(visible=True, axis="y")

        embed = (
            Embed(
                f"{name} by type",
                f"{name} is {description}",
                rgb_to_int(get_type_color(stats[0]["type"])),
                timestamp=datetime.now(tz=timezone.utc),
            )
            .set_footer("Bot by Tyrannicodin")
            .set_image("attachment://graph.png")
        )

        figure_bytes = BytesIO()
        plt.savefig(figure_bytes, format="PNG")
        plt.close()
        figure_bytes.seek(0)
        return figure_bytes, File(figure_bytes, "graph.png"), embed

    @stats.subcommand()
    async def games(self: StatsExt, ctx: SlashContext) -> None:
        """Get game count and average game length."""
        server = self.manager.get_server(ctx.guild_id)

        game_stats = await server.get_game_stats()
        if game_stats is None:
            await ctx.send("Couldn't find game statistics", ephemeral=True)
            return
        count, length = game_stats
        singular = count == 1
        embed = (
            Embed("Game history")
            .add_field(f"Game{"" if singular else "s"} played", str(count))
            .add_field("Average length", length)
        )
        await ctx.send(embed=embed)


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
