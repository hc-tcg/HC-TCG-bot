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


class dotdExt(Extension):
    def __init__(self, client, authed) -> None:
        self.client: Client = client
        self.data: dict[int, tuple[int, int, int]] = {}
        self.authed = authed

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
        self.data[int(ctx.author_id)] = (wins, ties, 5 - wins - ties)
        await ctx.send(
            f"Recorded result: {wins} wins, {ties} ties and {5-wins-ties} losses",
            ephemeral=True,
        )

    @dotd.subcommand("list")
    async def list_results(self, ctx: SlashContext):
        """List today's dotd results"""
        reversedData: dict[tuple[int, int, int], int] = {
            value: key for key, value in self.data.items()
        }
        dataSorted: list[tuple[int, int, int]] = list(self.data.values())
        dataSorted.sort(key=lambda x: x[0])
        output: str = ""
        for i, user in enumerate(dataSorted):
            discordMember: User = await self.client.fetch_user(reversedData[user])
            output: str = (
                f"{output}\n{i}. {discordMember.display_name} - {user[0]} wins"
            )
        if output:
            await ctx.send(output)
        else:
            await ctx.send("No results submitted yet", ephemeral=True)

    @dotd.subcommand()
    async def clear(self, ctx: SlashContext):
        if (
            int(ctx.author_id) in self.authed
            or int(ctx.guild_id) in self.authed
            or any((True for role in ctx.author.roles if role.id in self.authed))
        ):
            await ctx.send("Cleared all results")
        else:
            await ctx.send(
                "You don't have permissions to clear the results", ephemeral=True
            )


def setup(client, authed):
    return dotdExt(client, authed)
