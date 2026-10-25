"""
Hotel Reservation Management System - Flask backend
Serves both the REST API (/api/...) and the frontend (../frontend).
Run:  python app.py   then open http://127.0.0.1:5000
"""
import os
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, request, send_from_directory, session
from flask.json.provider import DefaultJSONProvider
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection

# ---------------------------------------------------------------- setup
app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ACTIVE_STATUSES = "('Confirmed', 'Checked-In')"


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    return DefaultJSONProvider.default(o)


class JSONProvider(DefaultJSONProvider):
    default = staticmethod(_json_default)


app.json = JSONProvider(app)


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({"error": err.message}), err.status


@app.errorhandler(mysql.connector.Error)
def handle_db_error(err):
    # 1644 = our trigger's SIGNAL (double booking caught by the database)
    if getattr(err, "errno", None) == 1644:
        return jsonify({"error": "Room is already booked for these dates"}), 409
    if getattr(err, "errno", None) == 1062:
        return jsonify({"error": "Duplicate entry (already exists)"}), 409
    app.logger.exception("Database error")
    return jsonify({"error": "Database error. Is MySQL running and is db.py correct?"}), 500


@app.errorhandler(404)
def handle_404(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(app.static_folder, "index.html")


@contextmanager
def db():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    try:
        yield conn, cur
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------- helpers
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            raise ApiError("Please log in first", 401)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            raise ApiError("Please log in first", 401)
        if session.get("role") != "admin":
            raise ApiError("Admin access only", 403)
        return fn(*args, **kwargs)
    return wrapper


def body():
    return request.get_json(silent=True) or {}


def to_int(value, name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{name} must be a number")


def to_price(value):
    try:
        price = Decimal(str(value))
    except Exception:
        raise ApiError("price_per_night must be a number")
    if price < 0:
        raise ApiError("price_per_night cannot be negative")
    return price


def parse_dates(check_in, check_out, allow_past=False):
    try:
        d_in = date.fromisoformat(str(check_in))
        d_out = date.fromisoformat(str(check_out))
    except ValueError:
        raise ApiError("Dates must be in YYYY-MM-DD format")
    if d_out <= d_in:
        raise ApiError("Check-out must be after check-in")
    if not allow_past and d_in < date.today():
        raise ApiError("Check-in cannot be in the past")
    return d_in, d_out


def get_reservation(cur, reservation_id):
    cur.execute("SELECT * FROM v_reservation_details WHERE reservation_id = %s",
                (reservation_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError("Reservation not found", 404)
    return row


def check_owner_or_admin(res):
    if session.get("role") != "admin" and res["user_id"] != session["user_id"]:
        raise ApiError("This is not your reservation", 403)


# ---------------------------------------------------------------- frontend
@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------- auth
@app.route("/api/register", methods=["POST"])
def register():
    data = body()
    name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))

    if len(name) < 2:
        raise ApiError("Please enter your full name")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ApiError("Please enter a valid email")
    if phone and not re.fullmatch(r"\d{10,15}", phone):
        raise ApiError("Phone must be 10-15 digits")
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters")

    with db() as (conn, cur):
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise ApiError("This email is already registered", 409)
        cur.execute(
            "INSERT INTO users (full_name, email, phone, password_hash, role) "
            "VALUES (%s, %s, %s, %s, 'guest')",
            (name, email, phone or None, generate_password_hash(password)),
        )
        conn.commit()
        user_id = cur.lastrowid

    session.clear()
    session.update(user_id=user_id, role="guest", name=name)
    return jsonify({"user_id": user_id, "full_name": name, "role": "guest"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    with db() as (_, cur):
        cur.execute("SELECT user_id, full_name, password_hash, role "
                    "FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        raise ApiError("Wrong email or password", 401)

    session.clear()
    session.update(user_id=user["user_id"], role=user["role"], name=user["full_name"])
    return jsonify({"user_id": user["user_id"], "full_name": user["full_name"],
                    "role": user["role"]})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"user": None})
    return jsonify({"user": {"user_id": session["user_id"],
                             "full_name": session["name"],
                             "role": session["role"]}})


# ---------------------------------------------------------------- rooms
@app.route("/api/room-types")
def room_types():
    with db() as (_, cur):
        cur.execute("SELECT type_id, type_name, description FROM room_types ORDER BY type_id")
        return jsonify(cur.fetchall())


@app.route("/api/rooms/available")
def available_rooms():
    d_in, d_out = parse_dates(request.args.get("check_in"), request.args.get("check_out"))
    guests = to_int(request.args.get("guests", 1), "guests")
    if guests < 1:
        raise ApiError("Guests must be at least 1")
    type_id = request.args.get("type_id", "").strip()

    sql = f"""
        SELECT r.room_id, r.room_number, r.type_id, rt.type_name,
               r.price_per_night, r.capacity, r.description
        FROM rooms r
        JOIN room_types rt ON rt.type_id = r.type_id
        WHERE r.is_active = TRUE
          AND r.capacity >= %s
          {"AND r.type_id = %s" if type_id else ""}
          AND NOT EXISTS (
                SELECT 1 FROM reservations res
                WHERE res.room_id = r.room_id
                  AND res.booking_status IN {ACTIVE_STATUSES}
                  AND res.check_in  < %s
                  AND res.check_out > %s)
        ORDER BY r.price_per_night, r.room_number
    """
    params = [guests]
    if type_id:
        params.append(to_int(type_id, "type_id"))
    params += [d_out, d_in]

    nights = (d_out - d_in).days
    with db() as (_, cur):
        cur.execute(sql, params)
        rooms = cur.fetchall()
    for r in rooms:
        r["nights"] = nights
        r["total_price"] = float(r["price_per_night"]) * nights
    return jsonify(rooms)


@app.route("/api/rooms")
def list_rooms():
    show_all = session.get("role") == "admin"
    with db() as (_, cur):
        cur.execute(f"""
            SELECT r.room_id, r.room_number, r.type_id, rt.type_name,
                   r.price_per_night, r.capacity, r.description, r.is_active
            FROM rooms r JOIN room_types rt ON rt.type_id = r.type_id
            {"" if show_all else "WHERE r.is_active = TRUE"}
            ORDER BY r.room_number""")
        return jsonify(cur.fetchall())


def validate_room(data, partial=False):
    out = {}
    if "room_number" in data or not partial:
        num = str(data.get("room_number", "")).strip()
        if not num or len(num) > 10:
            raise ApiError("Room number is required (max 10 characters)")
        out["room_number"] = num
    if "type_id" in data or not partial:
        out["type_id"] = to_int(data.get("type_id"), "type_id")
    if "price_per_night" in data or not partial:
        out["price_per_night"] = to_price(data.get("price_per_night"))
    if "capacity" in data or not partial:
        cap = to_int(data.get("capacity"), "capacity")
        if cap < 1:
            raise ApiError("Capacity must be at least 1")
        out["capacity"] = cap
    if "description" in data:
        out["description"] = str(data.get("description", "")).strip()[:255]
    if "is_active" in data:
        out["is_active"] = bool(data["is_active"])
    return out


@app.route("/api/rooms", methods=["POST"])
@admin_required
def add_room():
    room = validate_room(body())
    room.setdefault("description", "")
    with db() as (conn, cur):
        cur.execute("SELECT 1 FROM room_types WHERE type_id = %s", (room["type_id"],))
        if not cur.fetchone():
            raise ApiError("Room type does not exist")
        cur.execute("SELECT 1 FROM rooms WHERE room_number = %s", (room["room_number"],))
        if cur.fetchone():
            raise ApiError("Room number already exists", 409)
        cur.execute(
            "INSERT INTO rooms (room_number, type_id, price_per_night, capacity, description) "
            "VALUES (%s, %s, %s, %s, %s)",
            (room["room_number"], room["type_id"], room["price_per_night"],
             room["capacity"], room["description"]))
        conn.commit()
        return jsonify({"room_id": cur.lastrowid, "message": "Room added"}), 201


@app.route("/api/rooms/<int:room_id>", methods=["PUT"])
@admin_required
def update_room(room_id):
    changes = validate_room(body(), partial=True)
    if not changes:
        raise ApiError("Nothing to update")
    cols = ", ".join(f"{k} = %s" for k in changes)
    with db() as (conn, cur):
        cur.execute("SELECT 1 FROM rooms WHERE room_id = %s", (room_id,))
        if not cur.fetchone():
            raise ApiError("Room not found", 404)
        if "room_number" in changes:
            cur.execute("SELECT 1 FROM rooms WHERE room_number = %s AND room_id <> %s",
                        (changes["room_number"], room_id))
            if cur.fetchone():
                raise ApiError("Room number already exists", 409)
        cur.execute(f"UPDATE rooms SET {cols} WHERE room_id = %s",
                    list(changes.values()) + [room_id])
        conn.commit()
    return jsonify({"message": "Room updated"})


# ---------------------------------------------------------------- reservations
@app.route("/api/reservations", methods=["POST"])
@login_required
def create_reservation():
    data = body()
    room_id = to_int(data.get("room_id"), "room_id")
    guests = to_int(data.get("guests", 1), "guests")
    d_in, d_out = parse_dates(data.get("check_in"), data.get("check_out"))
    if guests < 1:
        raise ApiError("Guests must be at least 1")

    with db() as (conn, cur):
        conn.start_transaction()
        # lock the room row so two people cannot book it at the same moment
        cur.execute("SELECT room_id, price_per_night, capacity FROM rooms "
                    "WHERE room_id = %s AND is_active = TRUE FOR UPDATE", (room_id,))
        room = cur.fetchone()
        if not room:
            raise ApiError("Room not found or unavailable", 404)
        if guests > room["capacity"]:
            raise ApiError(f"This room allows maximum {room['capacity']} guests")

        cur.execute(f"""SELECT 1 FROM reservations
                        WHERE room_id = %s AND booking_status IN {ACTIVE_STATUSES}
                          AND check_in < %s AND check_out > %s LIMIT 1""",
                    (room_id, d_out, d_in))
        if cur.fetchone():
            raise ApiError("Room is already booked for these dates", 409)

        total = float(room["price_per_night"]) * (d_out - d_in).days
        cur.execute(
            "INSERT INTO reservations (user_id, room_id, check_in, check_out, guests, total_amount) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (session["user_id"], room_id, d_in, d_out, guests, total))
        new_id = cur.lastrowid
        conn.commit()
        return jsonify(get_reservation(cur, new_id)), 201


@app.route("/api/reservations/mine")
@login_required
def my_reservations():
    with db() as (_, cur):
        cur.execute("SELECT * FROM v_reservation_details WHERE user_id = %s "
                    "ORDER BY reservation_id DESC", (session["user_id"],))
        return jsonify(cur.fetchall())


@app.route("/api/reservations")
@admin_required
def all_reservations():
    status = request.args.get("status", "").strip()
    with db() as (_, cur):
        if status:
            cur.execute("SELECT * FROM v_reservation_details WHERE booking_status = %s "
                        "ORDER BY reservation_id DESC", (status,))
        else:
            cur.execute("SELECT * FROM v_reservation_details ORDER BY reservation_id DESC")
        return jsonify(cur.fetchall())


@app.route("/api/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    with db() as (conn, cur):
        res = get_reservation(cur, reservation_id)
        check_owner_or_admin(res)
        if res["booking_status"] != "Confirmed":
            raise ApiError(f"A {res['booking_status']} reservation cannot be cancelled", 409)
        cur.execute("UPDATE reservations SET booking_status = 'Cancelled' "
                    "WHERE reservation_id = %s", (reservation_id,))
        # money already paid goes back
        cur.execute("UPDATE payments SET payment_status = 'Refunded' "
                    "WHERE reservation_id = %s AND payment_status = 'Paid'",
                    (reservation_id,))
        refunded = cur.rowcount > 0
        conn.commit()
    return jsonify({"message": "Reservation cancelled" +
                    (" and payment refunded" if refunded else "")})


@app.route("/api/reservations/<int:reservation_id>/pay", methods=["POST"])
@login_required
def pay_reservation(reservation_id):
    method = str(body().get("payment_method", "")).strip()
    if method not in ("Cash", "Card", "UPI"):
        raise ApiError("Payment method must be Cash, Card or UPI")
    with db() as (conn, cur):
        res = get_reservation(cur, reservation_id)
        check_owner_or_admin(res)
        if res["booking_status"] not in ("Confirmed", "Checked-In"):
            raise ApiError("Only active reservations can be paid", 409)
        if res["payment_status"] == "Paid":
            raise ApiError("This reservation is already paid", 409)
        # (demo) payment is simulated - a real site would call a payment gateway here
        cur.execute("INSERT INTO payments (reservation_id, amount, payment_method, payment_status) "
                    "VALUES (%s, %s, %s, 'Paid')",
                    (reservation_id, res["total_amount"], method))
        conn.commit()
    return jsonify({"message": f"Payment of Rs. {res['total_amount']:.2f} received via {method}"})


@app.route("/api/reservations/<int:reservation_id>/check-in", methods=["POST"])
@admin_required
def check_in(reservation_id):
    with db() as (conn, cur):
        res = get_reservation(cur, reservation_id)
        if res["booking_status"] != "Confirmed":
            raise ApiError(f"Cannot check in a {res['booking_status']} reservation", 409)
        cur.execute("UPDATE reservations SET booking_status = 'Checked-In' "
                    "WHERE reservation_id = %s", (reservation_id,))
        conn.commit()
    return jsonify({"message": "Guest checked in"})


@app.route("/api/reservations/<int:reservation_id>/check-out", methods=["POST"])
@admin_required
def check_out(reservation_id):
    with db() as (conn, cur):
        res = get_reservation(cur, reservation_id)
        if res["booking_status"] != "Checked-In":
            raise ApiError("Only checked-in guests can be checked out", 409)
        if res["payment_status"] != "Paid":
            raise ApiError("Payment pending - collect payment before check-out", 409)
        cur.execute("UPDATE reservations SET booking_status = 'Checked-Out' "
                    "WHERE reservation_id = %s", (reservation_id,))
        conn.commit()
    return jsonify({"message": "Guest checked out"})


# ---------------------------------------------------------------- admin reports
@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    with db() as (_, cur):
        cur.execute("SELECT COUNT(*) AS n FROM rooms WHERE is_active = TRUE")
        total_rooms = cur.fetchone()["n"]
        cur.execute(f"""SELECT COUNT(DISTINCT room_id) AS n FROM reservations
                        WHERE booking_status IN {ACTIVE_STATUSES}
                          AND check_in <= CURDATE() AND check_out > CURDATE()""")
        occupied = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'guest'")
        guests = cur.fetchone()["n"]
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS n FROM payments WHERE payment_status = 'Paid'")
        revenue = cur.fetchone()["n"]
        cur.execute("SELECT booking_status, COUNT(*) AS count FROM reservations GROUP BY booking_status")
        by_status = cur.fetchall()
        cur.execute("""SELECT rt.type_name, COALESCE(SUM(p.amount), 0) AS revenue
                       FROM room_types rt
                       LEFT JOIN rooms r ON r.type_id = rt.type_id
                       LEFT JOIN reservations res ON res.room_id = r.room_id
                       LEFT JOIN payments p ON p.reservation_id = res.reservation_id
                                           AND p.payment_status = 'Paid'
                       GROUP BY rt.type_id, rt.type_name ORDER BY rt.type_id""")
        by_type = cur.fetchall()
    return jsonify({"total_rooms": total_rooms, "occupied_today": occupied,
                    "total_guests": guests, "total_revenue": revenue,
                    "reservations_by_status": by_status, "revenue_by_room_type": by_type})


@app.route("/api/admin/users")
@admin_required
def admin_users():
    with db() as (_, cur):
        cur.execute("""SELECT u.user_id, u.full_name, u.email, u.phone, u.created_at,
                              COUNT(res.reservation_id) AS bookings
                       FROM users u
                       LEFT JOIN reservations res ON res.user_id = u.user_id
                       WHERE u.role = 'guest'
                       GROUP BY u.user_id, u.full_name, u.email, u.phone, u.created_at
                       ORDER BY u.user_id""")
        return jsonify(cur.fetchall())


if __name__ == "__main__":
    app.run(debug=True)
