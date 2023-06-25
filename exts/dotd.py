from interactions import (
    Extension,
    Member,
    User,
    Client,
    SlashContext,
    OptionType,
    slash_option,
    slash_command,
)

from util import validate_user


class dotdExt(Extension):
    def __init__(self, client, config) -> None:
        self.client: Client = client
        self.data: dict[int, tuple[int, int, int, int]] = {}
        self.permissions = config["permissions"]

    @slash_command()
    async def dotd(self, ctx: SlashContext):
        """Commands for recording dotd results"""

    @dotd.subcommand()
    @slash_option("wins", "The number of wins you got", OptionType.INTEGER, True)
    @slash_option(
        "ties", "The number of ties you got (can be blank)", OptionType.INTEGER
    )
    async def submit(self, ctx: SlashContext, wins: int, ties: int = 0):
        """Submit a dotd result, will overwrite any previous results"""
        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        self.data[int(ctx.author_id)] = (
            int(ctx.author_id),
            wins,
            ties,
            5 - wins - ties,
        )
        await ctx.send(
            f"{ctx.author.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses",
        )

    @dotd.subcommand()
    @slash_option("player", "The player to add", OptionType.USER, True)
    @slash_option("wins", "The number of wins you got", OptionType.INTEGER, True)
    @slash_option(
        "ties", "The number of ties you got (can be blank)", OptionType.INTEGER
    )
    async def add_other(
        self, ctx: SlashContext, player: Member, wins: int, ties: int = 0
    ):
        if not validate_user(ctx.author, ctx.guild, self.permissions):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if wins > 5 or ties > 5 - wins or wins < 0 or ties < 0:
            await ctx.send("Invalid wins or ties", ephemeral=True)
            return
        if (
            int(ctx.author_id) in self.permissions
            or int(ctx.guild_id) in self.permissions
            or any((True for role in ctx.author.roles if role.id in self.permissions))
        ):
            self.data[player.id] = (int(player.id), wins, ties, 5 - wins - ties)
            await ctx.send(
                f"{player.display_name}: {wins} wins, {ties} ties and {5-wins-ties} losses",
            )
            return
        await ctx.send("You can't do that", ephemeral=True)

    @dotd.subcommand("list")
    async def list_results(self, ctx: SlashContext):
        """List today's dotd results"""
        reversedData: dict[tuple[int, int, int, int], int] = {
            value: key for key, value in self.data.items()
        }
        dataSorted: list[tuple[int, int, int, int]] = list(self.data.values())
        dataSorted.sort(key=lambda x: (-x[1], -x[2]))
        output: str = ""
        for i, user in enumerate(dataSorted, 1):
            discordMember: Member = await self.client.fetch_member(
                reversedData[user], ctx.guild_id
            )
            if not discordMember:
                discordMember: User = await self.client.fetch_user(reversedData[user])
            output: str = f"{output}\n{i}. {discordMember.display_name} - {user[1]} wins, {user[2]} ties and {user[3]} losses"
        if output:
            await ctx.send(output)
        else:
            await ctx.send("No results submitted yet", ephemeral=True)

    @dotd.subcommand()
    async def clear(self, ctx: SlashContext):
        """Clear all results"""
        if not validate_user(ctx.author, ctx.guild, self.permissions):
            await ctx.send("You can't do that!", ephemeral=True)
            return
        if (
            int(ctx.author_id) in self.permissions
            or int(ctx.guild_id) in self.permissions
            or any((True for role in ctx.author.roles if role.id in self.permissions))
        ):
            self.data: dict[int, tuple[int, int, int, int]] = dict()
            await ctx.send("Cleared all results")
        else:
            await ctx.send(
                "You don't have permissions to clear the results", ephemeral=True
            )


def setup(client, **kwargs):
    return dotdExt(client, **kwargs)
