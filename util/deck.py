# Everything to do with deck handling, by ProfNinja
import base64
from binascii import Error as binError


def deckToHash(deck, universe: list[str]):
    deckBytes = bytes(
        [universe.index(card) if card in universe else 0 for card in deck]
    )
    hash = base64.b64encode(deckBytes)
    return hash


def hashToDeck(dhsh: str, universe: list[str]):
    try:
        iarr = list(base64.b64decode(dhsh))
        deck = []
        for idx in iarr:
            try:
                deck.append(universe[idx])
            except IndexError:
                pass
        return deck
    except binError:
        return []


def hashToStars(dhsh: str, starData: dict[str, int], universe: list[str]):
    deck = hashToDeck(dhsh, universe)
    stars = 0
    for c in deck:
        stars += starData[c]
    return stars
