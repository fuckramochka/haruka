# Publishing to GitHub

The repository is clean and does not include `.env`, Telegram sessions, memory
databases, virtual environments or generated data.

## Create the repository

1. Create an empty GitHub repository without auto-generating a README/license.
2. From this folder run:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Haruka Engine 0.3 release"
git remote add origin https://github.com/YOUR_NAME/YOUR_REPOSITORY.git
git push -u origin main
```

3. Replace `YOUR_REPOSITORY_URL` in `docs/INSTALL.md` with the real URL.
4. In GitHub settings, enable private vulnerability reporting, Dependabot alerts
   and branch protection requiring the CI workflow.
5. Add a short repository description and topics: `telegram`, `ai`, `engine`,
   `telethon`, `bot-api`, `python`.

## Release

Update the version in `pyproject.toml` and `haruka/__init__.py`, update
`CHANGELOG.md`, then:

```bash
git tag -a v0.3.0 -m "Haruka Engine 0.3.0"
git push origin v0.3.0
```

The release workflow builds source/wheel artifacts, validates them with Twine and
attaches them to the GitHub Release. It does not publish to PyPI automatically.

## License

The repository currently uses MIT with copyright attributed to `ramochka`.
Change `LICENSE` before publishing if another ownership name or license is needed.
