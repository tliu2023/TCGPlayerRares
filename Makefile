SHELL := /bin/bash

HEADLESS ?= true
RARES_FILE ?= rares.txt

.PHONY: scrape add-to-cart

scrape:
	. .venv/bin/activate && HEADLESS=$(HEADLESS) RARES_FILE=$(RARES_FILE) ext_proxy python -m src.main

add-to-cart:
	. .venv/bin/activate && HEADLESS=$(HEADLESS) ext_proxy python -m src.add_to_cart
