SHELL := /bin/bash

HEADLESS ?= true
RARES_FILE ?= rares.txt
# `ext_proxy` is a zsh alias (not a binary), so it doesn't exist in make's
# non-interactive shell - set the same proxy env vars directly instead.
PROXY := http://proxy.bloomberg.com:81

.PHONY: scrape add-to-cart

scrape:
	. .venv/bin/activate && HEADLESS=$(HEADLESS) RARES_FILE=$(RARES_FILE) http_proxy=$(PROXY) https_proxy=$(PROXY) python -m src.main

add-to-cart:
	. .venv/bin/activate && HEADLESS=$(HEADLESS) http_proxy=$(PROXY) https_proxy=$(PROXY) python -m src.add_to_cart
