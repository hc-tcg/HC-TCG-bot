"""Commands for recording dotd results."""
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

from util import ServerManager


class DotdExt(Extension):

    """Commands for recording dotd results."""

    def __init__(self: "DotdExt", client: Client, manager: ServerManager) -> None:
        """Commands for recording dotd results."""
        self.client: Client = client
        self.data: dict[int, tuple[int, int, int, int]] = {}
        self.manager = manager

    @slash_command()
    async def dotd(self: "DotdExt", _: SlashContext) -> None:
        """Commands for recording dotd results."""

    @dotd.subcommand()
    @slash_option(
        "wins", "The number of games you won", OptionType.INTEGER, required=True
    )
    @slash_option(
        "ties", "The number of games you tied (can be blank)", OptionType.INTEGER
    )
    async def submit(
        self: "DotdExt", ctx: SlashContext, wins: int, ties: int = 0
    ) -> None:
        """Submit a dotd result, this will overwrite any previous results."""
        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        self.data[str(ctx.author_id)] = (
            str(ctx.author_id),
            wins,
            ties,
            5 - wins - ties,
        )
        await ctx.send(
            f"{ctx.author.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses"  # noqa: E501
        )

    @dotd.subcommand()
    @slash_option("player", "The player to add", OptionType.USER, required=True)
    @slash_option(
        "wins", "The number of games the player won", OptionType.INTEGER, required=True
    )
    @slash_option(
        "ties", "The number of games the player tied (can be blank)", OptionType.INTEGER
    )
    async def add_other(
        self: "DotdExt", ctx: SlashContext, player: Member, wins: int, ties: int = 0
    ) -> None:
        """Add a score for a player that is not you."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if not self.manager.discord_links[str(ctx.guild_id)].authorize_user(ctx.member):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        self.data[str(player.id)] = (str(player.id), wins, ties, 5 - wins - ties)
        await ctx.send(
            f"{player.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses",
            ephemeral=True,
        )

    @dotd.subcommand("list")
    async def list_results(self: "DotdExt", ctx: SlashContext) -> None:
        """List today's dotd results."""
        reversed_data: dict[tuple[int, int, int, int], int] = {
            value: key for key, value in self.data.items()
        }
        data_sorted: list[tuple[int, int, int, int]] = list(self.data.values())
        data_sorted.sort(key=lambda x: (-x[1], -x[2]))
        output: str = ""
        for i, user in enumerate(data_sorted, 1):
            discord_member: Member = await self.client.fetch_member(
                reversed_data[user], ctx.guild_id
            )
            if not discord_member:
                discord_member: User = await self.client.fetch_user(reversed_data[user])
            output: str = f"{output}\n{i}. {discord_member.display_name} - {user[1]} wins, {user[2]} ties and {user[3]} losses"  # noqa: E501
        if output:
            await ctx.send(output)
        else:
            await ctx.send("No results submitted yet", ephemeral=True)

    @dotd.subcommand()
    async def clear(self: "DotdExt", ctx: SlashContext) -> None:
        """Clear all results."""
        if ctx.member is None:
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if not self.manager.discord_links[str(ctx.guild_id)].authorize_user(ctx.member):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        self.data: dict[int, tuple[int, int, int, int]] = {}
        await ctx.send("Cleared all results")


def setup(client: Client, **kwargs: dict) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord client
    **kwargs (dict): Dictionary containing additional arguments
    """
    return DotdExt(client, **kwargs)
