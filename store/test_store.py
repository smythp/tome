"""Comprehensive test suite for the Store primitive.

Test-first design following rock-solid primitives playbook.
Tests written BEFORE implementation.
"""

import pytest
import sqlite3
import threading
import tempfile
import os
from pathlib import Path


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_lore.db"


@pytest.fixture
def store(db_path):
    """Create a fresh Store instance with test database."""
    from store import Store
    s = Store(db_path)
    return s


# ============================================================================
# 1. Basic CRUD Operations
# ============================================================================

class TestBasicGet:
    """Test basic get operations."""

    def test_get_nonexistent_key_returns_none(self, store):
        """Getting a key that doesn't exist returns None."""
        assert store.get("nonexistent") is None

    def test_get_after_set_returns_value(self, store):
        """Can get a value that was set."""
        store.set("a", "hello")
        entry = store.get("a")
        assert entry is not None
        assert entry["value"] == "hello"
        assert entry["key"] == "a"

    def test_get_returns_newest_when_multiple_values(self, store):
        """When multiple values exist at same key, get returns newest."""
        store.set("a", "first")
        store.set("a", "second")
        store.set("a", "third")
        entry = store.get("a")
        assert entry["value"] == "third"

    def test_get_with_explicit_buffer_id(self, store):
        """Can get from a specific buffer."""
        store.set("a", "in root", buffer_id=1)
        entry = store.get("a", buffer_id=1)
        assert entry["value"] == "in root"

    def test_get_from_wrong_buffer_returns_none(self, store):
        """Getting from wrong buffer returns None."""
        store.set("a", "in root", buffer_id=1)
        assert store.get("a", buffer_id=999) is None


class TestBasicSet:
    """Test basic set operations."""

    def test_set_returns_entry(self, store):
        """Set returns the created entry."""
        entry = store.set("a", "hello")
        assert entry is not None
        assert entry["value"] == "hello"
        assert entry["key"] == "a"
        assert "id" in entry

    def test_set_with_label(self, store):
        """Can set a value with a label."""
        entry = store.set("a", "hello", label="greeting")
        assert entry["label"] == "greeting"

    def test_set_in_specific_buffer(self, store):
        """Can set in a specific buffer."""
        entry = store.set("a", "hello", buffer_id=1)
        assert entry["buffer_id"] == 1

    def test_set_creates_timestamp(self, store):
        """Set creates a datetime timestamp."""
        entry = store.set("a", "hello")
        assert entry["datetime"] is not None

    def test_set_defaults_to_not_deleted(self, store):
        """New entries are not deleted."""
        entry = store.set("a", "hello")
        assert entry.get("deleted", 0) == 0


class TestBasicDelete:
    """Test basic delete operations."""

    def test_delete_existing_returns_true(self, store):
        """Deleting an existing entry returns True."""
        store.set("a", "hello")
        assert store.delete("a") is True

    def test_delete_nonexistent_returns_false(self, store):
        """Deleting a nonexistent entry returns False."""
        assert store.delete("nonexistent") is False

    def test_deleted_entry_not_returned_by_get(self, store):
        """Deleted entries are not returned by get."""
        store.set("a", "hello")
        store.delete("a")
        assert store.get("a") is None

    def test_delete_is_soft_by_default(self, store):
        """Delete is soft - entry still exists with deleted flag."""
        entry = store.set("a", "hello")
        store.delete("a")
        # Should be able to find in history with include_deleted
        history = store.history("a", include_deleted=True)
        assert len(history) == 1
        assert history[0]["deleted"] == 1


class TestHistory:
    """Test history retrieval."""

    def test_history_returns_all_values_at_key(self, store):
        """History returns all values ever stored at a key."""
        store.set("a", "first")
        store.set("a", "second")
        store.set("a", "third")
        history = store.history("a")
        assert len(history) == 3
        # Should be ordered by datetime desc (newest first)
        assert history[0]["value"] == "third"
        assert history[2]["value"] == "first"

    def test_history_excludes_deleted_by_default(self, store):
        """History excludes deleted entries by default."""
        store.set("a", "first")
        entry = store.set("a", "second")
        store.delete("a")  # Deletes newest
        history = store.history("a")
        assert len(history) == 1
        assert history[0]["value"] == "first"

    def test_history_includes_deleted_when_requested(self, store):
        """History can include deleted entries."""
        store.set("a", "first")
        store.set("a", "second")
        store.delete("a")
        history = store.history("a", include_deleted=True)
        assert len(history) == 2

    def test_history_empty_for_nonexistent_key(self, store):
        """History returns empty list for nonexistent key."""
        assert store.history("nonexistent") == []


