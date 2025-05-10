# Register Deletion Implementation Plan for Tome of Lore

## Overview

This document outlines the implementation plan for adding deletion functionality to the Tome of Lore application. The functionality will allow users to delete registers (regular values, lists, or buffers) while preserving historical data by marking items as deleted rather than removing them completely.

## Requirements

1. Regular values and lists can be deleted instantly upon pressing Delete key
2. Buffers require y/n confirmation before deletion
3. In list mode, individual list items can be deleted
4. Deleted items should still appear in history with indication they've been deleted
5. Deleted items can be restored through the history interface
6. All interaction must be voice-based, consistent with the app's audio-only interface

## Database Changes

The first step is to modify the database schema to support the "soft delete" functionality:

```sql
-- Add deleted column to the lore table with default value of 0 (false)
ALTER TABLE lore ADD COLUMN deleted BOOLEAN DEFAULT 0;
```

## Implementation Steps

### 1. Core Functionality

#### Soft Delete Function
Update the existing delete_entry function to mark items as deleted rather than removing them:

```python
def soft_delete_entry(entry_id):
    """Mark an entry as deleted without removing it from the database."""
    connection, cursor = connect()
    
    cursor.execute('UPDATE lore SET deleted = 1 WHERE id = ?;', (entry_id,))
    connection.commit()
    
    return cursor.rowcount > 0  # Return True if at least one row was updated
```

#### Modify Retrieve Function
Update the retrieve function to filter out deleted items by default:

```python
def retrieve(key, buffer_id=None, fetch='last', parent_id=None, include_deleted=False):
    # Existing code...
    
    # Add WHERE clause to filter out deleted items unless specifically requested
    if not include_deleted:
        query = query[:-1] + " AND deleted = 0"
    
    # Existing code...
```

#### Restore Function
Add a function to restore deleted items:

```python
def restore_entry(entry_id):
    """Restore a deleted entry by marking it as not deleted."""
    connection, cursor = connect()
    
    # Check if the key/buffer combination is occupied
    # Query to get entry details
    cursor.execute('SELECT key, buffer_id FROM lore WHERE id = ?;', (entry_id,))
    entry = cursor.fetchone()
    
    if entry:
        # Check if there's a non-deleted entry with the same key and buffer
        cursor.execute(
            'SELECT id FROM lore WHERE key = ? AND buffer_id = ? AND deleted = 0 LIMIT 1;', 
            (entry['key'], entry['buffer_id'])
        )
        conflict = cursor.fetchone()
        
        if conflict:
            return False, "Cannot restore, register is already occupied"
        
        # Restore the entry
        cursor.execute('UPDATE lore SET deleted = 0 WHERE id = ?;', (entry_id,))
        connection.commit()
        
        return True, "Entry restored"
    
    return False, "Entry not found"
```

#### Recursive Buffer Deletion
Add a function to recursively delete a buffer and its contents:

```python
def delete_buffer_recursively(buffer_id):
    """Recursively mark a buffer and all its contents as deleted."""
    if buffer_id == 1:  # Prevent deletion of root buffer
        return False, "Cannot delete root buffer"
        
    connection, cursor = connect()
    
    # Mark the buffer entry itself as deleted
    cursor.execute(
        'UPDATE lore SET deleted = 1 WHERE value = ? AND data_type = "buffer";', 
        (buffer_id,)
    )
    
    # Mark all entries in this buffer as deleted
    cursor.execute('UPDATE lore SET deleted = 1 WHERE buffer_id = ?;', (buffer_id,))
    
    # Find all sub-buffers
    cursor.execute(
        'SELECT value FROM lore WHERE buffer_id = ? AND data_type = "buffer";', 
        (buffer_id,)
    )
    sub_buffers = cursor.fetchall()
    
    # Recursively delete sub-buffers
    for sub_buffer in sub_buffers:
        delete_buffer_recursively(sub_buffer['value'])
    
    connection.commit()
    return True, f"Buffer {buffer_id} and its contents deleted"
```

### 2. User Interface Updates

#### Regular Register Deletion
Update the read mode handler to support the Delete key:

```python
# In read() function
if key == keyboard.Key.delete:
    if last_retrieved['key'] is not None:
        # Get the entry to delete
        result = retrieve(last_retrieved['key'], buffer_id=last_retrieved['buffer_id'])
        if result:
            # Delete the entry
            success = soft_delete_entry(result['id'])
            if success:
                speak(f"Deleted register {last_retrieved['key']}")
                # Reset last retrieved
                last_retrieved = {'value': None, 'key': None, 'buffer_id': None}
            else:
                speak("Failed to delete register")
        else:
            speak(f"No data at key {last_retrieved['key']}")
    else:
        speak("No register selected")
    return
```

#### Buffer Deletion with Confirmation
Create a new confirmation mode for buffer deletion:

