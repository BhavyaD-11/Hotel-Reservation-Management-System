-- Hotel Reservation Management System
-- Demonstration queries for viva / report

USE hotel_reservation;

-- 1. All room types
SELECT * FROM room_types;

-- 2. All users (never show password_hash)
SELECT user_id, full_name, email, phone, role FROM users;

-- 3. Rooms with their room type (INNER JOIN)
SELECT r.room_id, r.room_number, rt.type_name, r.price_per_night, r.capacity
FROM rooms r
JOIN room_types rt ON r.type_id = rt.type_id;

-- 4. Reservations with guest and room details (3-table JOIN)
SELECT u.full_name, r.room_number, res.check_in, res.check_out,
       res.total_amount, res.booking_status
FROM reservations res
JOIN users u ON res.user_id = u.user_id
JOIN rooms r ON res.room_id = r.room_id;

-- 5. Using the VIEW
SELECT * FROM v_reservation_details;

-- 6. Min / max / average price per room type (GROUP BY + aggregates)
SELECT rt.type_name,
       COUNT(r.room_id)       AS total_rooms,
       MIN(r.price_per_night) AS minimum_price,
       MAX(r.price_per_night) AS maximum_price,
       AVG(r.price_per_night) AS average_price
FROM room_types rt
JOIN rooms r ON rt.type_id = r.type_id
GROUP BY rt.type_id, rt.type_name;

-- 7. Rooms AVAILABLE between 10 Nov 2026 and 13 Nov 2026 (NOT EXISTS subquery)
SELECT r.room_id, r.room_number, rt.type_name, r.price_per_night
FROM rooms r
JOIN room_types rt ON r.type_id = rt.type_id
WHERE r.is_active = TRUE
  AND NOT EXISTS (
        SELECT 1 FROM reservations res
        WHERE res.room_id = r.room_id
          AND res.booking_status IN ('Confirmed', 'Checked-In')
          AND res.check_in  < '2026-11-13'
          AND res.check_out > '2026-11-10');

-- 8. Total revenue from paid payments
SELECT SUM(amount) AS total_revenue
FROM payments
WHERE payment_status = 'Paid';

-- 9. Revenue per room type (4-table JOIN + GROUP BY)
SELECT rt.type_name, SUM(p.amount) AS revenue
FROM payments p
JOIN reservations res ON p.reservation_id = res.reservation_id
JOIN rooms r          ON res.room_id = r.room_id
JOIN room_types rt    ON r.type_id = rt.type_id
WHERE p.payment_status = 'Paid'
GROUP BY rt.type_name;

-- 10. Guests who booked more than once (GROUP BY + HAVING)
SELECT u.full_name, COUNT(*) AS bookings
FROM reservations res
JOIN users u ON u.user_id = res.user_id
GROUP BY u.user_id, u.full_name
HAVING COUNT(*) > 1;

-- 11. Rooms that have never been booked (LEFT JOIN + IS NULL)
SELECT r.room_number
FROM rooms r
LEFT JOIN reservations res ON res.room_id = r.room_id
WHERE res.reservation_id IS NULL;

-- 12. Unpaid active reservations (outstanding dues)
SELECT reservation_id, guest_name, total_amount
FROM v_reservation_details
WHERE booking_status IN ('Confirmed', 'Checked-In')
  AND payment_status <> 'Paid';

-- 13. Trigger test: this must FAIL with "Room is already booked for these dates"
-- INSERT INTO reservations (user_id, room_id, check_in, check_out, guests, total_amount)
-- VALUES (2, 1, '2026-11-11', '2026-11-12', 2, 1500);
