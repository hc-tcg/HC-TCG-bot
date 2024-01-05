"""Handles interactions and linking discord and hc-tcg servers."""
from collections import defaultdict
from datetime import datetime as dt
from datetime import timezone
from enum import Enum
from typing import Any, Callable, Optional

from aiohttp.web import Application, Request, Response, post
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from interactions import (
    Activity,
    ActivityType,
    Button,
    ButtonStyle,
    Client,
    ComponentContext,
    Embed,
    GuildPrivateThread,
    Member,
    Message,
    SlashContext,
    spread_to_rows,
)
from pyjson5 import Json5Exception
from pyjson5 import decode as decode_json
from requests import exceptions, get
from requests import post as send_post

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
        self.created: dt = dt.fromtimestamp(data["createdTime"] / 1000, tz=timezone.utc)

        self.end_callback = self.default_callback

    async def default_callback(self: "Game") -> None:
        """Handle callbacks by doing nothing."""

    def generate_embed(self: "Game") -> Embed:
        """Generate an embed containing game information."""
        overview_text = self.overview()
        emb = Embed(
            title=overview_text[0],
            description=overview_text[1],
            timestamp=dt.now(tz=timezone.utc),
        ).set_footer("Bot by Tyrannicodin")
        for player in self.players:
            emb.add_field(f"{player.name} hash", player.deck_hash)
        return emb

    def overview(self: "Game") -> tuple[str, str]:
        """Get a simple two line statement about the game."""
        return f"{self.code} ({self.id})" if self.code else self.id, " vs ".join(
            f"{player.name} ({player.lives} lives)" for player in self.players
        )


class MatchStateEnum(Enum):
    """Possible match states."""

    WAITING_FOR_PLAYERS: int = 0
    STARTING_GAME: int = 1
    PLAYING: int = 2
    ENDED: int = 3


STATE_TEXT: dict["MatchStateEnum", str] = {
    MatchStateEnum.WAITING_FOR_PLAYERS: "Match: Waiting for players to join",
    MatchStateEnum.STARTING_GAME: "Match: Waiting for game {game} to start",
    MatchStateEnum.PLAYING: "Match: Game {game} in progress",
    MatchStateEnum.ENDED: "Match finished: {winner} won!",
}
STATE_COLORS: dict["MatchStateEnum", int] = {
    MatchStateEnum.WAITING_FOR_PLAYERS: 0,
    MatchStateEnum.STARTING_GAME: 0,
    MatchStateEnum.PLAYING: 0,
    MatchStateEnum.ENDED: 0,
}


