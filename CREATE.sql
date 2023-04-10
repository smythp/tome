CREATE TABLE lore (
       id INTEGER PRIMARY KEY,
       data_type VARCHAR,
       register INTEGER,
       value VARCHAR,
       label VARCHAR,
       key VARCHAR,
       datetime TIMESTAMP
       );


INSERT INTO lore (id, data_type, value, label, key, datetime) VALUES (1, "initial register", null, "initial register", null, "");
