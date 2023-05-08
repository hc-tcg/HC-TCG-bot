from interactions import Extension, Client, CommandContext, Embed, Role, extension_command, get

class adminExt(Extension):
    def __init__(self, client:Client) -> None:
        pass

    #@extension_command()
    async def admin():
        """Commands linked to the administration of of hc-tcg.fly.dev"""

def setup(client):
    return adminExt(client)