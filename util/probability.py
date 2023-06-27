# By Allophony on discord
from math import comb

deckSize = 42
OHSize = 7


def aGreatFormula(a, m, k, n):
    return comb(a, k) * comb(n - a, m - k) / comb(n, m)


def initialHandProb(hermitsInDeck, desiredExactHermits):
    validHands = sum(
        aGreatFormula(hermitsInDeck, OHSize, k, deckSize)
        for k in range(1, min(hermitsInDeck + 1, OHSize + 1))
    )
    goodHands = aGreatFormula(hermitsInDeck, OHSize, desiredExactHermits, deckSize)
    return goodHands / validHands


def probability(hermitsInDeck, draws, desiredHermits):
    if (
        draws + OHSize < desiredHermits
        or hermitsInDeck < desiredHermits
        or hermitsInDeck > deckSize
        or draws > deckSize - OHSize
    ):
        return 0
    res = 0
    for i in range(1, OHSize + 1):
        iHermitsInOH = initialHandProb(hermitsInDeck, i)
        if i >= desiredHermits:
            res = res + iHermitsInOH
        else:
            res = res + iHermitsInOH * sum(
                aGreatFormula(hermitsInDeck - i, draws, k, deckSize - OHSize)
                for k in range(desiredHermits - i, min(draws + 1, hermitsInDeck - i + 1))
            )
    return res
