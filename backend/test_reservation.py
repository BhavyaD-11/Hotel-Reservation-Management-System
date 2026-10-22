import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

url = "http://127.0.0.1:5000/api/reservations"

booking = {
    "guest_name": "Rahul Sharma",
    "hotel_id": 1,
    "check_in": "2027-01-10",
    "check_out": "2027-01-12",
    "guests": 2
}

request = Request(
    url,
    data=json.dumps(booking).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urlopen(request) as response:
        print("Status:", response.status)
        print(response.read().decode("utf-8"))
except HTTPError as error:
    print("Status:", error.code)
    print(error.read().decode("utf-8"))