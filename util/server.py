"""Handles interactions and linking discord and hc-tcg servers."""
from base64 import b64encode
from datetime import datetime
from typing import Any, Generator, Optional

from aiohttp.web import Application, Request, Response, post
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from interactions import Activity, ActivityType, Client, Embed, Member
from pyjson5 import Json5Exception
from pyjson5 import decode as decode_json
from requests import exceptions, get

from util import Card, deck_to_hash


class GamePlayer:
    """A representation of a player in a game."""

    def __init__(
        self: "GamePlayer", data: dict[str, Any], universe: dict[str, int]
    ) -> None:
        """Represent a player in a game.

        Args:
        ----
        data (dict): Player information
        universe (dict): Dictionary that converts card ids to Card objects
        """
        self.id: str = data["id"]
        self.name: str = data["censoredPlayerName"]
        self.minecraft_name: str = data["minecraftName"]
        self.lives: int = data["lives"]

        self.deck_hash: str = deck_to_hash(
            (
                card["cardId"]
                for card in data["pile"] + data["hand"] + data["discarded"]
            ),
            universe,
        )
        self.board: dict = data["board"]


class Game:
    """Store data about a game."""

    def __init__(self: "Game", data: dict[str, Any], universe: dict[str, Card]) -> None:
        """Store data about a game.

        Args:
        ----
        data (dict): The game data dict
        universe (dict): Dictionary that converts card ids to Card objects
        """
        self.players: list[GamePlayer] = [
            GamePlayer(data["state"]["players"][player_id], universe)
            for player_id in data["playerIds"]
        ]
        self.player_names = [player.name for player in self.players]
        self.id = data["id"]
        self.code: Optional[str] = data["code"]
        print(data.keys())
        self.created: datetime = datetime.fromtimestamp(
            data["createdTime"] / 1000, tz=None
        )

        self.end_callback = self.default_callback

    async def default_callback(self: "Game") -> None:
        """Handle callbacks by doing nothing."""

    def generate_embed(self: "Game") -> Embed:
        """Generate an embed containing game information."""
        overview_text = self.overview()
        emb = Embed(
            title=overview_text[0],
            description=overview_text[1],
            timestamp=datetime.now(tz=None),
        ).set_footer("Bot by Tyrannicodin")
        for player in self.players:
            emb.add_field(f"{player.name} hash", player.deck_hash)
        return emb

    def overview(self: "Game") -> tuple[str, str]:
        """Get a simple two line statement about the game."""
        return f"{self.code} ({self.id})" if self.code else self.id, " vs ".join(
            f"{player.name} ({player.lives} lives)" for player in self.players
        )


class Server:
    """An interface between a discord and hc-tcg server."""

    def __init__(
        self: "Server",
        server_id: str,
        server_url: str,
        server_key: str,
        guild_id: str,
        guild_key: str,
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
        """
        if admins is None:
            admins = []
        if tracked_forums is None:
            tracked_forums = {}

        self.server_id: str = server_id
        self.universe: Optional[dict[str, Card]] = None

        self.server_url: str = server_url
        self.api_url: str = server_url + "/api"
        self.server_key: str = server_key
        self.guild_id: str = guild_id
        self.guild_key: str = guild_key
        self.admin_roles: list[str] = admins
        self.tracked_forums: dict[str, list[str]] = tracked_forums

        self.followed_games: dict[str, Game] = []

    def authorize_user(self: "Server", member: Member) -> bool:
        """Check if a user is allowed to use a channel."""
        if self.admin_roles is []:
            return True
        admin_user = str(member.id) in self.admin_roles
        admin_role = any(str(role.id) in self.admin_roles for role in member.roles)

        return admin_user or admin_role

    def get_games(self: "Server") -> list[Game]:
        """Get games on the server."""
        try:
            game_data = get(
                f"{self.api_url}/games",
                headers={"api-key": self.server_key},
                timeout=20,
            ).json()
            return [Game(game_dict, self.universe) for game_dict in game_data]
        except (ConnectionError, exceptions.JSONDecodeError, exceptions.Timeout):
            return []

    @property
    def file_prefix(self: "Server") -> None:
        """The path to this server's save directory."""
        return rf"servers\{self.server_id}"


class ServerManager:
    """Manage multiple servers and their functionality."""

    def __init__(
        self: "ServerManager",
        client: Client,
        servers: list[Server],
        bot_server: Application,
        scheduler: AsyncIOScheduler,
        universe: dict[str, Card],
    ) -> None:
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
        self.server_links = {server.server_url: server for server in servers}
        for server in servers:
            server.universe = universe

        self.client = client
        self.universe = universe

        scheduler.add_job(self.update_status, IntervalTrigger(minutes=2))

        bot_server.add_routes([post("/admin/game_end", self.on_game_end)])

    async def on_game_end(self: "ServerManager", req: Request) -> Response:
        """Call when a server sends a request to the game_end api endpoint.

        Args:
        ----
        req (Request): The web request sent
        """
        try:
            json: dict = decode_json((await req.content.read()).decode())
        except Json5Exception:
            return Response(status=400, reason="Invalid json payload")
        api_key = req.headers.get("api-key")
        if (
            req.remote not in self.server_links.keys()
            and self.server_links[req.remote].guild_key == api_key
        ):
            print(f"Recieved request with invalid api key or url: {api_key}")
            return Response(status=403)

        required_keys = [
            "createdTime",
            "id",
            "code",
            "playerIds",
            "playerNames",
            "endInfo",
            "endTime",
        ]
        if not all(requiredKey in json.keys() for requiredKey in required_keys):
            keys = "\n".join(json.keys())
            print(f"Invalid data:\n {keys}")
            return Response(status=400)

        json["endInfo"].pop("deadPlayerIds")
        if json["id"] in self.server_links[req.remote].followed_games.keys():
            await (
                self.server_links[req.remote].followed_games[json["id"]].end_callback()
            )
        return Response()

    async def update_status(self: "ServerManager") -> None:
        """Update bot status with game count."""
        done_servers: list[Server] = []
        games: int = 0
        for server in self.server_links.values():
            if server in done_servers:
                continue
            done_servers.append(server)
            try:
                games += len(
                    get(
                        f"{server.api_url}/games",
                        headers={"api-key": server.server_key},
                        timeout=5,
                    ).json()
                )
            except (ConnectionError, exceptions.InvalidJSONError, exceptions.Timeout):
                pass
        await self.client.change_presence(
            activity=Activity(f"{games} games", ActivityType.WATCHING)
        )
