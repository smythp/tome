# Buffer Overview Implementation Plan

## Overview
This plan details the implementation of a buffer overview feature for Tome of Lore. Users will be able to press Control+i to get an overview of all items stored in the current buffer, and then navigate through those items one by one.

## Features
1. Buffer contents categorized by type (buffers, URLs, lists, text)
2. Initial overview with truncated content
3. Navigation through individual items with full content display
4. Escape key to return to read mode

## Implementation Steps

### 1. Add Buffer Overview State
Create a global state object to track the overview mode:

```python
# Overview mode state
overview_state = {
    'active': False,       # Whether overview mode is active
    'items': [],           # Flattened list of all items
    'current_index': 0,    # Current position in overview
    'buffer_id': None      # Buffer being viewed
}
```

### 2. Implement Content Categorization Function

```python
def get_buffer_contents_categorized(buffer_id=None):
    """Get all contents of a buffer, categorized by type in fixed order.
    
    Args:
        buffer_id: The buffer ID to get contents from (uses current_buffer_id if None)
        
    Returns:
        List of categorized items with type information
    """
    global current_buffer_id
    
    if buffer_id is None:
        buffer_id = current_buffer_id
        
    connection, cursor = connect()
    
    # Get all entries in this buffer
    cursor.execute('SELECT * FROM lore WHERE buffer_id = ? ORDER BY key;', (buffer_id,))
    entries = cursor.fetchall()
    
    # Categorize entries by type
    sub_buffers = []
    urls = []
    lists = []
    texts = []
    
    for entry in entries:
        key = entry['key']
        value = entry['value']
        data_type = entry['data_type']
        
        item = {
            'key': key,
            'value': value,
            'data_type': data_type,
            'entry': entry  # Store the full entry for reference
        }
        
        if data_type == TYPE_BUFFER:
            sub_buffers.append(item)
        elif data_type == TYPE_LIST:
            lists.append(item)
        elif is_valid_url(value) or is_valid_domain(value):
            urls.append(item)
        else:
            texts.append(item)
    
    # Return a flattened list in the desired order, with category markers
    result = []
    
    # Add sub-buffers first
    if sub_buffers:
        for item in sub_buffers:
            item['category'] = 'buffer'
            result.append(item)
    
    # Add URLs next
    if urls:
        for item in urls:
            item['category'] = 'url'
            result.append(item)
    
    # Add lists next
    if lists:
        for item in lists:
            item['category'] = 'list'
            result.append(item)
    
    # Add text items last
    if texts:
        for item in texts:
            item['category'] = 'text'
            result.append(item)
    
    return result
```

### 3. Implement Buffer Overview Function

```python
def buffer_overview():
    """Provide an overview of the current buffer's contents and enter overview navigation mode."""
    global overview_state
    global current_buffer_id
    
    buffer_id = current_buffer_id
    buffer_name = get_buffer_name() or "root"
    
    # Get categorized contents
    items = get_buffer_contents_categorized(buffer_id)
    
    # Update overview state
    overview_state['active'] = True
    overview_state['items'] = items
    overview_state['current_index'] = 0
    overview_state['buffer_id'] = buffer_id
    
    if not items:
        speak(f"Buffer {buffer_name} is empty")
        overview_state['active'] = False
        return
    
    # Count items by category
    buffers = sum(1 for item in items if item['category'] == 'buffer')
    urls = sum(1 for item in items if item['category'] == 'url')
    lists = sum(1 for item in items if item['category'] == 'list')
    texts = sum(1 for item in items if item['category'] == 'text')
    
    # Announce the buffer overview
    speak(f"Buffer {buffer_name} contains {len(items)} items")
    
    # Create category summaries, skipping empty categories
    summaries = []
    if buffers > 0:
        summaries.append(f"{buffers} buffer{'s' if buffers != 1 else ''}")
    if urls > 0:
        summaries.append(f"{urls} URL{'s' if urls != 1 else ''}")
    if lists > 0:
        summaries.append(f"{lists} list{'s' if lists != 1 else ''}")
    if texts > 0:
        summaries.append(f"{texts} text item{'s' if texts != 1 else ''}")
    
    # Join the summaries with commas and "and"
    if len(summaries) > 1:
        last = summaries.pop()
        overview = ", ".join(summaries) + " and " + last
    else:
        overview = summaries[0]
    
    speak(f"Contains {overview}")
    
    # Announce items by category with truncated content
    current_category = None
    
    for i, item in enumerate(items):
        category = item['category']
        key = item['key']
        value = item['value']
        
        # Announce category change
        if category != current_category:
            current_category = category
            if category == 'buffer':
                speak("Buffers:")
            elif category == 'url':
                speak("URLs:")
            elif category == 'list':
                speak("Lists:")
            elif category == 'text':
                speak("Text items:")
        
        # Format the item announcement based on category
        if category == 'buffer':
            speak(f"Key {key}: contains a buffer")
        elif category == 'url':
            # Extract domain for URLs
            domain = extract_domain(value)
            speak(f"Key {key}: {domain}")
        elif category == 'list':
            # Get list item count
            list_items = get_list_items(item['entry']['id'])
            count = len(list_items) if list_items else 0
            speak(f"Key {key}: list with {count} items")
        elif category == 'text':
            # Truncate text
            if len(value) > 80:
                truncated = value[:80] + "..."
            else:
                truncated = value
            speak(f"Key {key}: {truncated}")
    
    # After overview, speak navigation help
    speak("Use up/down arrows or Control+n/p to navigate items")
```

