

CREATE DATABASE IF NOT EXISTS date_proposal;


USE date_proposal;

CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    response VARCHAR(10) NOT NULL,
    day ENUM('Today', 'Tomorrow', 'Some other day'),
    time_slot ENUM('9pm & late night', '5pm - 9pm', '3 - 5 (I am busy)'),
    food VARCHAR(50),
    shared_message TEXT,
    saved_at DATETIME NOT NULL
);

USE defaultdb;
SELECT * from responses;
