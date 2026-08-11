# Utilities

import re


def slugify(value: str) -> str:
    """Return a stable lowercase identifier suitable for module names."""
    return re.sub(r"[^a-z0-9_]+", "_", value.casefold()).strip("_")

from .messages import *
from .other import *
from .entity import *
from .haruka import *
from .platform import *
from .git import *
from .args import *
from .network import *
from .placeholders import *
