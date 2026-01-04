"""Store - Hierarchical data storage primitive for Tome.

A clean abstraction over SQLite for tree-structured data with:
- Path-based access via buffer hierarchy
- Soft delete and restore
- List containers
- No global state
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

# Data type constants
TYPE_VALUE = "value"
TYPE_BUFFER = "buffer"
TYPE_LIST = "list"

# Type alias for entry dictionaries
Entry = dict


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Convert SQLite rows to dictionaries."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class Store:
    """Hierarchical data store.

    Manages a tree of entries where:
    - Each entry lives in a buffer (buffer_id)
    - Buffers can be nested (parent_id references)
    - Entries can be values, buffers, or lists
    - Soft delete preserves data for restoration
    """

    def __init__(self, db_path: Union[str, Path], default_buffer_id: int = 1):
        """Initialize store with database path.

        Args:
            db_path: Path to SQLite database file
            default_buffer_id: Default buffer for operations (usually root=1)
        """
        self.db_path = Path(db_path)
        self.default_buffer_id = default_buffer_id
        self._init_db()

    def _connect(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Get database connection and cursor."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        return conn, cursor

    def _init_db(self):
        """Initialize database schema if needed."""
        conn, cursor = self._connect()
        try:
            # Check if lore table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='lore'"
            )
            if cursor.fetchone() is None:
                # Create schema
                cursor.execute("""
                    CREATE TABLE lore (
                        id INTEGER PRIMARY KEY,
                        data_type VARCHAR,
                        buffer_id INTEGER,
                        parent_id INTEGER,
                        item_index INTEGER,
                        value VARCHAR,
                        label VARCHAR,
                        key VARCHAR,
                        datetime TIMESTAMP,
                        deleted BOOLEAN DEFAULT 0
                    )
                """)
                # Create root buffer
                cursor.execute("""
                    INSERT INTO lore (id, data_type, buffer_id, value, label, key, datetime, parent_id)
                    VALUES (1, 'buffer', 1, 1, 'root buffer', null, ?, null)
                """, (datetime.now().isoformat(),))
                conn.commit()
            else:
                # Check for deleted column (migration)
                cursor.execute("PRAGMA table_info(lore)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "deleted" not in columns:
                    cursor.execute(
                        "ALTER TABLE lore ADD COLUMN deleted BOOLEAN DEFAULT 0"
                    )
                    conn.commit()
        finally:
            conn.close()

    # =========================================================================
    # Core CRUD Operations
    # =========================================================================

    def get(self, key: str, buffer_id: int = None) -> Optional[Entry]:
        """Get the most recent entry at a key.

        Args:
            key: The key to look up
            buffer_id: Which buffer to look in (default: default_buffer_id)

        Returns:
            Entry dict or None if not found
        """
        if key is None:
            raise ValueError("key cannot be None")

        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE key = ? AND buffer_id = ?
                AND (deleted IS NULL OR deleted = 0)
                ORDER BY id DESC LIMIT 1
            """, (key, buffer_id))
            return cursor.fetchone()
        finally:
            conn.close()

    def set(
        self,
        key: str,
        value: str,
        buffer_id: int = None,
        label: str = None,
        data_type: str = TYPE_VALUE,
        parent_id: int = None,
        item_index: int = None,
    ) -> Entry:
        """Store a value at a key.

        Args:
            key: The key to store at
            value: The value to store
            buffer_id: Which buffer to store in (default: default_buffer_id)
            label: Optional descriptive label
            data_type: Entry type (value, buffer, list)
            parent_id: Parent reference for hierarchy
            item_index: Position in list (if applicable)

        Returns:
            The created entry
        """
        if key is None:
            raise ValueError("key cannot be None")
        if value is None:
            raise ValueError("value cannot be None")

        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                INSERT INTO lore (data_type, value, label, key, datetime, buffer_id, parent_id, item_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data_type, value, label, key, datetime.now().isoformat(),
                  buffer_id, parent_id, item_index))
            conn.commit()

            entry_id = cursor.lastrowid
            cursor.execute("SELECT * FROM lore WHERE id = ?", (entry_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def delete(self, key: str, buffer_id: int = None) -> bool:
        """Soft delete the most recent entry at a key.

        Args:
            key: The key to delete
            buffer_id: Which buffer to delete from

        Returns:
            True if an entry was deleted, False if not found
        """
        entry = self.get(key, buffer_id)
        if entry is None:
            return False

        return self.delete_entry(entry["id"])

    def delete_entry(self, entry_id: int) -> bool:
        """Soft delete an entry by ID.

        Args:
            entry_id: The entry ID to delete

        Returns:
            True if deleted successfully
        """
        conn, cursor = self._connect()
        try:
            cursor.execute(
                "UPDATE lore SET deleted = 1 WHERE id = ?",
                (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def restore(self, entry_id: int) -> tuple[bool, str]:
        """Restore a soft-deleted entry.

        Args:
            entry_id: The entry ID to restore

        Returns:
            Tuple of (success, message)
        """
        conn, cursor = self._connect()
        try:
            # Check if entry exists
            cursor.execute("SELECT * FROM lore WHERE id = ?", (entry_id,))
            entry = cursor.fetchone()
            if entry is None:
                return False, "Entry not found"

            # Check if already active
            if not entry.get("deleted"):
                return True, "Entry already active"

            # Check for conflict
            if entry["key"]:
                cursor.execute("""
                    SELECT id FROM lore
                    WHERE key = ? AND buffer_id = ?
                    AND (deleted IS NULL OR deleted = 0)
                    LIMIT 1
                """, (entry["key"], entry["buffer_id"]))
                if cursor.fetchone():
                    return False, "Conflict: active entry exists at same key"

            # Restore
            cursor.execute(
                "UPDATE lore SET deleted = 0 WHERE id = ?",
                (entry_id,)
            )
            conn.commit()
            return True, "Restored successfully"
        finally:
            conn.close()

    def history(
        self,
        key: str,
        buffer_id: int = None,
        include_deleted: bool = False
    ) -> list[Entry]:
        """Get all entries at a key, ordered by datetime descending.

        Args:
            key: The key to get history for
            buffer_id: Which buffer to look in
            include_deleted: Whether to include soft-deleted entries

        Returns:
            List of entries, newest first
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            if include_deleted:
                cursor.execute("""
                    SELECT * FROM lore
                    WHERE key = ? AND buffer_id = ?
                    ORDER BY datetime DESC
                """, (key, buffer_id))
            else:
                cursor.execute("""
                    SELECT * FROM lore
                    WHERE key = ? AND buffer_id = ?
                    AND (deleted IS NULL OR deleted = 0)
                    ORDER BY datetime DESC
                """, (key, buffer_id))
            return cursor.fetchall()
        finally:
            conn.close()

    def children(self, buffer_id: int = None) -> list[Entry]:
        """Get all entries in a buffer.

        Args:
            buffer_id: Which buffer to list (default: default_buffer_id)

        Returns:
            List of entries in the buffer
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE buffer_id = ?
                AND (deleted IS NULL OR deleted = 0)
                AND id != 1
                ORDER BY datetime DESC
            """, (buffer_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    # =========================================================================
    # Buffer Operations
    # =========================================================================

    def is_buffer(self, key: str, buffer_id: int = None) -> bool:
        """Check if a key contains a buffer.

        Args:
            key: The key to check
            buffer_id: Which buffer to look in

        Returns:
            True if key is a buffer
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE key = ? AND buffer_id = ? AND data_type = ?
                AND (deleted IS NULL OR deleted = 0)
                ORDER BY id DESC LIMIT 1
            """, (key, buffer_id, TYPE_BUFFER))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_buffer(self, key: str, buffer_id: int = None) -> int:
        """Create a new buffer at a key.

        Args:
            key: The key to create buffer at
            buffer_id: Which buffer to create in (default: default_buffer_id)

        Returns:
            The new buffer's ID
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        new_id = self._new_buffer_id()

        self.set(
            key=key,
            value=str(new_id),
            buffer_id=buffer_id,
            data_type=TYPE_BUFFER,
            parent_id=buffer_id,
        )
        return new_id

    def delete_buffer(self, buffer_id: int) -> tuple[bool, str]:
        """Recursively delete a buffer and its contents.

        Args:
            buffer_id: The buffer ID to delete

        Returns:
            Tuple of (success, message)
        """
        if buffer_id is None:
            raise ValueError("buffer_id cannot be None")

        if buffer_id == 1:
            return False, "Cannot delete root buffer"

        conn, cursor = self._connect()
        try:
            # Find the buffer entry
            cursor.execute("""
                SELECT id, buffer_id, key FROM lore
                WHERE value = ? AND data_type = 'buffer'
            """, (str(buffer_id),))
            buffer_entry = cursor.fetchone()

            if buffer_entry is None:
                return False, "Buffer not found"

            # Mark buffer entry as deleted
            cursor.execute(
                "UPDATE lore SET deleted = 1 WHERE id = ?",
                (buffer_entry["id"],)
            )

            # Find sub-buffers BEFORE marking as deleted
            cursor.execute("""
                SELECT value FROM lore
                WHERE buffer_id = ? AND data_type = 'buffer'
                AND (deleted IS NULL OR deleted = 0)
            """, (buffer_id,))
            sub_buffers = cursor.fetchall()

            # Mark all entries in buffer as deleted
            cursor.execute(
                "UPDATE lore SET deleted = 1 WHERE buffer_id = ?",
                (buffer_id,)
            )

            conn.commit()

            # Recursively delete sub-buffers
            for sub in sub_buffers:
                try:
                    sub_id = int(sub["value"])
                    if sub_id != buffer_id:  # Prevent self-reference loops
                        self.delete_buffer(sub_id)
                except (ValueError, TypeError):
                    pass

            return True, "Buffer deleted"
        finally:
            conn.close()

    def enter_buffer(self, key: str, buffer_id: int = None) -> Optional[int]:
        """Get the buffer ID for entering a buffer at a key.

        Args:
            key: The key containing the buffer
            buffer_id: Which buffer to look in

        Returns:
            The buffer ID to enter, or None if not a buffer
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE key = ? AND buffer_id = ? AND data_type = ?
                AND (deleted IS NULL OR deleted = 0)
                ORDER BY id DESC LIMIT 1
            """, (key, buffer_id, TYPE_BUFFER))
            entry = cursor.fetchone()

            if entry is None:
                return None

            try:
                return int(entry["value"])
            except (ValueError, TypeError):
                return None
        finally:
            conn.close()

    def _new_buffer_id(self) -> int:
        """Generate a new unique buffer ID."""
        conn, cursor = self._connect()
        try:
            # Buffer IDs are stored in the value column of buffer entries
            # Also check buffer_id column for the highest ID in use
            cursor.execute("""
                SELECT MAX(CAST(value AS INTEGER)) as max_val FROM lore
                WHERE data_type = 'buffer' AND value IS NOT NULL
            """)
            result = cursor.fetchone()
            max_from_value = result["max_val"] if result and result["max_val"] else 1

            cursor.execute("SELECT MAX(buffer_id) as max_id FROM lore")
            result = cursor.fetchone()
            max_from_buffer = result["max_id"] if result and result["max_id"] else 1

            return max(max_from_value, max_from_buffer) + 1
        finally:
            conn.close()

    # =========================================================================
    # List Operations
    # =========================================================================

    def is_list(self, key: str, buffer_id: int = None) -> bool:
        """Check if a key contains a list.

        Args:
            key: The key to check
            buffer_id: Which buffer to look in

        Returns:
            True if key is a list
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE key = ? AND buffer_id = ? AND data_type = ?
                AND (deleted IS NULL OR deleted = 0)
                ORDER BY id DESC LIMIT 1
            """, (key, buffer_id, TYPE_LIST))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_list(self, key: str, buffer_id: int = None) -> int:
        """Create a list at a key, optionally converting existing value.

        Args:
            key: The key to create list at
            buffer_id: Which buffer to create in

        Returns:
            The list entry's ID
        """
        buffer_id = buffer_id if buffer_id is not None else self.default_buffer_id

        # Check for existing entry
        existing = self.get(key, buffer_id)

        # Create the list entry
        list_entry = self.set(
            key=key,
            value="",
            buffer_id=buffer_id,
            data_type=TYPE_LIST,
        )
        list_id = list_entry["id"]

        # If there was an existing value, convert it to first list item
        if existing and existing.get("data_type") == TYPE_VALUE:
            # Soft delete the old entry
            self.delete_entry(existing["id"])
            # Add its value as first item
            self._add_list_item(list_id, existing["value"], buffer_id, 0)

        return list_id

    def list_items(self, list_id: int) -> list[Entry]:
        """Get all items in a list, ordered by index.

        Args:
            list_id: The list entry's ID

        Returns:
            List of items ordered by item_index
        """
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                SELECT * FROM lore
                WHERE parent_id = ?
                AND (deleted IS NULL OR deleted = 0)
                ORDER BY item_index ASC
            """, (list_id,))
            return cursor.fetchall()
        finally:
            conn.close()

    def append_to_list(self, list_id: int, value: str) -> int:
        """Append a value to a list.

        Args:
            list_id: The list entry's ID
            value: The value to append

        Returns:
            The index of the new item
        """
        # Get current items to determine next index
        items = self.list_items(list_id)
        next_index = len(items)

        # Get the list entry to find its buffer_id
        conn, cursor = self._connect()
        try:
            cursor.execute("SELECT * FROM lore WHERE id = ?", (list_id,))
            list_entry = cursor.fetchone()
            if list_entry is None:
                raise ValueError(f"List {list_id} not found")
            buffer_id = list_entry["buffer_id"]
        finally:
            conn.close()

        self._add_list_item(list_id, value, buffer_id, next_index)
        return next_index

    def _add_list_item(
        self,
        list_id: int,
        value: str,
        buffer_id: int,
        index: int
    ) -> Entry:
        """Add an item to a list at a specific index."""
        conn, cursor = self._connect()
        try:
            cursor.execute("""
                INSERT INTO lore (data_type, value, label, key, datetime, buffer_id, parent_id, item_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (TYPE_VALUE, value, None, None, datetime.now().isoformat(),
                  buffer_id, list_id, index))
            conn.commit()

            entry_id = cursor.lastrowid
            cursor.execute("SELECT * FROM lore WHERE id = ?", (entry_id,))
            return cursor.fetchone()
        finally:
            conn.close()
