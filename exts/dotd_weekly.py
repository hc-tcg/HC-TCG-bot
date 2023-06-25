from interactions import (
    Extension,
    Member,
    Client,
    SlashContext,
    OptionType,
    slash_option,
    slash_command,
)
from json import load, dump


class dotdWeeklyExt(Extension):
    def __init__(self, client, config) -> None:
        self.fp = config["files"]["dotd"]
        self.client: Client = client
        self.load()

    def load(self):
        try:
            with open(self.fp, "r") as f:
                self.data = load(f)
        except FileNotFoundError:
            open(self.fp, "w").close()
            self.data = []
            self.save()

    def save(self):
        with open(self.fp, "w") as f:
            dump(self.data, f)

    @slash_command()
    async def dotd_weekly(self, ctx: SlashContext):
        """Commands for the dotd weekly tournaments list"""

    @dotd_weekly.subcommand()
    @slash_option(
        "user", "The user to add to the dotd weekly list", OptionType.USER, True
    )
    async def add(self, ctx: SlashContext, user: Member):
        """Add a user to the dotd weekly tournament list"""
        self.data.append(int(user.id))
        self.save()
        await ctx.send("Successfully added user", ephemeral=True)

    @dotd_weekly.subcommand()
    @slash_option(
        "user", "The user to remove from the dotd weekly list", OptionType.USER, True
    )
    async def remove(self, ctx: SlashContext, user: Member):
        """Remove a user from the dotd weekly tournament list"""
        try:
            idx = self.data.index(int(user.id))
            self.data.pop(idx)
            self.save()
            await ctx.send("Successfully removed user", ephemeral=True)
        except ValueError:
            await ctx.send("Couldn't find that user", ephemeral=True)

    @dotd_weekly.subcommand()
    async def clear(self, ctx: SlashContext):
        """Clear the dotd weekly tournament list"""
        self.data = []
        self.save()
        await ctx.send("Successfully cleared users", ephemeral=True)

    @dotd_weekly.subcommand()
    async def list(self, ctx: SlashContext):
        """List the users in the dotd weekly tournament"""
        resp = "Users currently in dotd weekly tournament:\n"
        for user in self.data:
            resp += (
                await self.client.fetch_member(user, ctx.guild_id)
            ).display_name + "\n"
        resp.rstrip("\n")
        await ctx.send(resp)


def setup(client, **kwargs):
    return dotdWeeklyExt(client, **kwargs)
