# HC-TCG Bot
The HC-TCG Bot is a bot for [hc-tcg online](https://hc-tcg.online). It interfaces with the api and has commands for the official hc-tcg online server.

## Features
- Card and deck information
- Achievement information
- Deck of the day competitions
- Bug report management
- Game creation and counting

## Running
Rename .env.example to .env and enter your discord bot key, then create a servers directory. The servers directory contains python files which define a single server object.

It is recommended to run in a virtual environment, such as anaconda or venv.
To install dependencies directly, run `pip install -r requirements.txt`

Optionally, also install tqdm using `pip install tqdm` to see a progress bar when loading card data.

The bot is ran as a package, `python -m bot`

## Formatting and code style
We use ruff for formatting and linting, and mypy for type checking.
```
ruff format
ruff check
mypy -p bot
```