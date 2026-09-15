-- Run this once against your MySQL server, or let app.py create it
-- automatically on first run (init_db() does the same thing).

CREATE DATABASE IF NOT EXISTS date_proposal;


USE date_proposal;

CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    response VARCHAR(10) NOT NULL,
    day VARCHAR(20),
    time_slot VARCHAR(50),
    food VARCHAR(50),
    saved_at DATETIME NOT NULL
);

USE defaultdb;
SELECT * from responses;
truncate table responses;