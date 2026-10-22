```sql
-- Hotel Reservation Management System
-- Testing and demonstration queries

USE hotel_reservation;

-- 1. Display all room types
SELECT * FROM room_types;

-- 2. Display all users
SELECT user_id, full_name, email, phone
FROM users;

-- 3. Display all rooms
SELECT * FROM rooms;

-- 4. Display all reservations
SELECT * FROM reservations;

-- 5. Display all payments
SELECT * FROM payments;

-- 6. Display all tables in the database
SHOW TABLES;

-- 7. Display rooms with their room types
SELECT
    r.room_id,
    r.room_number,
    rt.type_name,
    r.price_per_night,
    r.capacity
FROM rooms r
JOIN room_types rt
    ON r.type_id = rt.type_id;

-- 8. Display reservations with customer and room details
SELECT
    u.full_name,
    r.room_number,
    res.check_in,
    res.check_out,
    res.total_amount,
    res.booking_status
FROM reservations res
JOIN users u
    ON res.user_id = u.user_id
JOIN rooms r
    ON res.room_id = r.room_id;

-- 9. Display reservations for user ID 1
SELECT *
FROM reservations
WHERE user_id = 1;

-- 10. Display minimum and maximum price for each room type
SELECT
    rt.type_name,
    MIN(r.price_per_night) AS minimum_price,
    MAX(r.price_per_night) AS maximum_price
FROM room_types rt
JOIN rooms r
    ON rt.type_id = r.type_id
GROUP BY rt.type_id, rt.type_name;

-- 11. Check room availability for the selected dates
-- Check-in: 10 November 2026
-- Check-out: 13 November 2026
SELECT
    r.room_id,
    r.room_number,
    rt.type_name,
    r.price_per_night
FROM rooms r
JOIN room_types rt
    ON r.type_id = rt.type_id
WHERE NOT EXISTS (
    SELECT 1
    FROM reservations res
    WHERE res.room_id = r.room_id
      AND res.booking_status = 'Confirmed'
      AND res.check_in < '2026-11-13'
      AND res.check_out > '2026-11-10'
);

-- 12. Calculate total paid revenue
SELECT SUM(amount) AS total_revenue
FROM payments
WHERE payment_status = 'Paid';
```
