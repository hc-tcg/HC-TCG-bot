"""Handles interactions and linking discord and hc-tcg servers."""

from __future__ import annotations

from datetime import datetime as dt
from datetime import timezone
from json import JSONDecodeError, loads
from time import time
from typing import Any

from aiohttp import ClientSession, ContentTypeError
from interactions import Client, Embed, Member, Snowflake
from PIL import Image

from bot.util.datagen import Achievement, DataGenerator


class GamePlayer:
    """A representation of a player in a game."""

    def __init__(self: GamePlayer, data: dict[str, Any]) -> None:
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

    def __init__(self: Game, data: dict[str, Any]) -> None:
        """Store data about a game.

        Args:
        ----
        data (dict): The game data dict
        """
        self.players: list[GamePlayer] = [GamePlayer(player) for player in data["players"]]
        self.player_names = [player.name for player in self.players]
        self.id = data["id"]
        self.spectator_code: str | None = data["spectatorCode"]
        self.created: dt = dt.fromtimestamp(data["createdTime"] / 1000, tz=timezone.utc)
        self.spectators = data["viewers"] - len(self.players)

        print(data["state"])


class QueueGame:
    """Information about a private queued game."""

    def __init__(self: QueueGame, data: dict[str, Any]) -> None:
        """Information about a private queued game.

        Args:
        ----
        data (dict): The game data dict
        """
        self.joinCode: str = data["gameCode"]
        self.spectatorCode: str = data["spectatorCode"]
        self.secret: str = data["apiSecret"]
        self.timeout: str = data["timeOutAt"] / 1000

        self.join_url: str = data["joinUrl"]
        self.spectate_url: str = data["spectateUrl"]

    def create_embed(self: QueueGame, *, spectators: bool = False) -> Embed:
        """Create an embed with information about the game."""
        e = (
            Embed(
                "Game",
                f"Expires <t:{self.timeout:.0F}:T>",
                timestamp=dt.now(tz=timezone.utc),
            )
            .add_field("Join code", self.joinCode, inline=True)
            .set_footer("Bot by Tyrannicodin16")
        )
        if spectators:
            e.add_field("Spectate code", self.spectatorCode, inline=True)
        return e


