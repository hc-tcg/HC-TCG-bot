"""Commands linked to the administration of a server."""
from datetime import datetime as dt

from interactions import (
    Client,
    Embed,
    Extension,
    OptionType,
    SlashContext,
    slash_command,
    slash_option,
)
from interactions.ext.paginators import Paginator

from util import Server, ServerManager


class AdminExt(Extension):
    """Commands linked to the administration of a server."""

    def __init__(self: "AdminExt", client: Client, manager: ServerManager) -> None:
        """Commands linked to the administration of a server.

        Args:
        ----
        client (Client): The discord bot client
        manager (ServerManager): The manager for all servers the bot is in
        """
        self.client = client
        self.manager = manager

    @slash_command()
    async def admin(self: "AdminExt", ctx: SlashContext) -> None:
        """Commands linked to the administration of a server."""

    @admin.subcommand()
    @slash_option(
        "search",
        "The player name, game id or game code to search for",
        OptionType.STRING,
    )
    async def list_games(self: "AdminExt", ctx: SlashContext, search: str = "") -> None:
        """Get information about all games, or a specific game given `search`."""
        if str(ctx.guild_id) not in self.manager.discord_links.keys():
            await ctx.send(
                "Couldn't find an online server for this discord!", ephemeral=True
            )
            return
        server: Server = self.manager.discord_links[str(ctx.guild_id)]
        if not server.authorize_user(ctx.author):
            await ctx.send("You can't do that!", ephemeral=True)

        data = server.get_games()
        data.sort(key=lambda x: x.created)
        if search != "":
            data = next(
                (
                    game
                    for game in data
                    if game.id == search
                    or search in game.player_names
                    or game.code == search
                ),
                None,
            )
            if not data:
                await ctx.send(
                    "Couldn't find that game, run without arguments to get all games",
                    ephemeral=True,
                )
                return
            await ctx.send(embeds=data.generate_embed())
            return
        embeds = []
        page_length = len(data) // 10 + (1 if len(data) % 10 > 0 else 0)
        for i in range(page_length):
            e = Embed(
                title=f"Active games ({i*10+1} - {(i+1)*10 if (i+1)*10 < len(data) else len(data)} of {len(data)})",  # noqa: E501
                timestamp=dt.now(None),
            )
            for game in data[i * 10 : (i + 1) * 10]:
                e.add_field(*game.overview(), inline=False)
            embeds.append(e)
        if len(embeds) > 1:
            await Paginator.create_from_embeds(self.client, *embeds, timeout=60).send(
                ctx
            )
        elif len(data) > 0:
            await ctx.send(embeds=embeds[0])
        else:
            await ctx.send(
                embeds=Embed(
                    title="No active games",
                    description="No active games for this server.",
                )
            )


def setup(client: Client, **kwargs: dict) -> Extension:
    """Create the extension.

    Args:
    ----
    client (Client): The discord client
    **kwargs (dict): Dictionary containing additional arguments
    """
    return AdminExt(client, **kwargs)
