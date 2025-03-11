CREATE TABLE lore (
       id INTEGER PRIMARY KEY,
       data_type VARCHAR,
       register INTEGER,
       parent_register INTEGER,
       value VARCHAR,
       label VARCHAR,
       key VARCHAR,
       datetime TIMESTAMP
       );


INSERT INTO lore (id, data_type, register, value, label, key, datetime, parent_register) VALUES (1, "register", 1, 1, "initial register", null, CURRENT_TIMESTAMP, null);