class Server:
    """An interface between a discord and hc-tcg server."""

    http_session: ClientSession
    data_generator: DataGenerator

    def __init__(
        self: Server,
        server_id: str,
        server_url: str,
        guild_id: str,
        admins: list[str] | None = None,
        tracked_forums: dict[str, list[str]] | None = None,
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

        self.last_game_count: int = 0
        self.last_game_count_time: int = 0
        self.last_queue_length: int = 0
        self.last_queue_length_time: int = 0

        self.type_data: dict[str, Image.Image] | None = None

        self.server_url: str = server_url
        self.guild_id: str = guild_id
        self.admin_roles: list[str] = admins
        self.tracked_forums: dict[str, list[str]] = tracked_forums

    def create_session(self: Server) -> None:
        """Create http session and data generator."""
        self.http_session = ClientSession(self.server_url + "/api/")
        self.data_generator = DataGenerator(self.http_session)

    def authorize_user(self: Server, member: Member) -> bool:
        """Check if a user is allowed to use privileged commands."""
        if self.admin_roles is []:
            return True
        admin_user = str(member.id) in self.admin_roles
        admin_role = any(str(role.id) in self.admin_roles for role in member.roles)

        return admin_user or admin_role

    async def get_deck(self: Server, code: str) -> dict | None:
        """Get information about a deck from the server.

        Args:
        ----
        code (str): The export code of the deck to retrieve
        """
        try:
            async with self.http_session.get(f"deck/{code}") as response:
                result = loads((await response.content.read()).decode())
                if not response.ok:
                    return None
        except (TimeoutError, JSONDecodeError):
            return None
        return result

    async def create_game(self: Server) -> QueueGame | None:
        """Create a server game."""
        try:
            async with self.http_session.get("games/create") as response:
                data: dict[str, str | int] = loads((await response.content.read()).decode())
                if not response.ok:
                    return None
            return QueueGame(data)
        except (
            ConnectionError,
            JSONDecodeError,
            KeyError,
        ):
            return None

    async def cancel_game(self: Server, game: QueueGame) -> bool:
        """Cancel a queued game."""
        try:
            async with self.http_session.delete(
                "games/cancel", json={"code": game.secret}
            ) as response:
                loads((await response.content.read()).decode())
                return response.status == 200
        except (
            ConnectionError,
            JSONDecodeError,
            KeyError,
        ):
            return False

    async def get_game_count(self: Server) -> int:
        """Get the number of games."""
        try:
            if self.last_game_count_time > time() - 60:
                return self.last_game_count

            async with self.http_session.get("games/count") as response:
                data: dict[str, int] = loads((await response.content.read()).decode())
                if not response.ok:
                    return 0
            self.last_game_count = data["games"]
            self.last_game_count_time = round(time())
            return self.last_game_count
        except (
            ConnectionError,
            JSONDecodeError,
            KeyError,
        ):
            return 0

    async def get_queue_length(self: Server) -> int:
        """Get the number of games."""
        try:
            if self.last_queue_length_time > time() - 60:
                return self.last_queue_length

            async with self.http_session.get("games/queue/length") as response:
                data: dict[str, int] = loads((await response.content.read()).decode())
                if not response.ok:
                    return 0
            self.last_queue_length = data["queueLength"]
            self.last_queue_length_time = round(time())
            return self.last_queue_length
        except (
            ConnectionError,
            JSONDecodeError,
            KeyError,
        ):
            return 0

    async def get_player_stats(self: Server, uuid: str) -> dict[str, int] | None:
        """Get a player's win stats from the server.

        Args:
        ----
        uuid (str): The player's uuid
        """
        try:
            async with self.http_session.get("stats", params={"uuid": uuid}) as response:
                if not response.ok:
                    return None
                return await response.json()
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None

    async def get_type_distribution_stats(self: Server) -> list[dict[str, float | str]] | None:
        """Get a player's win stats from the server.

        Args:
        ----
        uuid (str): The player's uuid
        """
        try:
            async with self.http_session.get("stats/type-distribution") as response:
                if not response.ok:
                    return None
                return await response.json()
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None

    async def get_type_icons(self: Server) -> dict[str, Image.Image] | None:
        """Get a dictionary of type icons."""
        if self.type_data is not None:
            return self.type_data
        try:
            async with self.http_session.get("types") as response:
                if not response.ok:
                    return None
                data: list[dict[str, str]] = await response.json()
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None
        self.type_data = {
            hermit_type["type"]: await self.data_generator.get_image(hermit_type["icon"])
            for hermit_type in data
        }
        return self.type_data

    async def get_game_stats(self: Server) -> tuple[int, str] | None:
        """Get number of games and average length."""
        try:
            async with self.http_session.get("stats/games") as response:
                if not response.ok:
                    return None
                data = await response.json()
                return (
                    data["allTimeGames"],
                    (
                        str(data["gameLength"]["averageLength"]["minutes"])
                        + f" minutes, {data["gameLength"]["averageLength"]["seconds"]} seconds"
                    ),
                )
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None

    async def get_player_achievement_progress(
        self: Server, uuid: str, achievement: Achievement
    ) -> int | None:
        """Get achievement progress for a player.

        Args:
        ----
        uuid (str): The player's uuid
        achievement (str): The achievement to get progress of
        """
        try:
            async with self.http_session.get(
                "achievements/player-progress",
                params={
                    "uuid": uuid,
                    "achievementId": achievement.achievement_id,
                    "level": achievement.index,
                },
            ) as response:
                if not response.ok:
                    return None
                data = await response.json()
                return data["progress"]
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None

    async def get_global_achievement_progress(
        self: Server, achievement: Achievement
    ) -> float | None:
        """Get global percentage progress for an achievement.

        Args:
        ----
        achievement (str): The achievement to get progress of
        level (str): The level to judge as completed
        """
        try:
            async with self.http_session.get(
                f"achievements/{achievement.achievement_id}/{achievement.index}",
            ) as response:
                if not response.ok:
                    return None
                data = await response.json()
                return data["percent"]
        except (
            ConnectionError,
            JSONDecodeError,
            ContentTypeError,
            KeyError,
        ):
            return None


class ServerManager:
    """Manage multiple servers and their functionality."""

    def __init__(self: ServerManager, client: Client, servers: list[Server]) -> None:
        """Manage multiple servers and their functionality.

        Args:
        ----
        client (Client): The bot client
        servers (list[Server]): A list of server objects to manage
        bot_server (Application): The web server hc-tcg servers send requests to
        scheduler (AsyncIOScheduler): Sheduler for repeating tasks
        universe (dict): Dictionary that converts card ids to Card objects
        """
        self._discord_links = {server.guild_id: server for server in servers}

        self.client = client
        self.servers = servers

    def get_server(self: ServerManager, guild_id: Snowflake | None) -> Server:
        """Get a server by its discord guild id.

        Args:
        ----
        guild_id (str): The guild id of the discord server
        """
        return (
            self._discord_links[str(guild_id)]
            if guild_id in self._discord_links.keys()
            else self.servers[0]
        )

    async def close_all_sessions(self: ServerManager) -> None:
        """Close all server ClientSessions."""
        for server in self.servers:
            await server.http_session.close()

    async def reload_all_generators(self: ServerManager) -> None:
        """Close all server DataGenerators."""
        for server in self.servers:
            server.create_session()
            await server.data_generator.reload_all()
