```sql
-- Hotel Reservation Management System
-- Database and table creation

CREATE DATABASE IF NOT EXISTS hotel_reservation;
USE hotel_reservation;

-- 1. Room Types Table
CREATE TABLE IF NOT EXISTS room_types (
    type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Rooms Table
CREATE TABLE IF NOT EXISTS rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    type_id INT NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    capacity INT NOT NULL DEFAULT 2,
    description VARCHAR(255),

    FOREIGN KEY (type_id)
        REFERENCES room_types(type_id),

    CHECK (price_per_night >= 0),
    CHECK (capacity > 0)
);

-- 4. Reservations Table
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guests INT NOT NULL DEFAULT 1,
    total_amount DECIMAL(10,2) NOT NULL,

    booking_status ENUM('Confirmed', 'Cancelled')
        NOT NULL DEFAULT 'Confirmed',

    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id),

    CHECK (check_out > check_in),
    CHECK (guests > 0),
    CHECK (total_amount >= 0)
);

-- 5. Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,

    payment_method ENUM('Cash', 'Card', 'UPI')
        NOT NULL,

    payment_status ENUM('Pending', 'Paid', 'Failed', 'Refunded')
        NOT NULL DEFAULT 'Pending',

    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id),

    CHECK (amount >= 0)
);
```
