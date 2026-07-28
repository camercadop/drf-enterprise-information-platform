"""Runtime dependency resolution for the enterprise platform.

Provides a single canonical way to resolve dotted-path references to classes
and callables at runtime. All plugin systems, storage backends, and pipeline
processors use these helpers instead of calling `importlib` directly.

Swap any dependency by changing its dotted path in settings — no call sites
need to change.
"""

import importlib
from typing import Any


def resolve(dotted_path: str) -> Any:
    """Import and return the object at the given dotted path.

    Use this when you need the class or callable itself (e.g., to inspect it,
    store it, or instantiate it with custom arguments). Use resolve_instance
    when you just need a no-argument instantiation.

    Args:
        dotted_path: A fully qualified dotted path, e.g.
            ``"apps.dms_ingestion.storage.LocalStorageBackend"``.

    Returns:
        The imported object (class, function, or any module-level name).

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the name does not exist on the module.
    """
    module_path, name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, name)


def resolve_instance(dotted_path: str) -> Any:
    """Import, instantiate with no arguments, and return the object.

    Convenience wrapper around resolve() for the common case of resolving a
    class and immediately calling it with no constructor arguments. If the
    class requires arguments, use resolve() and instantiate manually.

    Args:
        dotted_path: A fully qualified dotted path to a class, e.g.
            ``"apps.dms_ingestion.storage.LocalStorageBackend"``.

    Returns:
        A new instance of the resolved class.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the name does not exist on the module.
    """
    return resolve(dotted_path)()
