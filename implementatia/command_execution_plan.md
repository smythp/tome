# Command Execution Implementation Plan for Tome

## Overview

This document outlines the implementation plan for adding shell command execution functionality to Tome. The feature will allow users to store shell commands in registers and execute them directly from Tome.

## Core Functionality

1. Detect content type as "command" when appropriate
2. Add a config option to enable/disable command execution (default: disabled)
3. Execute commands directly when double-pressing a register key
4. Store, speak, and copy command output
5. Access previous command output with a dedicated hotkey

## User Experience Workflow

### Setup
1. User enables command execution via options menu
2. User stores a shell command in a register (e.g., using Ctrl+y)

### Execution
1. User presses the register key once to hear the command
2. User presses the same key again to execute the command
3. Tome executes the command and:
   - Reads the output aloud
   - Copies the output to the clipboard
   - Stores the output internally for later access

### Accessing Output
1. User presses the backtick (`) key to hear the last command output
2. User can press backtick twice to copy the output to clipboard again

## Technical Implementation Details

### Command Detection
```python
def detect_content_type(value):
    """Detect the type of content in a string."""
    if is_valid_url(value) or is_valid_domain(value):
        return "url"
    elif os.path.exists(value):
        return "file"
    # Basic command detection - can be enhanced
    elif (re.match(r'^[^/]*\s*\|', value) or  # Pipe pattern
          value.startswith('!') or            # Bang pattern
          ' && ' in value or                  # Command chains
          ';' in value):                      # Command separator
        return "command"
    else:
        return "text"
```

### Configuration
```python
# In start() function
if get_config('enable_commands') is None:
    set_config('enable_commands', 'off', 'Enable/disable shell command execution')
```

### Options Menu Addition
```python
# Add to options function
elif key.char == "x":
    # Toggle command execution
    current = get_config('enable_commands', 'off')
    new_value = 'on' if current == 'off' else 'off'
    set_config('enable_commands', new_value)
    speak(f"Command execution {status(new_value == 'on')}")
```

### Command Execution
```python
# In the read function's double-press handler
elif content_type == "command":
    # Get command execution setting
    enabled = get_config('enable_commands', 'off') == 'on'
    
    if not enabled:
        speak("Command execution is disabled. Enable in options menu.")
        # Fall back to copying
        copy(value)
        speak(f"Copied to clipboard")
        exit()
    
    # Strip leading '!' if present
    cmd = value
    if cmd.startswith('!'):
        cmd = cmd[1:].strip()
    
    try:
        # Execute the command
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Store output for later access
        output = result.stdout.strip()
        if result.returncode != 0:
            output = f"Command failed with error: {result.stderr.strip()}"
        
        # Store output (limited to 100,000 characters)
        if len(output) > 100000:
            output = output[:100000] + "\n\n[Output truncated due to size]"
        
        # Store the output in internal state
        global last_command_output
        last_command_output = output
        
        # Speak result summary
        if result.returncode == 0:
            speak("Command executed successfully")
        else:
            speak("Command failed")
        
        # Copy output to clipboard
        copy(output)
        
        exit()
    except Exception as e:
        speak(f"Error executing command")
        exit()
```

### Output Access Hotkey
```python
# In key_handler function
if key == keyboard.Key.grave_accent:  # Backtick key
    if last_command_output:
        if key_presses.get('backtick', 0) == 0:
            # First press - read it out loud
            speak(last_command_output[:1000])  # Limit what's spoken to avoid very long speech
            key_presses['backtick'] = 1
        else:
            # Second press - copy to clipboard
            copy(last_command_output)
            speak("Command output copied to clipboard")
            exit()
    else:
        speak("No command output available")
    return
```

## Design Decisions

1. **Simplicity over complexity**: No extensive safety checks since this is a local tool for power users
2. **Consistent interaction model**: Using the same double-press pattern as other features
3. **Output handling**: 
   - High character limit (100,000) to accommodate most command outputs
   - Single storage location to avoid complexity
   - Only storing the most recent output
4. **Dedicated hotkey**: Backtick (`) chosen due to its association with command-line interfaces

## Future Considerations

1. Option to store outputs in regular registers
2. Enhanced command detection
3. Command history buffer for multiple past outputs
4. Integration with file opener functionality for opening command results