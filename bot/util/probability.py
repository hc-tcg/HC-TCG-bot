"""Calculate probability of certain events, by Allophony on discord."""

from math import comb

deck_size = 42
opening_hand_size = 7


def allophony_formula(hermits: int, hand_size: int, desired: int, deck_size: int) -> float:
    """Allophony maths (idk)."""
    return (
        comb(hermits, desired)
        * comb(deck_size - hermits, hand_size - desired)
        / comb(deck_size, hand_size)
    )


def initial_hand_chance(hermits_in_deck: int, desired_hermits: int) -> float:
    """Get the chance of having `desired_hermits` hermits
    in your inital hand when you have `hermits_in_deck` in your deck.
    """  # noqa: D205
    valid_hands = sum(
        allophony_formula(hermits_in_deck, opening_hand_size, k, deck_size)
        for k in range(1, min(hermits_in_deck + 1, opening_hand_size + 1))
    )
    good_hands = allophony_formula(hermits_in_deck, opening_hand_size, desired_hermits, deck_size)
    return good_hands / valid_hands


def probability(hermits_in_deck: int, draws: int, desired_hermits: int) -> float:
    """Get the probability of having x hermits in your hands after d draws.

    Args:
    ----
    hermits_in_deck (int): The number of hermits in the deck
    draws (int): The number of draws taken
    desired_hermits (int): The target hermit count
    """
    if (
        draws + opening_hand_size < desired_hermits
        or hermits_in_deck < desired_hermits
        or hermits_in_deck > deck_size
        or draws > deck_size - opening_hand_size
    ):
        return 0
    res: float
    for i in range(1, opening_hand_size + 1):
        hermits_in_first_hand = initial_hand_chance(hermits_in_deck, i)
        if i >= desired_hermits:
            res = res + hermits_in_first_hand
        else:
            res = res + hermits_in_first_hand * sum(
                allophony_formula(hermits_in_deck - i, draws, k, deck_size - opening_hand_size)
                for k in range(desired_hermits - i, min(draws + 1, hermits_in_deck - i + 1))
            )
    return res
