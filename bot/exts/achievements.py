"""Get information about cards and decks."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime as dt
from datetime import timezone
from itertools import islice
from math import floor, log10

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import (
    AutocompleteContext,
    Client,
    Embed,
    Extension,
    OptionType,
    SlashContext,
    global_autocomplete,
    slash_command,
    slash_option,
)

from bot.util import ServerManager, rgb_to_int
from bot.util.datagen import hex_to_int


#https://mattgosden.medium.com/rounding-to-significant-figures-in-python-2415661b94c3
def sig_figs(x: float, precision: int) -> float:
    """Round a number to a given significant figure.

    Args:
    ----
    x (float): the number to be rounded
    precision (int): the number of significant figures
    """
    if x == 0:
        return 0

    x = float(x)
    precision = int(precision)

    return round(x, -int(floor(log10(abs(x)))) + (precision - 1))

ACHIEVEMENT_LOW_PERCENT = (208, 180, 86)
ACHIEVEMENT_HIGH_PERCENT = (86, 184, 208)


def linear_interpolate(
    low: tuple[int, int, int] = ACHIEVEMENT_LOW_PERCENT,
    high: tuple[int, int, int] = ACHIEVEMENT_HIGH_PERCENT,
    r: float = 0,
) -> int:
    """Interpolate between 2 rgb colors.

    Args:
    ----
    low (tuple): The color when r is 0
    high (tuple): The coolor when r is 1
    r (float): The ratio  between low and high
    """
    rl, gl, bl = low
    rh, gh, bh = high
    rf = rl + round((rh - rl) * r)
    gf = gl + round((gh - gl) * r)
    bf = bl + round((bh - bl) * r)
    return rgb_to_int((rf, gf, bf))


def take(items: int, iterable: Iterable) -> list:
    """Return first `items` items of the iterable as a list."""
    return list(islice(iterable, items))


class AchievementExt(Extension):
    """Get information about cards and decks."""

    def __init__(
        self: AchievementExt,
        _: Client,
        manager: ServerManager,
        _scheduler: AsyncIOScheduler,
    ) -> None:
        """Get information about cards and decks.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        """
        self.manager: ServerManager = manager

    @global_autocomplete("achievement_name")
    async def achievement_autocomplete(self: AchievementExt, ctx: AutocompleteContext) -> None:
        """Autocomplete an achievement name."""
        server = self.manager.get_server(ctx.guild_id)
        if not ctx.input_text:
            await ctx.send(
                [
                    achievement.name
                    for achievement in take(25, server.data_generator.achievement_universe)
                ]
            )
            return
        await ctx.send(
            [
                card.name
                for card in server.data_generator.achievement_universe
                if ctx.input_text.lower() in card.name.lower()
            ][0:25]
        )

    @slash_command()
    async def achievement(self: AchievementExt, _: SlashContext) -> None:
        """Get information about achievements."""

    @achievement.subcommand()
    @slash_option(
        "achievement_name",
        "The achievement to get",
        OptionType.STRING,
        required=True,
        autocomplete=True,
    )
    @slash_option("uuid", "Player uuid to get progress of", OptionType.STRING)
    async def info(
        self: AchievementExt, ctx: SlashContext, achievement_name: str, uuid: str = ""
    ) -> None:
        """Get information about cards and decks."""
        server = self.manager.get_server(ctx.guild_id)
        progress = None
        achievements = [
            achievement
            for achievement in server.data_generator.achievement_universe
            if achievement_name.lower() in achievement.name.lower()
        ]
        achievements.sort(key=lambda val: val.name)
        if len(achievements) > 0:
            achievement = achievements[0]
            if uuid != "":
                progress = await server.get_player_achievement_progress(uuid, achievement)
                if progress is None:
                    await ctx.send("Couldn't find that user!", ephemeral=True)
                    return
            global_percent, global_count = await server.get_global_achievement_progress(achievement)
            e = Embed(
                title=achievement.name,
                description=achievement.description,
                timestamp=dt.now(tz=timezone.utc),
            )

            if progress is None:
                e.add_field("Steps", str(achievement.steps), inline=True)
            else:
                e.add_field("Progress", f"{progress}/{achievement.steps}")

            if global_percent is not None:
                e.color = linear_interpolate(r=global_percent / 100)
                plural: str = "" if global_count == 1 else "s"
                e.add_field(
                    "Global progress",
                    f"{sig_figs(global_percent, 4)}% ({global_count} player{plural})",
                    inline=True,
                )

            if achievement.border_color:
                e.color = hex_to_int(achievement.border_color)
            if achievement.image_url:
                e.set_thumbnail(achievement.image_url)

            e.set_footer("Bot by Tyrannicodin16")
            await ctx.send(embeds=e)
        else:
            await ctx.send("Couldn't find that achievement!", ephemeral=True)


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
    return AchievementExt(client, manager, scheduler)
