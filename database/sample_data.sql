```sql
-- Hotel Reservation Management System
-- Sample data for testing

USE hotel_reservation;

-- 1. Insert Room Types
INSERT INTO room_types (type_name, description)
VALUES
('Standard', 'Comfortable standard room'),
('Deluxe', 'Spacious room with premium facilities'),
('Suite', 'Luxury room with additional space');

-- 2. Insert Rooms
INSERT INTO rooms
(room_number, type_id, price_per_night, capacity, description)
VALUES
('101', 1, 1500.00, 2, 'Standard room with essential facilities'),
('102', 1, 1500.00, 2, 'Standard room with double bed'),
('201', 2, 2500.00, 3, 'Deluxe room with premium facilities'),
('202', 2, 2500.00, 3, 'Deluxe room with city view'),
('301', 3, 4500.00, 4, 'Luxury suite with spacious interiors');

-- 3. Insert Demo User
INSERT INTO users
(full_name, email, phone, password_hash)
VALUES
(
    'Rahul Sharma',
    'rahul@example.com',
    '9876543210',
    'DEMO_HASH_REPLACE_WITH_REAL_HASH'
);

-- 4. Insert Demo Reservation
INSERT INTO reservations
(user_id, room_id, check_in, check_out, guests, total_amount)
VALUES
(1, 1, '2026-11-10', '2026-11-13', 2, 4500.00);
```