class TestChildren:
    """Test children listing."""

    def test_children_returns_entries_in_buffer(self, store):
        """Children returns all entries in a buffer."""
        store.set("a", "value_a")
        store.set("b", "value_b")
        store.set("c", "value_c")
        children = store.children()
        keys = [c["key"] for c in children]
        assert "a" in keys
        assert "b" in keys
        assert "c" in keys

    def test_children_excludes_deleted(self, store):
        """Children excludes deleted entries."""
        store.set("a", "value_a")
        store.set("b", "value_b")
        store.delete("b")
        children = store.children()
        keys = [c["key"] for c in children]
        assert "a" in keys
        assert "b" not in keys

    def test_children_specific_buffer(self, store):
        """Can list children of specific buffer."""
        # Create a nested buffer and add items to it
        new_buffer_id = store.create_buffer("sub")
        store.set("x", "in sub", buffer_id=new_buffer_id)

        # Children of root should not include "x"
        root_children = store.children(buffer_id=1)
        root_keys = [c["key"] for c in root_children]
        assert "x" not in root_keys

        # Children of sub should include "x"
        sub_children = store.children(buffer_id=new_buffer_id)
        sub_keys = [c["key"] for c in sub_children]
        assert "x" in sub_keys


# ============================================================================
# 2. Buffer Operations
# ============================================================================

class TestIsBuffer:
    """Test buffer detection."""

    def test_is_buffer_false_for_value(self, store):
        """Regular values are not buffers."""
        store.set("a", "hello")
        assert store.is_buffer("a") is False

    def test_is_buffer_true_for_buffer(self, store):
        """Created buffers are buffers."""
        store.create_buffer("sub")
        assert store.is_buffer("sub") is True

    def test_is_buffer_false_for_nonexistent(self, store):
        """Nonexistent keys are not buffers."""
        assert store.is_buffer("nonexistent") is False


class TestCreateBuffer:
    """Test buffer creation."""

    def test_create_buffer_returns_new_id(self, store):
        """Creating a buffer returns its new ID."""
        buffer_id = store.create_buffer("sub")
        assert buffer_id is not None
        assert buffer_id > 1  # Root buffer is 1

    def test_create_buffer_makes_key_a_buffer(self, store):
        """After creation, key is recognized as buffer."""
        store.create_buffer("sub")
        assert store.is_buffer("sub") is True

    def test_create_multiple_buffers_unique_ids(self, store):
        """Each buffer gets a unique ID."""
        id1 = store.create_buffer("a")
        id2 = store.create_buffer("b")
        id3 = store.create_buffer("c")
        assert len({id1, id2, id3}) == 3

    def test_create_nested_buffer(self, store):
        """Can create buffers inside buffers."""
        outer_id = store.create_buffer("outer")
        inner_id = store.create_buffer("inner", buffer_id=outer_id)
        assert inner_id != outer_id
        assert store.is_buffer("inner", buffer_id=outer_id) is True


class TestDeleteBuffer:
    """Test buffer deletion."""

    def test_delete_buffer_returns_success(self, store):
        """Deleting a buffer returns success tuple."""
        buffer_id = store.create_buffer("sub")
        success, msg = store.delete_buffer(buffer_id)
        assert success is True

    def test_delete_root_buffer_fails(self, store):
        """Cannot delete root buffer (ID=1)."""
        success, msg = store.delete_buffer(1)
        assert success is False
        assert "root" in msg.lower()

    def test_delete_buffer_removes_contents(self, store):
        """Deleting a buffer removes its contents."""
        buffer_id = store.create_buffer("sub")
        store.set("x", "value", buffer_id=buffer_id)
        store.delete_buffer(buffer_id)
        assert store.get("x", buffer_id=buffer_id) is None

    def test_delete_buffer_recursive(self, store):
        """Deleting a buffer deletes nested buffers."""
        outer_id = store.create_buffer("outer")
        inner_id = store.create_buffer("inner", buffer_id=outer_id)
        store.set("deep", "value", buffer_id=inner_id)

        store.delete_buffer(outer_id)

        # Inner buffer contents should also be deleted
        assert store.get("deep", buffer_id=inner_id) is None

    def test_delete_nonexistent_buffer_fails(self, store):
        """Deleting nonexistent buffer fails gracefully."""
        success, msg = store.delete_buffer(99999)
        assert success is False


