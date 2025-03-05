"""Get information about cards and decks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime as dt
from datetime import timezone
from itertools import islice
from math import ceil, sqrt

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


def take(items: int, iterable: Iterable) -> list:
    """Return first `items` items of the iterable as a list."""
    return list(islice(iterable, items))


beige = (226, 202, 139)


def count(s: str) -> str:
    """Count the number of items required."""
    final = []
    for k, v in Counter(s).most_common():
        final.append(f"{v}x {k}")
    return ", ".join(final) if len(final) else "None"


def best_factors(number: int) -> tuple[int, int]:
    """Get as close to being square as possible."""
    x = sqrt(number) // 1
    return ceil(x), ceil(x if number - x**2 == 0 else (number - x**2) / x + x)


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
            color: int = 0
            if achievement.border_color:
                color = hex_to_int(achievement.border_color)
            e = Embed(
                title=achievement.name,
                description=achievement.description,
                timestamp=dt.now(tz=timezone.utc),
                color=color,
            )
            if progress is None:
                e.add_field("Steps", str(achievement.steps), inline=True)
            else:
                e.add_field("Progress", f"{progress}/{achievement.steps}")
            e.add_field(
                "Global progress",
                f"{await server.get_global_achievement_progress(achievement)}%",
                inline=True,
            )
            if achievement.image_url:
                e.set_thumbnail(achievement.image_url)
            e.set_footer("Bot by Tyrannicodin16")
            await ctx.send(embeds=e)
        else:
            await ctx.send("Couldn't find that card!", ephemeral=True)


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
