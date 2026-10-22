from flask import Flask, jsonify, request
from db import get_db_connection
from typing import Any, cast

app = Flask(__name__)

hotels = [
    {
        "id": 1,
        "name": "Sunrise Grand Hotel",
        "city": "Hyderabad",
        "price_per_night": 2500,
        "available_rooms": 10
    },
    {
        "id": 2,
        "name": "Royal Comfort Inn",
        "city": "Bengaluru",
        "price_per_night": 1800,
        "available_rooms": 8
    },
    {
        "id": 3,
        "name": "Ocean View Resort",
        "city": "Goa",
        "price_per_night": 4000,
        "available_rooms": 5
    }
]

@app.route("/")
def home():
    return jsonify({
        "message": "Hotel Reservation Backend is Running!"
    })

@app.route("/api/hotels", methods=["GET"])
def get_hotels():
    city = request.args.get("city", "").strip()

    if city:
        results = [
            hotel for hotel in hotels
            if hotel["city"].lower() == city.lower()
        ]
    else:
        results = hotels

    return jsonify(results)

@app.route("/api/hotels/<int:hotel_id>", methods=["GET"])
def get_hotel(hotel_id):
    for hotel in hotels:
        if hotel["id"] == hotel_id:
            return jsonify(hotel)

    return jsonify({"error": "Hotel not found"}), 404
# Temporary reservation storage


@app.route("/api/reservations", methods=["POST"])
def create_reservation():
    from datetime import date

    data = request.get_json(silent=True) or {}

    required_fields = [
        "guest_name",
        "hotel_id",
        "check_in",
        "check_out",
        "guests"
    ]

    missing = [field for field in required_fields if field not in data]

    if missing:
        return jsonify({"error": "Missing fields", "fields": missing}), 400

    try:
        guest_name = data["guest_name"].strip()
        room_id = int(data["hotel_id"])
        check_in = date.fromisoformat(data["check_in"])
        check_out = date.fromisoformat(data["check_out"])
        guests = int(data["guests"])

        if not guest_name or check_in < date.today() or check_out <= check_in or guests < 1:
            return jsonify({"error": "Invalid booking details"}), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT user_id FROM users WHERE full_name = %s LIMIT 1",
            (guest_name,)
        )
        user = cast(dict[str, Any] | None, cursor.fetchone())

        if not user:
            cursor.close()
            connection.close()
            return jsonify({"error": "Guest not found in users table"}), 404

        cursor.execute(
            "SELECT room_id, price_per_night, capacity FROM rooms WHERE room_id = %s",
            (room_id,)
        )
        room = cast(dict[str, Any] | None, cursor.fetchone())

        if not room:
            cursor.close()
            connection.close()
            return jsonify({"error": "Room not found"}), 404

        if guests > room["capacity"]:
            cursor.close()
            connection.close()
            return jsonify({"error": "Guest count exceeds room capacity"}), 400

        nights = (check_out - check_in).days
        total_price = nights * float(room["price_per_night"])

        cursor.execute(
            """
            INSERT INTO reservations
            (user_id, room_id, check_in, check_out, guests,
             total_amount, booking_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Confirmed')
            """,
            (user["user_id"], room_id, check_in, check_out,
             guests, total_price)
        )

        reservation_id = cursor.lastrowid
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "reservation_id": reservation_id,
            "guest_name": guest_name,
            "room_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": guests,
            "total_price": round(total_price, 2),
            "status": "Confirmed"
        }), 201

    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "Invalid booking details"}), 400

    except Exception:
        app.logger.exception("Reservation database operation failed")
        return jsonify({"error": "Database operation failed"}), 500

@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    from datetime import date

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.reservation_id,
                u.full_name AS guest_name,
                r.room_id,
                r.check_in,
                r.check_out,
                r.guests,
                r.total_amount,
                r.booking_status
            FROM reservations r
            JOIN users u ON r.user_id = u.user_id
            ORDER BY r.reservation_id DESC
        """)

        reservations = cursor.fetchall()

        reservations = [
            {
                **cast(dict[str, Any], reservation),
                "check_in": cast(date, cast(dict[str, Any], reservation)["check_in"]).isoformat(),
                "check_out": cast(date, cast(dict[str, Any], reservation)["check_out"]).isoformat(),
                "total_amount": float(cast(dict[str, Any], reservation)["total_amount"]),
            }
            for reservation in reservations
        ]

        return jsonify(reservations)

    except Exception:
        app.logger.exception("Could not retrieve reservations")
        return jsonify({"error": "Database operation failed"}), 500

    finally:
        cursor.close()
        connection.close()
if __name__ == "__main__":
    app.run(debug=True)