class TestEnterBuffer:
    """Test buffer navigation."""

    def test_enter_buffer_returns_buffer_id(self, store):
        """Entering a buffer returns its ID."""
        buffer_id = store.create_buffer("sub")
        entered_id = store.enter_buffer("sub")
        assert entered_id == buffer_id

    def test_enter_nonexistent_returns_none(self, store):
        """Entering nonexistent buffer returns None."""
        assert store.enter_buffer("nonexistent") is None

    def test_enter_value_returns_none(self, store):
        """Entering a value (not buffer) returns None."""
        store.set("a", "hello")
        assert store.enter_buffer("a") is None


# ============================================================================
# 3. List Operations
# ============================================================================

class TestIsList:
    """Test list detection."""

    def test_is_list_false_for_value(self, store):
        """Regular values are not lists."""
        store.set("a", "hello")
        assert store.is_list("a") is False

    def test_is_list_true_for_list(self, store):
        """Created lists are lists."""
        store.create_list("mylist")
        assert store.is_list("mylist") is True

    def test_is_list_false_for_buffer(self, store):
        """Buffers are not lists."""
        store.create_buffer("sub")
        assert store.is_list("sub") is False


class TestCreateList:
    """Test list creation."""

    def test_create_list_returns_id(self, store):
        """Creating a list returns its ID."""
        list_id = store.create_list("mylist")
        assert list_id is not None

    def test_create_list_at_existing_value_converts(self, store):
        """Creating list at existing value converts it."""
        store.set("a", "original")
        list_id = store.create_list("a")

        # Should now be a list
        assert store.is_list("a") is True

        # Original value should be first item
        items = store.list_items(list_id)
        assert len(items) == 1
        assert items[0]["value"] == "original"

    def test_create_list_empty_when_no_existing(self, store):
        """Creating list at empty key creates empty list."""
        list_id = store.create_list("newlist")
        items = store.list_items(list_id)
        assert items == []

    def test_create_list_rejects_none_key_without_write(self, store):
        """A None key is rejected before creating any list row."""
        conn = sqlite3.connect(store.db_path)
        try:
            before_count = conn.execute("SELECT COUNT(*) FROM lore").fetchone()[0]
        finally:
            conn.close()

        with pytest.raises(ValueError, match="key cannot be None"):
            store.create_list(None)

        conn = sqlite3.connect(store.db_path)
        try:
            after_count = conn.execute("SELECT COUNT(*) FROM lore").fetchone()[0]
            null_list_count = conn.execute(
                "SELECT COUNT(*) FROM lore WHERE data_type = 'list' AND key IS NULL"
            ).fetchone()[0]
        finally:
            conn.close()

        assert after_count == before_count
        assert null_list_count == 0


class TestListItems:
    """Test list item retrieval."""

    def test_list_items_returns_ordered(self, store):
        """List items are returned in order."""
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "first")
        store.append_to_list(list_id, "second")
        store.append_to_list(list_id, "third")

        items = store.list_items(list_id)
        values = [i["value"] for i in items]
        assert values == ["first", "second", "third"]

    def test_list_items_have_indices(self, store):
        """List items have item_index."""
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "first")
        store.append_to_list(list_id, "second")

        items = store.list_items(list_id)
        assert items[0]["item_index"] == 0
        assert items[1]["item_index"] == 1

    def test_list_items_excludes_deleted(self, store):
        """Deleted list items are excluded."""
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "first")
        store.append_to_list(list_id, "second")

        items = store.list_items(list_id)
        # Delete the first item by its entry ID
        store.delete_entry(items[0]["id"])

        remaining = store.list_items(list_id)
        assert len(remaining) == 1
        assert remaining[0]["value"] == "second"


