document.addEventListener("DOMContentLoaded", function () {
    // Navigation menu links
    const navLinks = document.querySelectorAll("nav a");

    navLinks.forEach(function (link) {
        link.addEventListener("click", function () {
            console.log("Navigating to: " + link.href);
        });
    });

    // Registration form validation
    const registerForm = document.getElementById("registerForm");

    if (registerForm) {
        registerForm.addEventListener("submit", function (event) {
            const password = document.getElementById("password");
            const confirmPassword =
                document.getElementById("confirmPassword");

            if (
                password &&
                confirmPassword &&
                password.value !== confirmPassword.value
            ) {
                event.preventDefault();
                alert("Passwords do not match!");
            }
        });
    }

    // Booking page room selection
    const roomSelect = document.getElementById("roomType");
    const checkIn = document.getElementById("checkIn");
    const checkOut = document.getElementById("checkOut");

    if (roomSelect) {
        roomSelect.addEventListener("change", function () {
            console.log("Selected room: " + roomSelect.value);
        });
    }

    if (checkIn && checkOut) {
        checkIn.addEventListener("change", function () {
            checkOut.min = checkIn.value;
        });
    }

    console.log("Hotel Reservation System JavaScript loaded!");
});