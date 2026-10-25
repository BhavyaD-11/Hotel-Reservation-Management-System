-- Hotel Reservation Management System
-- Database schema (MySQL 8.0.16+ because of CHECK constraints)
-- WARNING: running this file DROPS and recreates all tables (fresh start).

CREATE DATABASE IF NOT EXISTS hotel_reservation;
USE hotel_reservation;

DROP VIEW  IF EXISTS v_reservation_details;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS room_types;
DROP TABLE IF EXISTS users;

-- 1. Room Types
CREATE TABLE room_types (
    type_id     INT AUTO_INCREMENT PRIMARY KEY,
    type_name   VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 2. Users (guests and admins)
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    phone         VARCHAR(15),
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('guest', 'admin') NOT NULL DEFAULT 'guest',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Rooms
CREATE TABLE rooms (
    room_id         INT AUTO_INCREMENT PRIMARY KEY,
    room_number     VARCHAR(10) NOT NULL UNIQUE,
    type_id         INT NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    capacity        INT NOT NULL DEFAULT 2,
    description     VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE = under maintenance / removed

    FOREIGN KEY (type_id) REFERENCES room_types(type_id),
    CHECK (price_per_night >= 0),
    CHECK (capacity > 0)
);

-- 4. Reservations
CREATE TABLE reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    room_id        INT NOT NULL,
    check_in       DATE NOT NULL,
    check_out      DATE NOT NULL,
    guests         INT NOT NULL DEFAULT 1,
    total_amount   DECIMAL(10,2) NOT NULL,
    booking_status ENUM('Confirmed', 'Checked-In', 'Checked-Out', 'Cancelled')
                   NOT NULL DEFAULT 'Confirmed',
    booked_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    INDEX idx_room_dates (room_id, check_in, check_out),

    CHECK (check_out > check_in),
    CHECK (guests > 0),
    CHECK (total_amount >= 0)
);

-- 5. Payments
CREATE TABLE payments (
    payment_id     INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    amount         DECIMAL(10,2) NOT NULL,
    payment_method ENUM('Cash', 'Card', 'UPI') NOT NULL,
    payment_status ENUM('Pending', 'Paid', 'Failed', 'Refunded')
                   NOT NULL DEFAULT 'Pending',
    payment_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id),
    CHECK (amount >= 0)
);

-- ------------------------------------------------------------------
-- VIEW: one row per reservation with guest, room and payment details
-- ------------------------------------------------------------------
CREATE VIEW v_reservation_details AS
SELECT
    res.reservation_id,
    res.user_id,
    u.full_name  AS guest_name,
    u.email      AS guest_email,
    res.room_id,
    r.room_number,
    rt.type_name,
    res.check_in,
    res.check_out,
    DATEDIFF(res.check_out, res.check_in) AS nights,
    res.guests,
    res.total_amount,
    res.booking_status,
    res.booked_at,
    COALESCE((SELECT p.payment_status FROM payments p
              WHERE p.reservation_id = res.reservation_id
              ORDER BY p.payment_id DESC LIMIT 1), 'Unpaid') AS payment_status
FROM reservations res
JOIN users u       ON u.user_id  = res.user_id
JOIN rooms r       ON r.room_id  = res.room_id
JOIN room_types rt ON rt.type_id = r.type_id;

-- ------------------------------------------------------------------
-- TRIGGER: database-level protection against double booking.
-- Even if the application has a bug, MySQL itself refuses an
-- overlapping booking for the same room.
-- (Run this file using MySQL Workbench or the mysql command line.)
-- ------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_double_booking;

DELIMITER $$
CREATE TRIGGER trg_prevent_double_booking
BEFORE INSERT ON reservations
FOR EACH ROW
BEGIN
    IF NEW.booking_status <> 'Cancelled' AND EXISTS (
        SELECT 1 FROM reservations
        WHERE room_id = NEW.room_id
          AND booking_status IN ('Confirmed', 'Checked-In')
          AND check_in  < NEW.check_out
          AND check_out > NEW.check_in
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Room is already booked for these dates';
    END IF;
END$$
DELIMITER ;