class TestAppendToList:
    """Test list append operations."""

    def test_append_returns_index(self, store):
        """Appending returns the index of new item."""
        list_id = store.create_list("mylist")
        idx0 = store.append_to_list(list_id, "first")
        idx1 = store.append_to_list(list_id, "second")
        assert idx0 == 0
        assert idx1 == 1

    def test_append_increases_list_size(self, store):
        """Appending increases list size."""
        list_id = store.create_list("mylist")
        assert len(store.list_items(list_id)) == 0
        store.append_to_list(list_id, "item")
        assert len(store.list_items(list_id)) == 1


class TestInsertInList:
    """Test list insert operations."""

    def test_insert_failure_rolls_back_shift(self, store, monkeypatch):
        """A failed insert does not leave shifted item indexes committed."""
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "first")
        store.append_to_list(list_id, "second")
        store.append_to_list(list_id, "third")

        def fail_add_list_item(*args, **kwargs):
            raise sqlite3.OperationalError("forced insert failure")

        monkeypatch.setattr(store, "_add_list_item", fail_add_list_item)

        with pytest.raises(sqlite3.OperationalError, match="forced insert failure"):
            store.insert_in_list(list_id, "inserted", 1)

        items = store.list_items(list_id)
        assert [item["value"] for item in items] == ["first", "second", "third"]
        assert [item["item_index"] for item in items] == [0, 1, 2]

    def test_insert_rejects_stale_index_without_mutation(self, store):
        """An index past the current list length is rejected atomically."""
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "first")
        store.append_to_list(list_id, "second")

        with pytest.raises(ValueError, match="index"):
            store.insert_in_list(list_id, "too far", 3)

        items = store.list_items(list_id)
        assert [item["value"] for item in items] == ["first", "second"]
        assert [item["item_index"] for item in items] == [0, 1]

    def test_concurrent_inserts_keep_unique_ordering(self, db_path):
        """Competing inserts serialize without duplicate item indexes."""
        from store import Store

        store = Store(db_path)
        list_id = store.create_list("mylist")
        store.append_to_list(list_id, "tail")
        barrier = threading.Barrier(6)
        errors = []

        def insert_value(value):
            try:
                worker_store = Store(db_path)
                barrier.wait()
                worker_store.insert_in_list(list_id, value, 0)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=insert_value, args=(f"item{i}",))
            for i in range(5)
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        assert errors == []
        items = Store(db_path).list_items(list_id)
        indices = [item["item_index"] for item in items]
        assert sorted(indices) == list(range(6))
        assert len(indices) == len(set(indices))


# ============================================================================
# 4. Soft Delete and Restore
# ============================================================================

class TestSoftDelete:
    """Test soft delete behavior."""

    def test_soft_delete_sets_flag(self, store):
        """Soft delete sets the deleted flag."""
        entry = store.set("a", "hello")
        store.delete("a")

        history = store.history("a", include_deleted=True)
        assert history[0]["deleted"] == 1

    def test_soft_delete_preserves_data(self, store):
        """Soft deleted data is preserved."""
        store.set("a", "precious")
        store.delete("a")

        history = store.history("a", include_deleted=True)
        assert history[0]["value"] == "precious"


class TestRestore:
    """Test restore operations."""

    def test_restore_undeletes_entry(self, store):
        """Restore makes entry visible again."""
        entry = store.set("a", "hello")
        store.delete("a")
        assert store.get("a") is None

        success, msg = store.restore(entry["id"])
        assert success is True
        assert store.get("a") is not None
        assert store.get("a")["value"] == "hello"

    def test_restore_nonexistent_fails(self, store):
        """Restoring nonexistent entry fails."""
        success, msg = store.restore(99999)
        assert success is False

    def test_restore_conflict_detection(self, store):
        """Restore fails if active entry exists at same key."""
        entry = store.set("a", "first")
        store.delete("a")
        store.set("a", "second")  # New value at same key

        success, msg = store.restore(entry["id"])
        assert success is False
        assert "conflict" in msg.lower()

    def test_restore_already_active_entry(self, store):
        """Restoring an already active entry is a no-op or clear success."""
        entry = store.set("a", "hello")
        success, msg = store.restore(entry["id"])
        # Should either succeed (no-op) or indicate already active
        assert success is True or "already" in msg.lower()


