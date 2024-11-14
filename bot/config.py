"""Load environment config."""

from __future__ import annotations

import os

import dotenv


class Config:
    """Load environement variables as class."""

    def __init__(self: Config) -> None:
        """Load environement variables as class."""
        dotenv.load_dotenv()

        env = os.environ

        self.SECRET: str = env.get("DISCORD_SECRET") or ""


CONFIG = Config()