```python
# Add a new mode to the mode_map
mode_map["confirm_delete"] = {
    "function": confirm_delete,
    "message": "Delete buffer? Press y to confirm, n to cancel",
}

# Add pending operation state
pending_operation = {
    'type': None,  # 'delete_buffer', etc.
    'params': {}   # Parameters for the operation
}

def confirm_delete(key):
    """Handle confirmation for deletion operations."""
    global mode
    global pending_operation
    
    try:
        if key.char.lower() == 'y':
            # Confirm deletion
            if pending_operation['type'] == 'delete_buffer':
                buffer_id = pending_operation['params']['buffer_id']
                buffer_name = pending_operation['params']['buffer_name']
                
                success, message = delete_buffer_recursively(buffer_id)
                if success:
                    speak(f"Deleted buffer {buffer_name}")
                    # Exit to parent buffer
                    exit_buffer()
                else:
                    speak(message)
            
            # Reset pending operation
            pending_operation = {'type': None, 'params': {}}
            # Return to read mode
            return_to_read_mode()
            
        elif key.char.lower() == 'n':
            # Cancel deletion
            speak("Deletion cancelled")
            # Reset pending operation
            pending_operation = {'type': None, 'params': {}}
            # Return to previous mode
            return_to_read_mode()
            
    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.esc:
            # Cancel on escape
            speak("Deletion cancelled")
            pending_operation = {'type': None, 'params': {}}
            return_to_read_mode()
```

Update the key_handler function to handle Delete key in read mode when in a non-root buffer:

```python
# In key_handler function
if key == keyboard.Key.delete and mode == "read" and current_buffer_id != 1:
    # Set up pending buffer deletion
    pending_operation['type'] = 'delete_buffer'
    pending_operation['params'] = {
        'buffer_id': current_buffer_id,
        'buffer_name': get_buffer_name()
    }
    # Enter confirmation mode
    change_mode('confirm_delete')
    speak(f"Delete buffer {get_buffer_name()}? Press y to confirm, n to cancel")
    return
```

#### List Item Deletion
Update the list_mode function to handle Delete key:

```python
# In list_mode function
if key == keyboard.Key.delete:
    if list_state['items'] and list_state['current_index'] < len(list_state['items']):
        # Get the current item
        current_item = list_state['items'][list_state['current_index']]
        item_id = current_item['id']
        
        # Get user-facing index for feedback
        user_idx = user_index(list_state['current_index'], list_state['items'])
        
        # Delete the item
        success = soft_delete_entry(item_id)
        if success:
            speak(f"Deleted item {user_idx}")
            
            # Remove from the items list
            list_state['items'].pop(list_state['current_index'])
            
            # Handle index adjustment
            if list_state['current_index'] >= len(list_state['items']) and list_state['items']:
                list_state['current_index'] = len(list_state['items']) - 1
                
            # Announce current position if items remain
            if list_state['items']:
                current_item = list_state['items'][list_state['current_index']]
                user_idx = user_index(list_state['current_index'], list_state['items'])
                speak(f"Now at item {user_idx} of {len(list_state['items'])}: {current_item['value']}")
            else:
                speak("List is now empty")
        else:
            speak("Failed to delete item")
    else:
        speak("No item to delete")
    return True
```

### 3. History Integration

Update the history function to indicate deleted items and support restoration:

```python
# In history mode
# Add Control-r for restoring entries
if pressed['ctrl'] and key.char == 'r' and history_state['entries']:
    current_entry = history_state['entries'][history_state['current_index']]
    
    # Check if the entry is deleted
    if current_entry.get('deleted', 0) == 1:
        # Try to restore
        success, message = restore_entry(current_entry['id'])
        speak(message)
        
        if success:
            # Update the entry in the history list
            history_state['entries'][history_state['current_index']]['deleted'] = 0
    else:
        speak("Entry is not deleted")
    return
```

Update the navigate_history function to indicate deleted items:

```python
# In navigate_history function
current_entry = entries[current_index]
total_entries = len(entries)

# Check if entry is deleted
deleted_prefix = "Deleted: " if current_entry.get('deleted', 0) == 1 else ""

if global_mode:
    speak(f"Entry {current_index + 1} of {total_entries}")
    format_global_history_entry(current_entry, deleted_prefix)
else:
    # Speak entry information with deleted status if applicable
    speak(f"Entry {current_index + 1} of {total_entries}: {deleted_prefix}{current_entry['value']}")
```

## Testing Plan

1. Test deletion of regular values
   - Create a value at key 'a', then delete it
   - Verify it disappears from normal access but appears in history as deleted

2. Test buffer deletion with confirmation
   - Create a buffer, navigate to it, attempt to delete it
   - Test both confirming and cancelling deletion
   - Verify buffer and contents are properly marked as deleted

3. Test list item deletion
   - Create a list with multiple items
   - Delete items from different positions (beginning, middle, end)
   - Verify proper reindexing and continued list functionality

4. Test restoration
   - Delete various types of entries
   - Access history and attempt to restore them
   - Test restoration conflict handling

## Conclusion

This implementation plan provides a comprehensive approach to adding deletion functionality to Tome of Lore while preserving historical data and maintaining the application's audio-only interface. The plan breaks down the work into manageable components and addresses all the specified requirements.