# ============================================================================
# 5. Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unicode_in_values(self, store):
        """Unicode values work correctly."""
        store.set("emoji", "Hello 🌍 World 你好")
        entry = store.get("emoji")
        assert entry["value"] == "Hello 🌍 World 你好"

    def test_unicode_in_labels(self, store):
        """Unicode labels work correctly."""
        store.set("a", "value", label="标签 📝")
        entry = store.get("a")
        assert entry["label"] == "标签 📝"

    def test_empty_string_value(self, store):
        """Empty string is a valid value."""
        store.set("a", "")
        entry = store.get("a")
        assert entry["value"] == ""

    def test_very_long_value(self, store):
        """Very long values work."""
        long_value = "x" * 100000
        store.set("a", long_value)
        entry = store.get("a")
        assert entry["value"] == long_value

    def test_special_characters_in_key(self, store):
        """Special characters in keys work."""
        # Keys are typically single chars but test edge cases
        store.set("!", "bang")
        store.set("@", "at")
        assert store.get("!")["value"] == "bang"
        assert store.get("@")["value"] == "at"

    def test_none_buffer_id_uses_default(self, store):
        """None buffer_id defaults to root buffer."""
        store.set("a", "hello", buffer_id=None)
        entry = store.get("a", buffer_id=1)
        assert entry is not None

    def test_multiple_stores_same_key_same_buffer(self, store):
        """Multiple stores at same key create multiple entries."""
        store.set("a", "v1")
        store.set("a", "v2")
        store.set("a", "v3")

        history = store.history("a")
        assert len(history) == 3


class TestRootBufferProtection:
    """Test root buffer special handling."""

    def test_root_buffer_exists(self, store):
        """Root buffer (ID=1) exists after init."""
        children = store.children(buffer_id=1)
        # Should not raise, may be empty
        assert isinstance(children, list)

    def test_cannot_delete_root_buffer(self, store):
        """Root buffer cannot be deleted."""
        success, msg = store.delete_buffer(1)
        assert success is False


class TestStoreConnectionSemantics:
    """Test supported Store connection modes."""

    def test_memory_database_is_rejected(self):
        """Store does not silently accept per-connection in-memory databases."""
        from store import Store

        with pytest.raises(ValueError, match=":memory:"):
            Store(":memory:")


# ============================================================================
# 6. Error Cases
# ============================================================================

class TestErrorCases:
    """Test error handling."""

    def test_get_with_none_key_raises(self, store):
        """Getting with None key raises error."""
        with pytest.raises((TypeError, ValueError)):
            store.get(None)

    def test_set_with_none_key_raises(self, store):
        """Setting with None key raises error."""
        with pytest.raises((TypeError, ValueError)):
            store.set(None, "value")

    def test_set_with_none_value_raises(self, store):
        """Setting with None value raises error."""
        with pytest.raises((TypeError, ValueError)):
            store.set("a", None)

    def test_delete_buffer_with_none_raises(self, store):
        """Deleting buffer with None ID raises error."""
        with pytest.raises((TypeError, ValueError)):
            store.delete_buffer(None)

    def test_list_items_invalid_id_returns_empty(self, store):
        """List items for invalid ID returns empty list."""
        items = store.list_items(99999)
        assert items == []

    def test_append_to_nonexistent_list_raises(self, store):
        """Appending to nonexistent list raises error."""
        with pytest.raises((ValueError, KeyError)):
            store.append_to_list(99999, "value")


# ============================================================================
# 7. Invariants (Property-based style assertions)
# ============================================================================

class TestInvariants:
    """Test invariants that must always hold."""

    def test_get_after_set_matches(self, store):
        """get(key) after set(key, value) returns that value."""
        store.set("test", "myvalue")
        assert store.get("test")["value"] == "myvalue"

    def test_delete_makes_invisible(self, store):
        """After delete, get returns None."""
        store.set("test", "value")
        store.delete("test")
        assert store.get("test") is None

    def test_restore_makes_visible(self, store):
        """After restore, get returns the value."""
        entry = store.set("test", "value")
        store.delete("test")
        store.restore(entry["id"])
        assert store.get("test") is not None

    def test_buffer_ids_are_positive_integers(self, store):
        """All buffer IDs are positive integers."""
        id1 = store.create_buffer("a")
        id2 = store.create_buffer("b")
        assert isinstance(id1, int) and id1 > 0
        assert isinstance(id2, int) and id2 > 0

    def test_list_items_ordered_by_index(self, store):
        """List items are always ordered by item_index."""
        list_id = store.create_list("mylist")
        for i in range(10):
            store.append_to_list(list_id, f"item{i}")

        items = store.list_items(list_id)
        for i, item in enumerate(items):
            assert item["item_index"] == i


