"""Everything to do with deck handling, originally by ProfNinja."""

import base64
from binascii import Error as binError

from .datagen import Card


def deck_to_hash(deck: list[str], universe: dict[str, Card]) -> str:
    """Convert a list of cards to a deck hash string.

    Args:
    ----
    deck (list): List of cards to convert
    universe (dict): Dictionary that converts card ids to Card objects
    """
    deck_numbers = bytes([universe[card_id].numeric_id for card_id in deck])
    deck_hash = base64.b64encode(deck_numbers)
    return deck_hash.decode()


def hash_to_deck(deck_hash: str, universe: dict[str, Card]) -> list[Card]:
    """Convert a deck hash to list of ids.

    Args:
    ----
    deck_hash (str): The deck's encoded hash
    universe (dict): Dictionary that converts card ids to Card objects
    """
    try:
        numeric_ids = list(base64.b64decode(deck_hash))
        deck = []
        for numeric_id in numeric_ids:
            card = next(
                (card for card in universe.values() if card.numeric_id == numeric_id),
                None,
            )
            if card:
                deck.append(card)
        return deck
    except binError:
        return []


def hash_to_stars(deck_hash: str, universe: dict[str, Card]) -> int:
    """Get the cost of a deck hash.

    Args:
    ----
    deck_hash (str): The deck's encoded hash
    universe (dict): Dictionary that converts card ids to Card objects
    """
    deck = hash_to_deck(deck_hash, universe)
    stars = 0
    wilds = len(list(filter(lambda d: d.cost == "wild", deck)))
    stars += max(wilds - 3, 0)
    for card in filter(lambda d: d.cost != "wild", deck):
        stars += card.cost
    return stars
