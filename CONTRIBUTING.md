# Contributing to Haruka

Thank you for improving the engine.

## Before opening code

- Use an issue for large behavior or public API changes.
- Keep the core engine-first; do not add unrelated novelty commands as core.
- New Telegram functionality belongs behind a focused facade.
- Compatibility code stays under `haruka.compat`.

## Development setup

```bash
git clone https://github.com/fuxckramochka/haruka.git
cd haruka
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,full]'
pytest
ruff check haruka tests
```

## Pull requests

1. Branch from `main`.
2. Keep changes focused.
3. Add or update tests.
4. Update documentation and changelog for user-visible behavior.
5. Run compile, tests and Ruff.
6. Explain security and migration impact.

## Style

Python 3.10+, type annotations for public APIs, 100-character lines, async I/O, no hidden global state. User-facing text should be concise. Never log credentials.

## Commit examples

- `feat(loader): add manifest compatibility check`
- `fix(dispatcher): preserve aliases in feature gates`
- `docs: explain Docker first login`

## Review priorities

Correctness and account safety first, then stable contracts, testability, compatibility and appearance.
