"""Plain text of the 10-K HTML, used to look up the facts quoted in nkeresearch/facts.py."""
import html
import re
import sys
from pathlib import Path


def to_text(path: Path) -> str:
    t = Path(path).read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"<ix:header>.*?</ix:header>", "", t, flags=re.DOTALL)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


if __name__ == "__main__":
    text = to_text(Path(sys.argv[1]))
    for kw in sys.argv[2:]:
        for m in list(re.finditer(kw, text))[:3]:
            print(f"[{kw}] ...{text[max(0, m.start() - 150):m.start() + 350]}...\n")
