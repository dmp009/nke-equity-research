"""Export outputs/NKE_stock_pitch.pptx to PDF with Microsoft PowerPoint (macOS) and render PNG previews.

Needs PowerPoint for Mac and PyMuPDF (`pip install pymupdf`). Not part of CI: the PPTX is the source.
"""
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PPTX, PDF, IMG = ROOT / "outputs/NKE_stock_pitch.pptx", ROOT / "outputs/NKE_stock_pitch.pdf", ROOT / "docs/img"

SCRIPT = f'''
tell application "Microsoft PowerPoint"
    open POSIX file "{PPTX}"
    delay 3
    set p to active presentation
    save p in POSIX file "{PDF}" as save as PDF
    close p saving no
end tell
'''


def main() -> None:
    PDF.unlink(missing_ok=True)
    subprocess.run(["osascript", "-e", SCRIPT], check=True)
    if not PDF.exists():
        sys.exit("PowerPoint did not write the PDF")
    IMG.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(PDF) as doc:
        for i, page in enumerate(doc, 1):
            page.get_pixmap(dpi=110).save(IMG / f"slide_{i:02d}.png")
        print(f"{PDF.name}: {len(doc)} slides, previews in docs/img/")


if __name__ == "__main__":
    main()