### 4. Add Domain Extraction Helper

```python
def extract_domain(url):
    """Extract just the domain from a URL."""
    if not url:
        return ""
        
    # Add protocol if missing for proper parsing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except:
        # Fallback to regex if parsing fails
        import re
        match = re.search(r'(?:https?:\/\/)?([^\/]+)', url)
        if match:
            return match.group(1)
        return url
```

### 5. Implement Navigation Function

```python
def navigate_overview(direction):
    """Navigate through overview items.
    
    Args:
        direction: 'next' or 'prev' to indicate direction
        
    Returns:
        True if navigation was successful, False otherwise
    """
    global overview_state
    
    if not overview_state['active'] or not overview_state['items']:
        speak("No overview active or buffer is empty")
        return False
    
    items = overview_state['items']
    current_index = overview_state['current_index']
    
    if direction == 'next' and current_index < len(items) - 1:
        # Move to next item
        overview_state['current_index'] += 1
    elif direction == 'prev' and current_index > 0:
        # Move to previous item
        overview_state['current_index'] -= 1
    else:
        # Cannot navigate further
        if direction == 'next':
            speak("End of items")
        else:
            speak("Beginning of items")
        return False
    
    # Announce the current item with full details
    announce_current_overview_item()
    return True
```

### 6. Implement Current Item Announcement

```python
def announce_current_overview_item():
    """Announce the current item in the overview."""
    global overview_state
    
    if not overview_state['active'] or not overview_state['items']:
        return
    
    items = overview_state['items']
    current_index = overview_state['current_index']
    
    if current_index < 0 or current_index >= len(items):
        return
    
    item = items[current_index]
    category = item['category']
    key = item['key']
    value = item['value']
    
    # Format announcement based on category (with FULL content)
    position = f"Item {current_index + 1} of {len(items)}"
    
    if category == 'buffer':
        speak(f"{position}: Key {key} contains a buffer")
    elif category == 'url':
        speak(f"{position}: Key {key} contains URL: {value}")
    elif category == 'list':
        # Get list item count
        list_items = get_list_items(item['entry']['id'])
        count = len(list_items) if list_items else 0
        speak(f"{position}: Key {key} contains a list with {count} items")
    elif category == 'text':
        speak(f"{position}: Key {key} contains: {value}")
```

### 7. Add Control Key Handler for Buffer Overview

Add the buffer overview function to the read mode key handler:

```python
# In the read function, add to the control key section:
if pressed['ctrl']:
    # Control-i: show buffer overview
    if key.char == 'i':
        buffer_overview()
        return
```

### 8. Add Overview Mode to Key Handler

Modify the key_handler function to handle navigation in overview mode:

```python
# Add to key_handler at the beginning:
# Check if we're in overview mode
if overview_state['active']:
    try:
        # Handle character keys
        if hasattr(key, 'char'):
            # Control+n: next item
            if key.char == 'n' and pressed['ctrl']:
                navigate_overview('next')
                return
            # Control+p: previous item
            elif key.char == 'p' and pressed['ctrl']:
                navigate_overview('prev')
                return
    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.up:
            navigate_overview('prev')
            return
        elif key == keyboard.Key.down:
            navigate_overview('next')
            return
        elif key == keyboard.Key.esc:
            # Exit overview mode
            overview_state['active'] = False
            return_to_read_mode()
            return
```

## Testing Plan

1. Test buffer overview with:
   - Empty buffer
   - Buffer with only one category of items
   - Buffer with mixed categories
   - Items with very long values

2. Test navigation:
   - Moving up/down through items
   - Boundary conditions (first and last item)
   - Different input methods (arrows and Control+n/p)
   - Escaping back to read mode

3. Test domain extraction with:
   - URLs with protocols (http, https)
   - URLs without protocols
   - URLs with subpaths
   - Invalid URLs

## Expected User Experience

1. User navigates to a buffer
2. User presses Control+i to get an overview of contents
3. System announces categories and counts
4. System lists all items with truncated information
5. User can navigate through items with full content using up/down arrows
6. User presses Escape to return to read mode