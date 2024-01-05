"""Commands for matches."""

from interactions import (
    Client,
    ComponentContext,
    Extension,
    GuildText,
    OptionType,
    SlashContext,
    component_callback,
    slash_command,
    slash_option,
)

from util import Match, MatchStateEnum, Server, ServerManager


class MatchExt(Extension):
    """Commands for creating matches."""

    def __init__(self: "MatchExt", client: Client, manager: ServerManager) -> None:
        """Commands linked to the administration of a server.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The manager for all servers the bot is in
        """
        self.client: Client = client
        self.manager: ServerManager = manager
        self.games: dict[str, Match] = {}

    @slash_command()
    @slash_option(
        "first_to", "First to how many games", OptionType.INTEGER, required=True
    )
    async def match(self: "MatchExt", ctx: SlashContext, first_to: int) -> None:
        """Create a public match for someone to join."""
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send(
                "Couldn't find an online server for this discord!", ephemeral=True
            )
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]
        if ctx.channel is not GuildText:
            await ctx.send("Can't create games in threads sorry!", ephemeral=True)
            return

        new_match = Match(self.client, ctx, server, first_to)
        await new_match.send_message()
        self.games[new_match.id] = new_match

    @component_callback("join_game")
    async def join_game(self: "MatchExt", ctx: ComponentContext) -> None:
        """Add a player to a match."""
        if str(ctx.message_id) not in self.games.keys():
            await ctx.send("Couldn't find game.", ephemeral=True)
            return
        target_match = self.games[str(ctx.message_id)]
        if (
            len(target_match.players) >= 2
            or target_match.state != MatchStateEnum.WAITING_FOR_PLAYERS
        ):
            await ctx.send("You can't join this game.", ephemeral=True)
            return
        target_match.players.append(str(ctx.author_id))
        await target_match.thread.add_member(ctx.author)
        await ctx.send("Joined game.", ephemeral=True)

        if len(target_match.players) == 2:
            await target_match.start_game()

    @component_callback("leave_game")
    async def leave_game(self: "MatchExt", ctx: ComponentContext) -> None:
        """Remove a player from a match."""
        if str(ctx.message_id) not in self.games.keys():
            await ctx.send("Couldn't find game.", ephemeral=True)
            return
        target_match = self.games[str(ctx.message_id)]
        if str(ctx.author_id) not in target_match.players:
            await ctx.send("You aren't in this game.", ephemeral=True)
            return
        target_match.players.remove(str(ctx.author_id))
        await target_match.thread.remove_member(ctx.author)
        await ctx.send("Left game", ephemeral=True)