class Match:
    """A collection of games."""

    def __init__(
        self: "Match", client: Client, ctx: SlashContext, server: "Server", games: int
    ) -> None:
        """Create a match.

        Args:
        ----
        client (Client): The bot client
        ctx (SlashContext): The original command context
        server (Server): The server this match is on
        games (int): The number of games a player needs to win
        """
        self.client: Client = client
        self.context: SlashContext = ctx
        self.server: Server = server
        self.games: int = games
        self.current_game: int = 0

        self.state: MatchStateEnum = MatchStateEnum.WAITING_FOR_PLAYERS
        self.players: list[str] = []
        self.game: Optional[Game] = None
        self.game_message: Optional[Message] = None
        self.scores: defaultdict = defaultdict(int)
        self.winner: Optional[str] = None

        self.button_join = Button(
            style=ButtonStyle.SUCCESS,
            label="Join game",
            emoji=":white_check_mark:",
            custom_id="join_game",
        )
        self.button_leave = Button(
            style=ButtonStyle.DANGER,
            label="Leave game",
            emoji=":x:",
            custom_id="leave_game",
        )
        self.emb = Embed(
            title=STATE_TEXT[self.state].format(winner=self.winner),
            color=STATE_COLORS[self.state],
            timestamp=dt.now(tz=timezone.utc),
        ).set_footer("Bot by Tyrannicodin16")

    async def set_state(self: "Match", new_state: MatchStateEnum) -> None:
        """Properly update the state value."""
        self.state = new_state
        self.emb.title = STATE_TEXT[self.state].format(
            winner=self.winner, game=self.current_game
        )
        self.emb.color = STATE_COLORS[self.state]
        self.button_join.disabled = self.state != MatchStateEnum.WAITING_FOR_PLAYERS
        self.button_leave.disabled = self.state != MatchStateEnum.WAITING_FOR_PLAYERS
        await self.message.edit(
            embed=self.emb,
            components=spread_to_rows(self.button_join, self.button_leave),
        )

    async def send_message(self: "Match") -> None:
        """Send message for the match."""
        self.message: Message = await self.context.send(
            embeds=self.emb,
            components=spread_to_rows(self.button_join, self.button_leave),
        )
        self.id: str = str(self.message.id)
        self.thread: GuildPrivateThread = (
            await self.context.channel.create_private_thread(
                "Match id: " + str(self.id),
                invitable=True,
                reason=f"Match id {self.id} thread",
            )
        )
        await self.thread.join()

    async def start_game(self: "Match") -> None:
        """Create a game."""
        self.current_game += 1
        code = self.server.create_game()
        self.server.prepared_games[code] = self.handle_game_start
        await self.set_state(MatchStateEnum.STARTING_GAME)

        game_embed = Embed(
            title=f"Game {self.current_game}",
            description=f"Code: {code}",
            color=STATE_COLORS[self.state],
            timestamp=dt.now(tz=timezone.utc),
        ).set_footer("Bot by Tyrannicodin16")

        await self.thread.send(
            content="".join(f"<@{player_id}>" for player_id in self.players),
            embeds=game_embed,
        )

    async def handle_game_start(self: "Match", game: Game) -> None:
        """Update the game state on start and subscribe to end event."""
        self.game = game
        self.game.end_callback = self.handle_game_end
        self.server.followed_games[self.game.id] = self.game
        await self.set_state(MatchStateEnum.PLAYING)

    async def handle_game_end(self: "Match", game_info: dict) -> None:
        """Record game results."""
        player_dict: dict[str, str] = dict(
            zip(game_info["playerIds"], game_info["playerNames"])
        )
        game_winner: str = player_dict[game_info["endInfo"]["winner"]]
        self.scores[game_winner] += 1
        self.emb.add_field(
            f"Game {self.current_game} - {game_winner} won",
            " - ".join(
                f"{player} ({self.scores[player]})"
                for player in sorted(game_info["playerNames"])
            ),
        )
        if self.scores[game_winner] == self.games:
            self.winner = game_winner
            await self.thread.edit(archived=True, locked=True, reason="Match end")
            await self.set_state(MatchStateEnum.ENDED)
            return
        await self.start_game()


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

        self.followed_games: dict[str, Game] = {}
        self.prepared_games: dict[str, Callable] = {}

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

    def create_game(self: "Server") -> Optional[str]:
        """Create a server game."""
        try:
            return send_post(
                f"{self.api_url}/createGame",
                headers={"api-key": self.server_key},
                timeout=20,
            ).json()["code"]
        except (
            ConnectionError,
            exceptions.JSONDecodeError,
            exceptions.Timeout,
            KeyError,
        ):
            return None

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
        self.server_links = {server.guild_key: server for server in servers}
        for server in servers:
            server.universe = universe

        self.client = client
        self.universe = universe

        scheduler.add_job(self.update_status, IntervalTrigger(minutes=2))

        bot_server.add_routes([post("/admin/game_end", self.on_game_end)])
        bot_server.add_routes([post("/admin/game_start", self.on_game_start)])

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
            api_key not in self.server_links.keys()
            or self.server_links[api_key].guild_key == api_key
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

        server = self.server_links[api_key]
        json["endInfo"].pop("deadPlayerIds")
        if json["id"] in server.followed_games.keys():
            await (
                server.followed_games[json["id"]].end_callback(json)
            )
        return Response()

    async def on_game_start(self: "ServerManager", req: Request) -> Response:
        """Call when a server sends a request to the game_start api endpoint.

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
            api_key not in self.server_links.keys()
            or self.server_links[api_key].guild_key != api_key
        ):
            print(f"Recieved request with invalid api key or url: {api_key}")
            print(self.server_links.keys())
            return Response(status=403)

        required_keys = [
            "createdTime",
            "id",
            "code",
            "playerIds",
            "playerNames",
            "state",
        ]
        if not all(requiredKey in json.keys() for requiredKey in required_keys):
            keys = "\n- ".join(json.keys())
            print(f"Invalid data:\n {keys}")
            return Response(status=400)

        server = self.server_links[api_key]
        if json["code"] in server.prepared_games.keys():
            await server.prepared_games[json["code"]](
                Game(json, self.universe)
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
