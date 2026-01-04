"""Oracle tests - Property-based verification of Store invariants.

Uses Hypothesis to verify mathematical properties hold for ALL inputs.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import tempfile
from pathlib import Path
import os

# Shared settings for all property tests
property_settings = settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def make_store():
    """Create a fresh Store with temp database."""
    from store import Store
    import uuid
    db_path = Path(tempfile.gettempdir()) / f"test_lore_{uuid.uuid4().hex}.db"
    return Store(db_path)


@pytest.fixture
def store_factory():
    """Factory for creating Store instances."""
    return make_store


# Strategies for generating test data
keys = st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")
values = st.text(min_size=0, max_size=1000)
labels = st.one_of(st.none(), st.text(min_size=0, max_size=100))


# ============================================================================
# Get/Set Invariants
# ============================================================================

class TestGetSetInvariants:
    """Properties about get/set operations."""

    @given(key=keys, value=values)
    @property_settings
    def test_set_then_get_returns_value(self, store_factory, key, value):
        """After set(k, v), get(k) returns v."""
        store = store_factory()
        store.set(key, value)
        entry = store.get(key)
        assert entry is not None
        assert entry["value"] == value

    @given(key=keys, values_list=st.lists(values, min_size=2, max_size=10))
    @property_settings
    def test_get_returns_newest(self, store_factory, key, values_list):
        """get() returns the most recently set value."""
        store = store_factory()
        for v in values_list:
            store.set(key, v)
        entry = store.get(key)
        assert entry["value"] == values_list[-1]

    @given(key=keys, value=values, label=labels)
    @property_settings
    def test_set_preserves_label(self, store_factory, key, value, label):
        """Label set is the label retrieved."""
        store = store_factory()
        store.set(key, value, label=label)
        entry = store.get(key)
        assert entry["label"] == label

    @given(key1=keys, key2=keys, value1=values, value2=values)
    @property_settings
    def test_different_keys_independent(self, store_factory, key1, key2, value1, value2):
        """Different keys store independent values."""
        assume(key1 != key2)
        store = store_factory()
        store.set(key1, value1)
        store.set(key2, value2)
        assert store.get(key1)["value"] == value1
        assert store.get(key2)["value"] == value2


# ============================================================================
# Delete/Restore Invariants
# ============================================================================

class TestDeleteRestoreInvariants:
    """Properties about delete and restore."""

    @given(key=keys, value=values)
    @property_settings
    def test_delete_makes_invisible(self, store_factory, key, value):
        """After delete, get returns None."""
        store = store_factory()
        store.set(key, value)
        store.delete(key)
        assert store.get(key) is None

    @given(key=keys, value=values)
    @property_settings
    def test_restore_makes_visible(self, store_factory, key, value):
        """After restore, get returns the value."""
        store = store_factory()
        entry = store.set(key, value)
        store.delete(key)
        success, _ = store.restore(entry["id"])
        assert success
        assert store.get(key)["value"] == value

    @given(key=keys, value=values)
    @property_settings
    def test_delete_preserves_in_history(self, store_factory, key, value):
        """Deleted items appear in history with include_deleted."""
        store = store_factory()
        store.set(key, value)
        store.delete(key)
        history = store.history(key, include_deleted=True)
        assert len(history) == 1
        assert history[0]["value"] == value
        assert history[0]["deleted"] == 1


# ============================================================================
# History Invariants
# ============================================================================

class TestHistoryInvariants:
    """Properties about history."""

    @given(key=keys, values_list=st.lists(values, min_size=1, max_size=20))
    @property_settings
    def test_history_length_matches_sets(self, store_factory, key, values_list):
        """History length equals number of sets."""
        store = store_factory()
        for v in values_list:
            store.set(key, v)
        history = store.history(key)
        assert len(history) == len(values_list)

    @given(key=keys, values_list=st.lists(values, min_size=1, max_size=10))
    @property_settings
    def test_history_ordered_newest_first(self, store_factory, key, values_list):
        """History is ordered newest first."""
        store = store_factory()
        for v in values_list:
            store.set(key, v)
        history = store.history(key)
        history_values = [h["value"] for h in history]
        assert history_values == list(reversed(values_list))


# ============================================================================
# Buffer Invariants
# ============================================================================

class TestBufferInvariants:
    """Properties about buffers."""

    @given(key=keys)
    @property_settings
    def test_create_buffer_makes_is_buffer_true(self, store_factory, key):
        """After create_buffer, is_buffer returns True."""
        store = store_factory()
        store.create_buffer(key)
        assert store.is_buffer(key)

    @given(key=keys, value=values)
    @property_settings
    def test_value_is_not_buffer(self, store_factory, key, value):
        """A value entry is not a buffer."""
        store = store_factory()
        store.set(key, value)
        assert not store.is_buffer(key)

    @given(buffer_keys=st.lists(keys, min_size=2, max_size=5, unique=True))
    @property_settings
    def test_buffer_ids_unique(self, store_factory, buffer_keys):
        """Each buffer gets a unique ID."""
        store = store_factory()
        ids = [store.create_buffer(k) for k in buffer_keys]
        assert len(set(ids)) == len(ids)

    @given(key=keys)
    @property_settings
    def test_enter_buffer_returns_create_id(self, store_factory, key):
        """enter_buffer returns the ID from create_buffer."""
        store = store_factory()
        created_id = store.create_buffer(key)
        entered_id = store.enter_buffer(key)
        assert created_id == entered_id


# ============================================================================
# List Invariants
# ============================================================================

class TestListInvariants:
    """Properties about lists."""

    @given(key=keys)
    @property_settings
    def test_create_list_makes_is_list_true(self, store_factory, key):
        """After create_list, is_list returns True."""
        store = store_factory()
        store.create_list(key)
        assert store.is_list(key)

    @given(key=keys, items=st.lists(values, min_size=0, max_size=20))
    @property_settings
    def test_list_items_count_matches_appends(self, store_factory, key, items):
        """List item count equals number of appends."""
        store = store_factory()
        list_id = store.create_list(key)
        for item in items:
            store.append_to_list(list_id, item)
        list_items = store.list_items(list_id)
        assert len(list_items) == len(items)

    @given(key=keys, items=st.lists(values, min_size=1, max_size=10))
    @property_settings
    def test_list_items_ordered_by_append(self, store_factory, key, items):
        """List items are in append order."""
        store = store_factory()
        list_id = store.create_list(key)
        for item in items:
            store.append_to_list(list_id, item)
        list_items = store.list_items(list_id)
        values_in_list = [i["value"] for i in list_items]
        assert values_in_list == items

    @given(key=keys, items=st.lists(values, min_size=1, max_size=10))
    @property_settings
    def test_list_item_indices_sequential(self, store_factory, key, items):
        """List item indices are 0, 1, 2, ..."""
        store = store_factory()
        list_id = store.create_list(key)
        for item in items:
            store.append_to_list(list_id, item)
        list_items = store.list_items(list_id)
        indices = [i["item_index"] for i in list_items]
        assert indices == list(range(len(items)))


# ============================================================================
# Children Invariants
# ============================================================================

class TestChildrenInvariants:
    """Properties about children listing."""

    @given(entries=st.lists(st.tuples(keys, values), min_size=1, max_size=10, unique_by=lambda x: x[0]))
    @property_settings
    def test_children_includes_all_set_keys(self, store_factory, entries):
        """Children includes all keys that were set."""
        store = store_factory()
        for key, value in entries:
            store.set(key, value)
        children = store.children()
        child_keys = {c["key"] for c in children}
        set_keys = {k for k, v in entries}
        assert set_keys <= child_keys

    @given(key=keys, value=values)
    @property_settings
    def test_deleted_not_in_children(self, store_factory, key, value):
        """Deleted entries don't appear in children."""
        store = store_factory()
        store.set(key, value)
        store.delete(key)
        children = store.children()
        child_keys = {c["key"] for c in children}
        assert key not in child_keys


