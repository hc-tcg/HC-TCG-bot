"""Handles interactions and linking discord and hc-tcg servers."""

from datetime import datetime as dt
from datetime import timezone
from typing import Any, Optional, Union

from interactions import Client, Embed, Member
from requests import delete, exceptions, get


class GamePlayer:
    """A representation of a player in a game."""

    def __init__(self: "GamePlayer", data: dict[str, Any]) -> None:
        """Represent a player in a game.

        Args:
        ----
        data (dict): Player information
        """
        self.id: str = data["playerId"]
        self.name: str = data["censoredPlayerName"]
        self.minecraft_name: str = data["minecraftName"]
        self.lives: int = data["lives"]

        self.deck: list[str] = data["deck"]


class Game:
    """Store data about a game."""

    def __init__(self: "Game", data: dict[str, Any]) -> None:
        """Store data about a game.

        Args:
        ----
        data (dict): The game data dict
        """
        self.players: list[GamePlayer] = [GamePlayer(player) for player in data["players"]]
        self.player_names = [player.name for player in self.players]
        self.id = data["id"]
        self.spectator_code: Optional[str] = data["spectatorCode"]
        self.created: dt = dt.fromtimestamp(data["createdTime"] / 1000, tz=timezone.utc)
        self.spectators = data["viewers"] - len(self.players)

        print(data["state"])


class QueueGame:
    """Information about a private queued game."""

    def __init__(self: "QueueGame", data: dict[str, Any]) -> None:
        """Information about a private queued game.

        Args:
        ----
        data (dict): The game data dict
        """
        self.joinCode: str = data["gameCode"]
        self.spectatorCode: str = data["spectatorCode"]
        self.secret: str = data["apiSecret"]
        self.timeout: str = data["timeOutAt"] / 1000

    def create_embed(self: "QueueGame") -> Embed:
        """Create an embed with information about the game."""
        return (
            Embed("Game", f"Expires <t:{self.timeout:.0F}:T>", timestamp=dt.now(tz=timezone.utc))
            .add_field("Join code", self.joinCode, inline=True)
            .add_field("Spectate code", self.spectatorCode, inline=True)
            .set_footer("Bot by Tyrannicodin16")
        )


class Server:
    """An interface between a discord and hc-tcg server."""

    def __init__(
        self: "Server",
        server_id: str,
        server_url: str,
        guild_id: str,
        admins: Optional[list[str]] = None,
        tracked_forums: Optional[dict[str, list[str]]] = None,
    ) -> None:
        """Create a Server object.

        Args:
        ----
        server_id (str): Unique name for the server
        server_url (str): The url of the hc-tcg server
        server_key (str): The api key to send to the server
        guild_id (str): The id of the discord server
        guild_key (str): The api key sent from the server
        admins (list[str]): List of users and/or roles that can use privileged
        features, if blank allows all users to use privileged features
        tracked_forums (list[str]): Dictionary with channel ids and tags to ignore
        update_channel (str): The channel to get server updates from
        """
        if admins is None:
            admins = []
        if tracked_forums is None:
            tracked_forums = {}

        self.server_id: str = server_id

        self.api_url: str = server_url + "/api"
        self.guild_id: str = guild_id
        self.admin_roles: list[str] = admins
        self.tracked_forums: dict[str, list[str]] = tracked_forums

    def authorize_user(self: "Server", member: Member) -> bool:
        """Check if a user is allowed to use privileged commands."""
        if self.admin_roles is []:
            return True
        admin_user = str(member.id) in self.admin_roles
        admin_role = any(str(role.id) in self.admin_roles for role in member.roles)

        return admin_user or admin_role

    def get_deck(self: "Server", code: str) -> Optional[dict]:
        """Get information about a deck from the server.

        Args:
        ----
        code (str): The export code of the deck to retrieve
        """
        try:
            result = get(f"{self.api_url}/deck/{code}", timeout=5).json()
        except (TimeoutError, exceptions.JSONDecodeError):
            return
        if result["type"] == "success":
            return result
        return None

    def create_game(self: "Server") -> Optional[QueueGame]:
        """Create a server game."""
        try:
            data: dict[str, Union[str, int]] = get(f"{self.api_url}/games/create", timeout=5).json()
            return QueueGame(data)
        except (ConnectionError, exceptions.JSONDecodeError, exceptions.Timeout, KeyError):
            return None

    def cancel_game(self: "Server", game: QueueGame) -> bool:
        """Cancel a queued game."""
        try:
            data: dict[str, Optional[str]] = delete(
                f"{self.api_url}/games/cancel", timeout=5, json={"code": game.secret}
            ).json()
            return "success" in data.keys()
        except (ConnectionError, exceptions.JSONDecodeError, exceptions.Timeout, KeyError):
            return False

    def get_game_count(self: "Server") -> int:
        """Get the number of games."""
        try:
            data: dict[str, int] = get(
                f"{self.api_url}/games/count", timeout=5
            ).json()
            return data["games"]
        except (ConnectionError, exceptions.JSONDecodeError, exceptions.Timeout, KeyError):
            return 0


class ServerManager:
    """Manage multiple servers and their functionality."""

    def __init__(self: "ServerManager", client: Client, servers: list[Server]) -> None:
        """Manage multiple servers and their functionality.

        Args:
        ----
        client (Client): The bot client
        servers (list[Server]): A list of server objects to manage
        bot_server (Application): The web server hc-tcg servers send requests to
        scheduler (AsyncIOScheduler): Sheduler for repeating tasks
        universe (dict): Dictionary that converts card ids to Card objects
        """
        self.discord_links = {server.guild_id: server for server in servers}

        self.client = client
        self.servers = servers
