"""Gremlin tests - Adversarial attacks on the Store primitive.

These tests try to break the Store with malicious/malformed inputs.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_lore.db"


@pytest.fixture
def store(db_path):
    """Create a fresh Store instance with test database."""
    from store import Store
    return Store(db_path)


# ============================================================================
# Type Confusion Attacks
# ============================================================================

class TestTypeConfusion:
    """ATTACK: What happens with wrong types?"""

    def test_get_with_integer_key(self, store):
        """Integer key instead of string."""
        with pytest.raises((TypeError, ValueError, AttributeError)):
            store.get(123)

    def test_get_with_list_key(self, store):
        """List as key."""
        with pytest.raises((TypeError, ValueError)):
            store.get(["a", "b"])

    def test_get_with_dict_key(self, store):
        """Dict as key."""
        with pytest.raises((TypeError, ValueError)):
            store.get({"key": "value"})

    def test_set_with_integer_value(self, store):
        """Integer value instead of string."""
        # This might work due to SQLite's type affinity
        # but we should test the behavior
        try:
            entry = store.set("a", 123)
            # If it works, value should be stringified or stored as-is
            assert entry is not None
        except (TypeError, ValueError):
            pass  # Also acceptable

    def test_set_with_bytes_value(self, store):
        """Bytes value instead of string."""
        try:
            entry = store.set("a", b"binary data")
            retrieved = store.get("a")
            # Should either work or raise
            assert retrieved is not None
        except (TypeError, ValueError, sqlite3.ProgrammingError):
            pass

    def test_buffer_id_as_string(self, store):
        """String buffer_id instead of int."""
        with pytest.raises((TypeError, ValueError, sqlite3.InterfaceError)):
            store.get("a", buffer_id="not_an_int")

    def test_buffer_id_as_float(self, store):
        """Float buffer_id instead of int."""
        # Float might be truncated to int by SQLite
        store.set("a", "value", buffer_id=1)
        result = store.get("a", buffer_id=1.5)
        # Might work (truncated to 1) or raise


class TestMalformedInputs:
    """ATTACK: Invalid but syntactically correct inputs."""

    def test_empty_key(self, store):
        """Empty string as key."""
        # Empty string is technically valid
        entry = store.set("", "value")
        assert store.get("")["value"] == "value"

    def test_whitespace_only_key(self, store):
        """Whitespace-only key."""
        entry = store.set("   ", "value")
        assert store.get("   ")["value"] == "value"

    def test_newline_in_key(self, store):
        """Key with newlines."""
        entry = store.set("line1\nline2", "value")
        assert store.get("line1\nline2")["value"] == "value"

    def test_null_byte_in_key(self, store):
        """Key with null bytes."""
        # Null bytes can cause issues with C-based libraries
        try:
            entry = store.set("a\x00b", "value")
            # If it succeeds, retrieval should work too
            assert store.get("a\x00b") is not None
        except (ValueError, sqlite3.ProgrammingError):
            pass

    def test_null_byte_in_value(self, store):
        """Value with null bytes."""
        try:
            entry = store.set("key", "val\x00ue")
            retrieved = store.get("key")
            assert retrieved is not None
        except (ValueError, sqlite3.ProgrammingError):
            pass

    def test_very_long_key(self, store):
        """Extremely long key."""
        long_key = "x" * 10000
        entry = store.set(long_key, "value")
        assert store.get(long_key)["value"] == "value"

    def test_negative_buffer_id(self, store):
        """Negative buffer_id."""
        # Should work (it's just a number) but find nothing
        result = store.get("a", buffer_id=-1)
        assert result is None

    def test_zero_buffer_id(self, store):
        """Zero buffer_id."""
        result = store.get("a", buffer_id=0)
        assert result is None

    def test_huge_buffer_id(self, store):
        """Very large buffer_id."""
        result = store.get("a", buffer_id=2**62)
        assert result is None


class TestUnicodeEdgeCases:
    """ATTACK: Unicode edge cases and normalization."""

    def test_emoji_key(self, store):
        """Emoji as key."""
        store.set("🔥", "fire")
        assert store.get("🔥")["value"] == "fire"

    def test_mixed_scripts(self, store):
        """Mixed script characters."""
        store.set("Hello世界مرحبا", "mixed")
        assert store.get("Hello世界مرحبا")["value"] == "mixed"

    def test_rtl_text(self, store):
        """Right-to-left text."""
        store.set("مفتاح", "قيمة")
        assert store.get("مفتاح")["value"] == "قيمة"

    def test_zalgo_text(self, store):
        """Zalgo/combining characters."""
        zalgo = "H̸̡̪̯ͨ͊̽̅̾ẹ̶̱̹͖͉̠̮̥̤͡c̨̫̤̩̥̖̤̪ͅo̢͚̦͍̻̰͠m̷̘̞͚͈̞̬̻̜e̳̩͟ͅs̸̤̱̣͕̼̰̱̬̗"
        store.set(zalgo, "value")
        assert store.get(zalgo)["value"] == "value"

    def test_zero_width_chars(self, store):
        """Zero-width characters."""
        # Zero-width joiner and non-joiner
        key_with_zwj = "a\u200db"
        store.set(key_with_zwj, "value")
        # Should retrieve exactly (no normalization)
        assert store.get(key_with_zwj)["value"] == "value"
        # Different key without ZWJ should not match
        assert store.get("ab") is None

    def test_bom_in_value(self, store):
        """Byte Order Mark in value."""
        store.set("key", "\ufeffvalue")
        assert store.get("key")["value"] == "\ufeffvalue"

    def test_surrogate_pairs(self, store):
        """Characters outside BMP (surrogate pairs in UTF-16)."""
        # Mathematical symbols, emoji, etc.
        store.set("math", "𝒜𝒷𝒸")
        assert store.get("math")["value"] == "𝒜𝒷𝒸"


class TestSQLInjection:
    """ATTACK: SQL injection attempts."""

    def test_sql_in_key(self, store):
        """SQL injection in key."""
        malicious = "'; DROP TABLE lore; --"
        store.set(malicious, "value")
        # Table should still exist, and we should get our value
        assert store.get(malicious)["value"] == "value"

    def test_sql_in_value(self, store):
        """SQL injection in value."""
        malicious = "value'; DROP TABLE lore; --"
        store.set("key", malicious)
        assert store.get("key")["value"] == malicious

    def test_sql_in_label(self, store):
        """SQL injection in label."""
        malicious = "label'; DROP TABLE lore; --"
        store.set("key", "value", label=malicious)
        assert store.get("key")["label"] == malicious

    def test_format_string_attack(self, store):
        """Format string characters."""
        store.set("key", "%s %d %x")
        assert store.get("key")["value"] == "%s %d %x"


class TestMemoryAttacks:
    """ATTACK: Memory/resource exhaustion."""

    def test_very_large_value(self, store):
        """Value approaching memory limits."""
        # 10MB value
        large = "x" * (10 * 1024 * 1024)
        entry = store.set("big", large)
        assert store.get("big")["value"] == large

    def test_many_entries_same_key(self, store):
        """Many entries at the same key."""
        for i in range(1000):
            store.set("key", f"value_{i}")
        history = store.history("key")
        assert len(history) == 1000

    def test_deeply_nested_buffers(self, store):
        """Many levels of buffer nesting."""
        current_buffer = 1
        for i in range(50):  # 50 levels deep
            new_id = store.create_buffer(f"level_{i}", buffer_id=current_buffer)
            current_buffer = new_id
        # Should be able to set/get at deepest level
        store.set("deep", "value", buffer_id=current_buffer)
        assert store.get("deep", buffer_id=current_buffer)["value"] == "value"

    def test_many_buffers(self, store):
        """Many sibling buffers."""
        for i in range(100):
            store.create_buffer(f"buffer_{i}")
        # All should exist
        for i in range(100):
            assert store.is_buffer(f"buffer_{i}")


class TestConcurrencyAttacks:
    """ATTACK: Race conditions and concurrent access."""

    def test_multiple_stores_read_own_writes(self, store, db_path):
        """Multiple Store instances see each other's writes."""
        from store import Store
        store2 = Store(db_path)

        store.set("shared", "from_store1")
        assert store2.get("shared")["value"] == "from_store1"

        store2.set("shared", "from_store2")
        assert store.get("shared")["value"] == "from_store2"


