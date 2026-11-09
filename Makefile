PYTHON ?= python
APP_PYTHON = $(PYTHON)
export PYTHON
export PLAYWRIGHT_BROWSERS_PATH := $(CURDIR)/.cache/ms-playwright

.PHONY: setup init-db upgrade-db admin run check format test browser-setup test-ui test-all acceptance acceptance-b acceptance-c acceptance-e benchmark count

setup:
	$(APP_PYTHON) -m pip install Flask Werkzeug python-dotenv Pillow pytest pytest-cov ruff
	npm ci --cache .cache/npm

init-db:
	$(APP_PYTHON) -m flask --app app init-db

upgrade-db:
	$(APP_PYTHON) -m flask --app app upgrade-db

admin:
	$(APP_PYTHON) -m flask --app app create-admin

run:
	$(APP_PYTHON) -m flask --app app run --host 127.0.0.1

check:
	$(APP_PYTHON) -m ruff check app tests scripts
	$(APP_PYTHON) -m ruff format --check app tests scripts
	$(APP_PYTHON) -m compileall -q app tests scripts
	npm run lint

format:
	$(APP_PYTHON) -m ruff format app tests scripts
	$(APP_PYTHON) -m ruff check --fix app tests scripts

test:
	$(APP_PYTHON) -m pytest --cov=app --cov-report=term-missing

browser-setup:
	npm exec playwright install chromium

test-ui:
	npm run test:ui

test-all: check test test-ui acceptance acceptance-b acceptance-c acceptance-e benchmark

acceptance:
	$(APP_PYTHON) -m scripts.acceptance_a

acceptance-b:
	$(APP_PYTHON) -m scripts.acceptance_b

acceptance-c:
	$(APP_PYTHON) -m scripts.acceptance_c

acceptance-e:
	$(APP_PYTHON) -m scripts.acceptance_e

benchmark:
	$(APP_PYTHON) -m scripts.benchmark_search

count:
	$(APP_PYTHON) -m scripts.count_code
