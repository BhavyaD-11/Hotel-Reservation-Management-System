from flask import Flask, jsonify, request

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
reservations = []
next_reservation_id = 1

@app.route("/api/reservations", methods=["POST"])
def create_reservation():
    global next_reservation_id

    data = request.get_json(silent=True) or {}

    required_fields = [
        "guest_name",
        "hotel_id",
        "check_in",
        "check_out",
        "guests"
    ]

    missing = [
        field for field in required_fields
        if field not in data
    ]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing
        }), 400

    hotel = next(
        (h for h in hotels if h["id"] == data["hotel_id"]),
        None
    )

    if hotel is None:
        return jsonify({"error": "Hotel not found"}), 404

    try:
        from datetime import date

        check_in = date.fromisoformat(data["check_in"])
        check_out = date.fromisoformat(data["check_out"])
        guests = int(data["guests"])

        if check_in < date.today():
            return jsonify({"error": "Check-in cannot be in the past"}), 400

        if check_out <= check_in:
            return jsonify({"error": "Check-out must be after check-in"}), 400

        if guests < 1:
            return jsonify({"error": "Guests must be at least 1"}), 400

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid dates or guest count"}), 400

    nights = (check_out - check_in).days
    total_price = nights * hotel["price_per_night"]

    reservation = {
        "reservation_id": next_reservation_id,
        "guest_name": data["guest_name"],
        "hotel_id": hotel["id"],
        "hotel_name": hotel["name"],
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": guests,
        "nights": nights,
        "total_price": total_price,
        "status": "Confirmed"
    }

    reservations.append(reservation)
    next_reservation_id += 1

    return jsonify(reservation), 201


@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations)
if __name__ == "__main__":
    app.run(debug=True)