from dataclasses import dataclass


@dataclass
class Palette:
    BACKGROUND: tuple[int, int, int] = (226, 202, 139)
    NAME: tuple[int, int, int] = (0, 0, 0)
    BASIC_ATTACK: tuple[int, int, int] = (0, 0, 0)
    SPECIAL_ATTACK: tuple[int, int, int] = (0, 0, 0)
    HEALTH: tuple[int, int, int] = (246, 4, 1)
    TYPE_BACKGROUND: tuple[int, int, int] = (255, 255, 255)
    BASIC_DAMAGE: tuple[int, int, int] = (246, 4, 1)
    SPECIAL_DAMAGE: tuple[int, int, int] = (23, 66, 234)


palettes: dict[str, Palette] = {
    "base": Palette(),
    "alter_egos": Palette((25, 25, 25), (255, 255, 255), (255, 255, 255), (255, 255, 255)),
    "pharoah": Palette((239, 228, 103), (246, 4, 1), (246, 4, 1), (23, 66, 234)),
}
