"""One palette for the deck, the charts and the deep dive.

Categorical pair validated with the dataviz skill's palette validator (light mode):
ORANGE = Nike / forecast / focus, BLUE = history / comparison. GREEN and RED are status
colours (above / below the share price) and always come with a label.
"""

INK = "15171A"  # titles and body text
MUTED = "6B7280"  # captions, axis labels
LINE = "E5E7EB"  # hairlines and gridlines
TINT = "F4F5F7"  # card background
WARM = "FDEEE6"  # highlight box background
DARK = "111316"  # title and closing slides
DARK_MUTED = "A1A7B0"
ORANGE = "E8590C"
BLUE = "2F6FC4"
GREEN = "1F9D55"
RED = "C2362B"
WHITE = "FFFFFF"

HEAD_FONT = "Arial"
BODY_FONT = "Calibri"


def hexc(c: str) -> str:
    """Matplotlib colour from a palette hex."""
    return "#" + c
