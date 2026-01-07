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

    def get(self, entry_id: int) -> dict | None:
        """Get entry by id."""
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

        Returns list of entry content/names from root to current buffer.

        Raises:
            RuntimeError: If path traversal exceeds 100,000 iterations
                         (indicates Store bug or malicious implementation)
        """
        result = []
        current_id = self._buffer_id
        max_iterations = 100_000

        # Walk from current up to root, collecting names
        visited = set()
        iterations = 0
        while current_id is not None and current_id not in visited:
            iterations += 1
            if iterations > max_iterations:
                raise RuntimeError(
                    f"Path traversal exceeded {max_iterations} iterations. "
                    f"This indicates a bug in Store.get() (non-deterministic or pathological data)."
                )

            visited.add(current_id)
            entry = self._store.get(current_id)
            if entry is None:
                break
            result.append(entry.get('content', f'buffer-{current_id}'))
            current_id = entry.get('buffer_id')  # parent

        # Reverse to get root-to-current order
        result.reverse()
        return result

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