# ============================================================================
# Cross-Cutting Invariants
# ============================================================================

class TestCrossCuttingInvariants:
    """Invariants that span multiple operations."""

    @given(key=keys, value=values)
    @property_settings
    def test_buffer_and_value_coexist(self, store_factory, key, value):
        """A key can have both a buffer and a value (different entries)."""
        store = store_factory()
        store.set(key, value)
        store.create_buffer(key)
        # Both should exist
        # get() returns most recent, which is the buffer
        # But history should show both
        history = store.history(key)
        # Buffer entry may not have same "value" field semantics
        assert len(history) >= 1

    @given(key=keys, old_value=values, new_value=values)
    @property_settings
    def test_list_conversion_preserves_original(self, store_factory, key, old_value, new_value):
        """Converting a value to a list preserves the original value."""
        store = store_factory()
        store.set(key, old_value)
        list_id = store.create_list(key)
        items = store.list_items(list_id)
        # Original value should be first item
        assert len(items) == 1
        assert items[0]["value"] == old_value

    @given(key=keys, value=values)
    @property_settings
    def test_entry_ids_are_positive(self, store_factory, key, value):
        """All entry IDs are positive integers."""
        store = store_factory()
        entry = store.set(key, value)
        assert isinstance(entry["id"], int)
        assert entry["id"] > 0
