from interactions import Extension, Member, SlashContext, OptionType, slash_option, slash_command
from json import load, dump

class dotdExt(Extension):
    def __init__(self, client, fp) -> None:
        self.fp = fp
        self.client = client
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
    async def dotd(self, ctx:SlashContext):
        """Commands for the weekly dotd tournaments list"""

    @dotd.subcommand()
    @slash_option("user", "The user to add to the dotd list", OptionType.USER)
    async def add(self, ctx:SlashContext, user:Member):
        self.data.append(int(user.id))
        self.save()
        await ctx.send("Successfully added user", ephemeral=True)

    @dotd.subcommand()
    @slash_option("user", "The user to remove from the dotd list", OptionType.USER)
    async def remove(self, ctx:SlashContext, user:Member):
        try:
            idx = self.data.index(int(user.id))
            self.data.pop(idx)
            self.save()
            await ctx.send("Successfully removed user", ephemeral=True)
        except ValueError:
            await ctx.send("Couldn't find that user", ephemeral=True)

    @dotd.subcommand()
    async def clear(self, ctx:SlashContext):
        self.data = []
        self.save()
        await ctx.send("Successfully cleared users", ephemeral=True)

    @dotd.subcommand()
    async def list(self, ctx:SlashContext):
        resp = "Users currently in dotd tournament:\n"
        for user in self.data:
            resp += (await self.client.get_member(ctx.guild_id, user)).name + "\n"
        resp.rstrip("\n")
        await ctx.send(resp)

def setup(client, fp):
    return dotdExt(client, fp)