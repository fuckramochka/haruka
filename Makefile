.PHONY: install dev test lint check run docker-build

install:
	python -m pip install -e '.[full]'

dev:
	python -m pip install -e '.[dev,full]'

test:
	python -m pytest

lint:
	ruff check haruka tests

check:
	python -m compileall -q haruka tests
	python -m pytest
	ruff check haruka tests

run:
	python -m haruka

docker-build:
	docker build -t haruka:local .
