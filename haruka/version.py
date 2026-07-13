"""Single source of truth for the Haruka version."""

__version__ = "2.2.0"
CODENAME = "Nova"


def version_string() -> str:
    return f"Haruka v{__version__} ({CODENAME})"
