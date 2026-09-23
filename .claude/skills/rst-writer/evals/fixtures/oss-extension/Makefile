.PHONY: docs
SPHINXOPTS ?= -n -W --keep-going
docs:
	uv run --project . sphinx-build $(SPHINXOPTS) -b html docs _build/html
