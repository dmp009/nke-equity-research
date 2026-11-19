PY ?= .venv/bin/python
export PYTHONPATH := .

.PHONY: data build pdf test test-all lint

data:      ## refresh SEC filings and market snapshot (network)
	$(PY) -c "from nkeresearch.sec import download; download('data/raw/nke_companyfacts.json')"
	$(PY) -m nkeresearch.market

build:     ## Excel model, pitch deck (PPTX) and deep-dive charts from the committed snapshots
	$(PY) scripts/build_all.py

pdf:       ## export the deck to PDF + PNG previews with PowerPoint (macOS; needs pymupdf)
	$(PY) scripts/export_pdf.py

test:      ## fast tests
	$(PY) -m pytest -q -m "not slow"

test-all:  ## includes recalculating the Excel workbook and comparing it with the Python model
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .
