def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_global_history(connection, cursor, limit=None):
    """
    Retrieve all entries from the database, sorted by datetime (newest first).
    
    Args:
        connection: SQLite connection object
        cursor: SQLite cursor object
        limit: Optional limit on number of entries to return
        
    Returns:
        List of entries sorted by datetime (newest first)
    """
    # Exclude the root buffer record itself (id=1) as it's not a real entry
    query = "SELECT * FROM lore WHERE id != 1 ORDER BY datetime DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    query += ";"
    
    results = cursor.execute(query)
    if not results:
        return []
    
    return results.fetchall()


class TestHarness:
    """Test harness for simulating keyboard input in Tome of Lore.
    
    This class provides utilities to create mock keyboard events and test
    the application's response without requiring actual keyboard input.
    """
    
    def __init__(self, tome_module=None):
        """Initialize the test harness.
        
        Args:
            tome_module: The tome module to test. If None, it will be imported.
        """
        if tome_module is None:
            import tome
            self.tome = tome
        else:
            self.tome = tome_module
            
        # Save initial state
        self.initial_state = {
            'mode': self.tome.mode,
            'current_buffer_id': self.tome.current_buffer_id,
            'buffer_stack': self.tome.buffer_stack.copy(),
            'buffer_path': self.tome.buffer_path.copy(),
            'pressed': self.tome.pressed.copy(),
        }
        
        # Create a record of all speech output
        self.spoken_text = []
        
        # Patch the speak function to capture output
        self._original_speak = self.tome.speak
        self.tome.speak = self._capture_speech
        
    def _capture_speech(self, text, speed=270, asynchronous=True):
        """Capture speech output without actually speaking."""
        self.spoken_text.append(text)
        print(f"Speech: {text}")  # Print for immediate feedback
        
    def restore_speak(self):
        """Restore the original speak function."""
        self.tome.speak = self._original_speak
    
    def create_char_key(self, char):
        """Create a mock key with a character.
        
        Args:
            char: The character for the key (e.g., 'a', '1', etc.)
            
        Returns:
            A mock key object with a char attribute.
        """
        class MockKeyCode:
            def __init__(self, char_value):
                self.char = char_value
                
        return MockKeyCode(char)
    
    def create_special_key(self, key_name):
        """Create a mock special key.
        
        Args:
            key_name: Name of the key (e.g., 'esc', 'backspace', etc.)
            
        Returns:
            A mock key object that mimics a special key.
        """
        # Check if it's a valid key name
        if not hasattr(self.tome.keyboard.Key, key_name):
            valid_keys = [attr for attr in dir(self.tome.keyboard.Key) 
                        if not attr.startswith('_')]
            raise ValueError(f"Invalid key name: {key_name}. Valid keys: {', '.join(valid_keys)}")
            
        # Return the actual key object from pynput
        return getattr(self.tome.keyboard.Key, key_name)
    
    def press_key(self, key):
        """Simulate pressing a key.
        
        Args:
            key: Either a character string for regular keys or a key name 
                 for special keys.
                
        Returns:
            The result of the key_handler function.
        """
        # Clear speech record for this key press
        self.spoken_text = []
        
        # Create the appropriate key object
        if isinstance(key, str) and len(key) == 1:
            # It's a regular character key
            key_obj = self.create_char_key(key)
        else:
            # It's a special key
            key_obj = self.create_special_key(key)
            
        # Call the key handler
        return self.tome.key_handler(key_obj)
    
    def press_keys(self, keys):
        """Press a sequence of keys.
        
        Args:
            keys: List of keys to press in sequence.
            
        Returns:
            List of speech outputs for each key press.
        """
        results = []
        for key in keys:
            self.press_key(key)
            results.append(self.spoken_text.copy())
        return results
    
    def hold_modifier(self, modifier, pressed=True):
        """Simulate holding or releasing a modifier key.
        
        Args:
            modifier: The modifier key ('shift', 'ctrl', or 'alt').
            pressed: True to press, False to release.
        """
        if modifier not in ('shift', 'ctrl', 'alt'):
            raise ValueError("Modifier must be 'shift', 'ctrl', or 'alt'")
            
        self.tome.pressed[modifier] = pressed
        
    def reset_state(self):
        """Reset the application state to the initial values."""
        self.tome.mode = self.initial_state['mode']
        self.tome.current_buffer_id = self.initial_state['current_buffer_id']
        self.tome.buffer_stack = self.initial_state['buffer_stack'].copy()
        self.tome.buffer_path = self.initial_state['buffer_path'].copy()
        self.tome.pressed = self.initial_state['pressed'].copy()
        self.spoken_text = []
        
    def get_last_speech(self):
        """Get the last speech output."""
        return self.spoken_text[-1] if self.spoken_text else None
        
    def __del__(self):
        """Restore the original speak function when the harness is destroyed."""
        try:
            self.restore_speak()
        except:
            pass
