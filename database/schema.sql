CREATE DATABASE IF NOT EXISTS hotel_reservation;

USE hotel_reservation;

CREATE TABLE IF NOT EXISTS hotels (
    hotel_id INT PRIMARY KEY AUTO_INCREMENT,
    hotel_name VARCHAR(100) NOT NULL,
    location VARCHAR(100)
);