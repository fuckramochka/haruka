.PHONY: install dev test lint run doctor docker
install:
	python install.py
dev:
	python install.py --dev
test:
	python -m pytest -q
lint:
	python -m ruff check .
run:
	python main.py
doctor:
	python -m compileall -q haruka && python -c "import haruka; print(haruka.__version__)"
docker:
	docker compose up --build
