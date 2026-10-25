-- Hotel Reservation Management System
-- Sample data. Run AFTER schema.sql.
--
-- Demo logins:
--   Admin : admin@hotel.com   / admin123
--   Guest : rahul@example.com / guest123

USE hotel_reservation;

INSERT INTO room_types (type_name, description) VALUES
('Standard', 'Comfortable standard room'),
('Deluxe',   'Spacious room with premium facilities'),
('Suite',    'Luxury room with additional space');

INSERT INTO rooms (room_number, type_id, price_per_night, capacity, description) VALUES
('101', 1, 1500.00, 2, 'Standard room with essential facilities'),
('102', 1, 1500.00, 2, 'Standard room with double bed'),
('103', 1, 1600.00, 3, 'Standard room with extra bed'),
('201', 2, 2500.00, 3, 'Deluxe room with premium facilities'),
('202', 2, 2500.00, 3, 'Deluxe room with city view'),
('301', 3, 4500.00, 4, 'Luxury suite with spacious interiors'),
('302', 3, 5200.00, 4, 'Presidential suite with private balcony');

INSERT INTO users (full_name, email, phone, password_hash, role) VALUES
('Hotel Admin',  'admin@hotel.com',   '9000000000',
 'pbkdf2:sha256:1000000$CpqPKvQpMhXvRvaW$b3882013e2e430d9c4f955eb4d9864366a126dbfe4df90eb27fcfb4a263bef18', 'admin'),
('Rahul Sharma', 'rahul@example.com', '9876543210',
 'pbkdf2:sha256:1000000$O2W24gb1lfPzCutc$67d43e1ea2be7d83b00fd2c2b14ee7967c88c7a271b753a72b60fe0c15e698f9', 'guest');

-- Demo reservation for Rahul (user_id 2), room 101, 3 nights = 4500
INSERT INTO reservations (user_id, room_id, check_in, check_out, guests, total_amount)
VALUES (2, 1, '2026-11-10', '2026-11-13', 2, 4500.00);

INSERT INTO payments (reservation_id, amount, payment_method, payment_status)
VALUES (1, 4500.00, 'UPI', 'Paid');
