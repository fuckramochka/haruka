import harukatl.extensions.html as html_ext


class _CustomEmojisProxy:
    def __bool__(self):
        # Newer Telethon/HarukaTL builds may not define CUSTOM_EMOJIS.
        # Treat missing value as enabled by default.
        return bool(getattr(html_ext, "CUSTOM_EMOJIS", True))

    def __repr__(self):
        return repr(bool(self))


CUSTOM_EMOJIS = _CustomEmojisProxy()
