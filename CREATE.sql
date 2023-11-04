CREATE TABLE lore (
       id INTEGER PRIMARY KEY,
       data_type VARCHAR,
       register INTEGER,
       value VARCHAR,
       label VARCHAR,
       key VARCHAR,
       previous_register INTEGER,
       datetime TIMESTAMP
       );


INSERT INTO lore (id, previous_register, data_type, value, label, key, datetime) VALUES (1, 0, "initial register", null, "initial register", null, "");
