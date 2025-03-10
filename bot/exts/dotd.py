"""Commands for recording dotd results."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import (
    Client,
    Extension,
    Member,
    OptionType,
    SlashContext,
    User,
    slash_command,
    slash_option,
)

from bot.util import ServerManager


class DotdExt(Extension):
    """Commands for recording dotd results."""

    def __init__(
        self: DotdExt,
        client: Client,
        manager: ServerManager,
        _scheduler: AsyncIOScheduler,
    ) -> None:
        """Commands for recording dotd results.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The server connection manager
        _scheduler (AsyncIOScheduler): Event scheduler
        _generator (DataGenerator): Card data generator
        """
        self.client: Client = client
        self.manager = manager

        self.data: dict[str, tuple[int, int, int]] = {}

    @slash_command()
    async def dotd(self: DotdExt, _: SlashContext) -> None:
        """Commands for recording dotd results."""

    @dotd.subcommand()
    @slash_option("wins", "The number of games you won", OptionType.INTEGER, required=True)
    @slash_option("ties", "The number of games you tied (can be blank)", OptionType.INTEGER)
    async def submit(self: DotdExt, ctx: SlashContext, wins: int, ties: int = 0) -> None:
        """Submit a dotd result, this will overwrite any previous results."""
        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        self.data[str(ctx.author_id)] = (
            wins,
            ties,
            5 - wins - ties,
        )
        await ctx.send(
            f"{ctx.author.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses"
        )

    @dotd.subcommand()
    @slash_option("player", "The player to add", OptionType.USER, required=True)
    @slash_option("wins", "The number of games the player won", OptionType.INTEGER, required=True)
    @slash_option("ties", "The number of games the player tied (can be blank)", OptionType.INTEGER)
    async def add_other(
        self: DotdExt, ctx: SlashContext, player: Member, wins: int, ties: int = 0
    ) -> None:
        """Add a score for a player that is not you."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if not self.manager.get_server(ctx.guild_id).authorize_user(ctx.member, allow_dotd=True):
            await ctx.send("You can't do that!", ephemeral=True)
            return

        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        self.data[str(player.id)] = (wins, ties, 5 - wins - ties)
        await ctx.send(
            f"{player.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses",
            ephemeral=True,
        )

    @dotd.subcommand("list")
    async def list_results(self: DotdExt, ctx: SlashContext) -> None:
        """List today's dotd results."""
        reversed_data: dict[tuple[int, int, int], str] = {
            value: key for key, value in self.data.items()
        }
        data_sorted: list[tuple[str, int, int, int]] = [
            (key, *value) for key, value in self.data.items()
        ]

        data_sorted.sort(key=lambda x: (-x[1], -x[2]))
        output: str = ""
        for i, user in enumerate(data_sorted, 1):
            discord_member: User | Member | None = await self.client.fetch_member(
                reversed_data[user[1:4]], ctx.guild_id
            )
            if not discord_member:
                discord_member = await self.client.fetch_user(reversed_data[user[1:4]])
            output = (
                f"{output}\n{i}. {discord_member.display_name if discord_member else user[0]} - "
                + f"{user[1]} wins, {user[2]} ties and {user[3]} losses"
            )
        if output:
            await ctx.send(output)
        else:
            await ctx.send("No results submitted yet", ephemeral=True)

    @dotd.subcommand()
    async def clear(self: DotdExt, ctx: SlashContext) -> None:
        """Clear all results."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        server = self.manager.get_server(ctx.guild_id)
        if not server.authorize_user(ctx.member, allow_dotd=True):
            await ctx.send("You can't do that!", ephemeral=True)
            return

        await ctx.send("Clearing results and assigning role.")

        if not server.dotd_winner:
            return
        role = ctx.guild.get_role(server.dotd_winner)
        if not role:
            return

        for member in role.members:
            await member.remove_role(role)

        data_sorted: list[tuple[str, int, int, int]] = [
            (key, *value) for key, value in self.data.items()
        ]
        if len(data_sorted) == 0:
            self.data = {}
            return

        data_sorted.sort(key=lambda x: (-x[1], -x[2]))

        best_result = data_sorted[0][1:4]
        for user in data_sorted:
            if best_result != user[1:4]:
                break
            discord_member: User | Member | None = await self.client.fetch_member(
                user[0], ctx.guild_id
            )
            if type(discord_member) is not Member:
                continue
            await discord_member.add_role(role)

        self.data = {}


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
    generator (DataGenerator): Card data generator
    """
    return DotdExt(client, manager, scheduler)
