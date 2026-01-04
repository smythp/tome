"""Handler discovery for teller.

Auto-discovers and registers handlers from the handlers/ directory.
Drop a .py file with a BaseHandler subclass and it gets picked up.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, Type

from .base import BaseHandler

logger = logging.getLogger(__name__)


def discover_handlers(handlers_dir: Path = None) -> Dict[str, BaseHandler]:
    """Discover and instantiate handlers from a directory.

    Scans the given directory for .py files, imports them, and looks
    for classes that inherit from BaseHandler. Each valid handler is
    instantiated and registered under its name property.

    Args:
        handlers_dir: Directory to scan. Defaults to ./handlers/ relative
                      to this module.

    Returns:
        Dict mapping handler names to handler instances.
    """
    if handlers_dir is None:
        handlers_dir = Path(__file__).parent / "handlers"

    handlers: Dict[str, BaseHandler] = {}

    if not handlers_dir.exists():
        logger.warning(f"[teller] Handlers directory not found: {handlers_dir}")
        return handlers

    for file_path in handlers_dir.glob("*.py"):
        # Skip __init__.py and private files
        if file_path.stem.startswith("_"):
            continue

        try:
            # Load the module
            module = _load_module_from_path(file_path)
            if module is None:
                continue

            # Find BaseHandler subclasses
            for item_name in dir(module):
                if item_name.startswith("_"):
                    continue

                item = getattr(module, item_name)

                # Check if it's a class that inherits from BaseHandler
                if (isinstance(item, type) and
                    issubclass(item, BaseHandler) and
                    item is not BaseHandler):

                    try:
                        # Instantiate and register
                        instance = item()
                        handler_name = instance.name
                        handlers[handler_name] = instance
                        logger.debug(f"[teller] Registered handler: {handler_name}")
                    except Exception as e:
                        logger.warning(
                            f"[teller] Failed to instantiate handler "
                            f"{item_name} from {file_path}: {e}"
                        )

        except Exception as e:
            logger.warning(f"[teller] Failed to load {file_path}: {e}")

    return handlers


def _load_module_from_path(file_path: Path):
    """Load a Python module from a file path.

    Args:
        file_path: Path to the .py file.

    Returns:
        The loaded module, or None if loading failed.
    """
    module_name = f"teller.handlers.{file_path.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    except Exception as e:
        logger.warning(f"[teller] Import error for {file_path}: {e}")
        return None
