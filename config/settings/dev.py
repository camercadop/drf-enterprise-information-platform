from .base import *  # noqa: F403, F401

DEBUG = True

LOGGING["formatters"] = {  # type: ignore[index]  # noqa: F405
    "console": {
        "format": "%(message)s",
    },
}
LOGGING["handlers"]["console"] = {  # type: ignore[index]  # noqa: F405
    "class": "rich.logging.RichHandler",
    "formatter": "console",
    "rich_tracebacks": True,
}
