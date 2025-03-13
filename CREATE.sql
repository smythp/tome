CREATE TABLE lore (
       id INTEGER PRIMARY KEY,
       data_type VARCHAR,       -- Type of data: "value" for normal values, "buffer" for nested buffers, "list" for lists
       buffer_id INTEGER,       -- ID of the buffer this entry belongs to
       parent_id INTEGER,       -- ID of the parent (buffer or list) this entry belongs to
       item_index INTEGER,      -- For ordering items in a list (renamed from 'index' which is a reserved keyword)
       value VARCHAR,           -- The actual value stored
       label VARCHAR,           -- Optional descriptive label
       key VARCHAR,             -- The keyboard key this value is associated with
       datetime TIMESTAMP       -- When this entry was created
       );

CREATE TABLE config (
       key VARCHAR PRIMARY KEY,
       value VARCHAR,
       description VARCHAR
       );


-- Create the root buffer (ID 1)
INSERT INTO lore (id, data_type, buffer_id, value, label, key, datetime, parent_id) 
VALUES (1, "buffer", 1, 1, "root buffer", null, CURRENT_TIMESTAMP, null);

-- Default configuration settings
INSERT INTO config (key, value, description) VALUES ('debug_mode', 'off', 'Enable/disable debug output');
