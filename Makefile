PYTHON ?= python

.PHONY: install run test smoke

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) app.py

test:
	pytest

smoke:
	$(PYTHON) scripts/smoke_test.py
