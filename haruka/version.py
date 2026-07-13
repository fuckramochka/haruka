"""Single source of truth for the Haruka version."""

__version__ = "2.3.0"
CODENAME = "Prism"


def version_string() -> str:
    return f"Haruka v{__version__} ({CODENAME})"