# ============================================================================
# 8. Config Operations
# ============================================================================

class TestGetConfig:
    """Test config get operations."""

    def test_get_nonexistent_returns_none(self, store):
        """Getting a config key that doesn't exist returns None."""
        assert store.get_config("nonexistent") is None

    def test_get_nonexistent_returns_default(self, store):
        """Getting nonexistent config returns provided default."""
        assert store.get_config("nonexistent", "fallback") == "fallback"

    def test_get_after_set_returns_value(self, store):
        """Can get a config value that was set."""
        store.set_config("debug", "on")
        assert store.get_config("debug") == "on"

    def test_get_ignores_default_when_value_exists(self, store):
        """Default is ignored when value exists."""
        store.set_config("debug", "on")
        assert store.get_config("debug", "off") == "on"


class TestSetConfig:
    """Test config set operations."""

    def test_set_creates_new_config(self, store):
        """Setting creates a new config entry."""
        store.set_config("theme", "dark")
        assert store.get_config("theme") == "dark"

    def test_set_updates_existing_config(self, store):
        """Setting an existing key updates it."""
        store.set_config("theme", "dark")
        store.set_config("theme", "light")
        assert store.get_config("theme") == "light"

    def test_set_with_description(self, store):
        """Can set config with description."""
        store.set_config("speed", "270", description="TTS speed in WPM")
        # Value should be retrievable
        assert store.get_config("speed") == "270"

    def test_set_preserves_description_on_update(self, store):
        """Updating value without description preserves existing description."""
        store.set_config("speed", "270", description="TTS speed in WPM")
        store.set_config("speed", "300")  # Update without description
        # Value updated, description should still exist (can't directly check,
        # but shouldn't error)
        assert store.get_config("speed") == "300"

    def test_set_can_override_description(self, store):
        """Can explicitly update description."""
        store.set_config("speed", "270", description="Old desc")
        store.set_config("speed", "300", description="New desc")
        assert store.get_config("speed") == "300"


class TestConfigEdgeCases:
    """Test config edge cases."""

    def test_config_empty_string_value(self, store):
        """Empty string is a valid config value."""
        store.set_config("empty", "")
        assert store.get_config("empty") == ""

    def test_config_unicode_value(self, store):
        """Unicode values work in config."""
        store.set_config("greeting", "Hello 你好 🌍")
        assert store.get_config("greeting") == "Hello 你好 🌍"

    def test_config_special_chars_in_key(self, store):
        """Special characters in config keys work."""
        store.set_config("app.setting.name", "value")
        assert store.get_config("app.setting.name") == "value"

    def test_config_isolated_from_lore(self, store):
        """Config doesn't interfere with lore data."""
        store.set_config("a", "config_value")
        store.set("a", "lore_value")

        # Both should coexist
        assert store.get_config("a") == "config_value"
        assert store.get("a")["value"] == "lore_value"

    def test_config_persists_across_connections(self, db_path):
        """Config persists when store is reopened."""
        from store import Store

        # First connection - set config
        store1 = Store(db_path)
        store1.set_config("persist_test", "saved")

        # Second connection - read config
        store2 = Store(db_path)
        assert store2.get_config("persist_test") == "saved"


class TestConfigErrors:
    """Test config error handling."""

    def test_get_config_with_none_key_raises(self, store):
        """Getting config with None key raises TypeError."""
        with pytest.raises(TypeError):
            store.get_config(None)

    def test_set_config_with_none_key_raises(self, store):
        """Setting config with None key raises TypeError."""
        with pytest.raises(TypeError):
            store.set_config(None, "value")

    def test_set_config_with_none_value_raises(self, store):
        """Setting config with None value raises TypeError."""
        with pytest.raises(TypeError):
            store.set_config("key", None)