class TestMutationSafety:
    """ATTACK: Mutating returned data."""

    def test_mutate_returned_entry(self, store):
        """Modifying returned entry doesn't affect store."""
        store.set("key", "original")
        entry = store.get("key")
        entry["value"] = "mutated"

        # Store should still have original
        fresh = store.get("key")
        assert fresh["value"] == "original"

    def test_mutate_history_list(self, store):
        """Modifying history list doesn't affect store."""
        store.set("key", "v1")
        store.set("key", "v2")
        history = store.history("key")
        history.clear()

        # Store should still have history
        fresh_history = store.history("key")
        assert len(fresh_history) == 2


class TestDeleteEdgeCases:
    """ATTACK: Edge cases around deletion."""

    def test_delete_already_deleted(self, store):
        """Deleting already deleted entry."""
        store.set("key", "value")
        store.delete("key")
        # Second delete should be safe
        result = store.delete("key")
        assert result is False  # Nothing to delete

    def test_restore_twice(self, store):
        """Restoring an entry twice."""
        entry = store.set("key", "value")
        store.delete("key")
        store.restore(entry["id"])
        # Second restore should be safe
        success, msg = store.restore(entry["id"])
        assert success is True  # Already active, no-op

    def test_delete_buffer_that_contains_buffers(self, store):
        """Delete buffer with nested buffers inside."""
        outer = store.create_buffer("outer")
        inner = store.create_buffer("inner", buffer_id=outer)
        store.set("item", "value", buffer_id=inner)

        store.delete_buffer(outer)

        # Everything should be deleted
        assert store.is_buffer("outer") is False
        assert store.get("item", buffer_id=inner) is None


class TestListEdgeCases:
    """ATTACK: Edge cases around lists."""

    def test_append_to_deleted_list(self, store):
        """Appending to a deleted list."""
        list_id = store.create_list("mylist")
        store.delete("mylist")

        # Appending to deleted list should probably fail
        with pytest.raises((ValueError, KeyError)):
            store.append_to_list(list_id, "value")

    def test_list_items_of_value(self, store):
        """Getting list items of a regular value's ID."""
        entry = store.set("key", "value")
        # Treating a value ID as a list ID
        items = store.list_items(entry["id"])
        assert items == []  # No items, not a list

    def test_create_list_at_buffer(self, store):
        """Creating a list at a key that's a buffer."""
        store.create_buffer("mybuffer")
        # Creating list should probably work (creates new entry)
        list_id = store.create_list("mybuffer")
        assert store.is_list("mybuffer")
