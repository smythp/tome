"""
Mark RSP - Position and session state tracking.

Tracks where you are in hierarchical data:
- buffer_id: current position
- stack: navigation history (for back())
- last_retrieved: last entry accessed (opaque storage)
- path: human-readable breadcrumb (requires Store)
"""

from typing import Any, Protocol


class Store(Protocol):
    """Protocol for data store (from store.store.Store)."""

    def get_buffer_entry(self, buffer_id: int) -> dict | None:
        """Get an active buffer entry by logical buffer ID."""
        ...


class Mark:
    """
    Position and session state tracker.

    Tracks current location in hierarchical data and provides
    navigation (into/back/reset) with history.
    """

    def __init__(self, store: Store, buffer_id: int = 1):
        """
        Create Mark instance.

        Args:
            store: Data store for resolving paths
            buffer_id: Initial buffer_id (default 1 = root)

        Raises:
            TypeError: If buffer_id is not an int
        """
        if not isinstance(buffer_id, int):
            raise TypeError(f"buffer_id must be int, got {type(buffer_id).__name__}")

        self._store = store
        self._buffer_id = buffer_id
        self._stack: list[int] = []
        self._last_retrieved: Any = None

    @property
    def buffer_id(self) -> int:
        """Current buffer_id."""
        return self._buffer_id

    @property
    def stack(self) -> list[int]:
        """Navigation history stack."""
        return self._stack

    @property
    def last_retrieved(self) -> Any:
        """Last retrieved entry (opaque storage)."""
        return self._last_retrieved

    @last_retrieved.setter
    def last_retrieved(self, value: Any) -> None:
        """Set last retrieved entry."""
        self._last_retrieved = value

    @property
    def path(self) -> list[str]:
        """
        Human-readable breadcrumb from root to current position.

        Returns list of buffer names from root to current buffer.

        Raises:
            RuntimeError: If path traversal exceeds 100,000 iterations
                         (indicates Store bug or malicious implementation)
        """
        result = []
        current_id = self._buffer_id
        max_iterations = 100_000

        visited = set()
        iterations = 0
        while current_id is not None and current_id not in visited:
            iterations += 1
            if iterations > max_iterations:
                raise RuntimeError(
                    f"Path traversal exceeded {max_iterations} iterations. "
                    f"This indicates a bug in Store.get_buffer_entry() "
                    f"(non-deterministic or pathological data)."
                )

            visited.add(current_id)
            entry = self._get_buffer_entry(current_id)
            if entry is None:
                break
            result.append(self._buffer_name(entry, current_id))
            current_id = self._parent_buffer_id(entry)

        result.reverse()
        return result

    def _get_buffer_entry(self, buffer_id: int) -> dict | None:
        """Resolve a buffer entry using the real Store API, with legacy test fallback."""
        get_buffer_entry = getattr(self._store, "get_buffer_entry", None)
        if callable(get_buffer_entry):
            return get_buffer_entry(buffer_id)

        return self._store.get(buffer_id)

    def _buffer_name(self, entry: dict, buffer_id: int) -> str:
        """Pick a spoken name for a buffer entry."""
        if buffer_id == 1 and entry.get("data_type") == "buffer":
            return "root"

        return (
            entry.get("key")
            or entry.get("label")
            or entry.get("content")
            or entry.get("value")
            or f"buffer-{buffer_id}"
        )

    def _parent_buffer_id(self, entry: dict) -> Any:
        """Return the parent buffer ID from real Store rows or legacy fixtures."""
        if "parent_id" in entry:
            return entry.get("parent_id")
        return entry.get("buffer_id")

    def into(self, buffer_id: int) -> 'Mark':
        """
        Navigate into a buffer.

        Pushes current buffer_id onto stack and sets new current.

        Args:
            buffer_id: Buffer to navigate into

        Returns:
            self (for chaining)

        Raises:
            TypeError: If buffer_id is not an int
        """
        if not isinstance(buffer_id, int):
            raise TypeError(f"buffer_id must be int, got {type(buffer_id).__name__}")

        self._stack.append(self._buffer_id)
        self._buffer_id = buffer_id
        return self

    def back(self) -> bool:
        """
        Navigate back to previous buffer.

        Pops stack and sets as current. No-op if stack is empty.

        Returns:
            True if navigated back, False if already at root/start

        Raises:
            TypeError: If stack contains non-int value
        """
        if not self._stack:
            return False

        buffer_id = self._stack.pop()
        if not isinstance(buffer_id, int):
            raise TypeError(f"buffer_id must be int, got {type(buffer_id).__name__}")

        self._buffer_id = buffer_id
        return True

    def reset(self) -> 'Mark':
        """
        Reset to root.

        Clears stack and sets buffer_id to 1.

        Returns:
            self (for chaining)
        """
        self._stack.clear()
        self._buffer_id = 1
        return self
