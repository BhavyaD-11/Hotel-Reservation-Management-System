/* Hotel Reservation Management System - frontend logic
   Talks to the Flask API on the same origin (/api/...). */

const $ = (id) => document.getElementById(id);
const state = { user: null, search: null, payingId: null, editingRoomId: null, types: [] };

// ---------------------------------------------------------------- helpers
const esc = (v) => String(v ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => "Rs. " + Number(n || 0).toLocaleString("en-IN");
const fmtDate = (d) => new Date(d + "T00:00:00").toLocaleDateString("en-IN",
    { day: "2-digit", month: "short", year: "numeric" });
const isoDate = (d) => {
    const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return z.toISOString().slice(0, 10);
};

async function api(path, options = {}) {
    const opts = { credentials: "same-origin", ...options };
    if (opts.body && typeof opts.body !== "string") {
        opts.body = JSON.stringify(opts.body);
        opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    }
    const res = await fetch("/api" + path, opts);
    let data = {};
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) {
        const err = new Error(data.error || "Something went wrong");
        err.status = res.status;
        throw err;
    }
    return data;
}

let toastTimer;
function toast(message, isError = false) {
    const t = $("toast");
    t.textContent = message;
    t.className = "show" + (isError ? " error" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.className = ""), 3500);
}

// every button/link click wrapped so an error becomes a toast, not a silent failure
const safe = (fn) => async (...args) => {
    try { await fn(...args); } catch (e) { toast(e.message, true); }
};

// ---------------------------------------------------------------- navigation
function showView(name) {
    if (name === "bookings" && !state.user) { openAuth("login"); return; }
    if (name === "admin" && state.user?.role !== "admin") { return; }
    document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== "view-" + name));
    document.querySelectorAll(".nav-btn").forEach((b) =>
        b.classList.toggle("active", b.dataset.nav === name));
    if (name === "bookings") safe(loadMyBookings)();
    if (name === "admin") safe(() => showAdminTab(currentAdminTab))();
}
document.querySelectorAll("[data-nav]").forEach((el) =>
    el.addEventListener("click", (e) => { e.preventDefault(); showView(el.dataset.nav); }));

// ---------------------------------------------------------------- dialogs
document.querySelectorAll("dialog").forEach((d) => {
    d.addEventListener("click", (e) => {
        if (e.target === d || e.target.closest("[data-close]")) d.close();
    });
});

// ---------------------------------------------------------------- auth
function renderUser() {
    const u = state.user;
    $("whoami").textContent = u ? `${u.full_name}${u.role === "admin" ? " (admin)" : ""}` : "";
    $("btn-login").hidden = !!u;
    $("btn-logout").hidden = !u;
    $("nav-bookings").hidden = !u || u.role === "admin";
    $("nav-admin").hidden = !u || u.role !== "admin";
}

function openAuth(mode) {
    document.querySelectorAll("[data-auth]").forEach((b) =>
        b.classList.toggle("active", b.dataset.auth === mode));
    $("login-form").hidden = mode !== "login";
    $("register-form").hidden = mode !== "register";
    $("login-error").textContent = "";
    $("register-error").textContent = "";
    if (!$("auth-dialog").open) $("auth-dialog").showModal();
}
document.querySelectorAll("[data-auth]").forEach((b) =>
    b.addEventListener("click", () => openAuth(b.dataset.auth)));
$("btn-login").addEventListener("click", () => openAuth("login"));

$("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
        await api("/login", { method: "POST",
            body: { email: $("l-email").value, password: $("l-pass").value } });
        await afterAuth("Welcome back!");
    } catch (err) { $("login-error").textContent = err.message; }
});

$("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
        await api("/register", { method: "POST", body: {
            full_name: $("r-name").value, email: $("r-email").value,
            phone: $("r-phone").value, password: $("r-pass").value } });
        await afterAuth("Account created. Welcome!");
    } catch (err) { $("register-error").textContent = err.message; }
});

async function afterAuth(message) {
    $("auth-dialog").close();
    $("login-form").reset();
    $("register-form").reset();
    await loadUser();
    toast(message);
    showView(state.user?.role === "admin" ? "admin" : "search");
}

$("btn-logout").addEventListener("click", safe(async () => {
    await api("/logout", { method: "POST" });
    state.user = null;
    renderUser();
    showView("search");
    toast("Logged out");
}));

async function loadUser() {
    const data = await api("/me");
    state.user = data.user;
    renderUser();
}

// ---------------------------------------------------------------- search + booking
async function loadRoomTypes() {
    state.types = await api("/room-types");
    $("s-type").innerHTML = '<option value="">Any type</option>' +
        state.types.map((t) => `<option value="${t.type_id}">${esc(t.type_name)}</option>`).join("");
    $("rm-type").innerHTML = state.types.map((t) =>
        `<option value="${t.type_id}">${esc(t.type_name)}</option>`).join("");
}

$("search-form").addEventListener("submit", safe(async (e) => {
    e.preventDefault();
    const q = new URLSearchParams({
        check_in: $("s-in").value, check_out: $("s-out").value,
        guests: $("s-guests").value, type_id: $("s-type").value });
    const rooms = await api("/rooms/available?" + q);
    state.search = { check_in: $("s-in").value, check_out: $("s-out").value,
                     guests: Number($("s-guests").value) };
    renderRooms(rooms);
}));

function renderRooms(rooms) {
    const s = state.search;
    const nights = rooms[0]?.nights;
    $("search-summary").textContent = rooms.length
        ? `${rooms.length} room${rooms.length > 1 ? "s" : ""} available, ${fmtDate(s.check_in)} to ${fmtDate(s.check_out)}`
        : "No rooms are free for those dates. Try different dates or fewer guests.";
    $("results").innerHTML = rooms.map((r) => `
        <article class="room">
            <div class="key-tag">${esc(r.room_number)}</div>
            <div>
                <h3>${esc(r.type_name)} room</h3>
                <p>${esc(r.description)}</p>
                <p class="meta">Sleeps up to ${r.capacity}</p>
            </div>
            <div class="price">
                <strong>${money(r.total_price)}</strong>
                <span>${r.nights} night${r.nights > 1 ? "s" : ""} at ${money(r.price_per_night)}</span>
                <button class="btn primary" data-book="${r.room_id}">Book this room</button>
            </div>
        </article>`).join("");
}

$("results").addEventListener("click", safe(async (e) => {
    const btn = e.target.closest("[data-book]");
    if (!btn) return;
    if (!state.user) { toast("Please log in to book a room", true); openAuth("login"); return; }
    if (state.user.role === "admin") { toast("Log in as a guest to make a booking", true); return; }
    btn.disabled = true;
    try {
        const r = await api("/reservations", { method: "POST",
            body: { room_id: Number(btn.dataset.book), ...state.search } });
        toast(`Booking #${r.reservation_id} confirmed`);
        $("results").innerHTML = "";
        $("search-summary").textContent = "";
        openPayment(r);
    } finally { btn.disabled = false; }
}));

// ---------------------------------------------------------------- payment
function openPayment(r) {
    state.payingId = r.reservation_id;
    $("pay-title").textContent = `Pay for booking #${r.reservation_id}`;
    $("pay-summary").textContent =
        `Room ${r.room_number} (${r.type_name}), ${fmtDate(r.check_in)} to ${fmtDate(r.check_out)}. ` +
        `Amount due: ${money(r.total_amount)}`;
    $("pay-dialog").showModal();
}

$("pay-dialog").addEventListener("close", () => {
    if ($("my-bookings").offsetParent !== null) safe(loadMyBookings)();
});

$("pay-form").addEventListener("submit", safe(async (e) => {
    e.preventDefault();
    const out = await api(`/reservations/${state.payingId}/pay`, { method: "POST",
        body: { payment_method: $("pay-method").value } });
    $("pay-dialog").close();
    toast(out.message);
    refreshCurrentView();
}));

function refreshCurrentView() {
    if (!$("view-bookings").hidden) loadMyBookings().catch(() => {});
    if (!$("view-admin").hidden) showAdminTab(currentAdminTab).catch(() => {});
}

// ---------------------------------------------------------------- my bookings
function bookingTable(rows, admin) {
    if (!rows.length) return '<p class="empty">No reservations found.</p>';
    return `<table>
        <thead><tr><th>#</th>${admin ? "<th>Guest</th>" : ""}<th>Room</th><th>Dates</th>
            <th>Guests</th><th>Total</th><th>Status</th><th>Payment</th><th></th></tr></thead>
        <tbody>${rows.map((r) => {
            const active = r.booking_status === "Confirmed" || r.booking_status === "Checked-In";
            const acts = [];
            if (active && r.payment_status !== "Paid")
                acts.push(`<button class="btn small primary" data-act="pay" data-id="${r.reservation_id}">Pay</button>`);
            if (admin && r.booking_status === "Confirmed")
                acts.push(`<button class="btn small ghost" data-act="check-in" data-id="${r.reservation_id}">Check in</button>`);
            if (admin && r.booking_status === "Checked-In")
                acts.push(`<button class="btn small ghost" data-act="check-out" data-id="${r.reservation_id}">Check out</button>`);
            if (r.booking_status === "Confirmed")
                acts.push(`<button class="btn small danger" data-act="cancel" data-id="${r.reservation_id}">Cancel</button>`);
            return `<tr>
                <td>${r.reservation_id}</td>
                ${admin ? `<td>${esc(r.guest_name)}<br><small class="muted">${esc(r.guest_email)}</small></td>` : ""}
                <td>${esc(r.room_number)} <small class="muted">${esc(r.type_name)}</small></td>
                <td>${fmtDate(r.check_in)} to ${fmtDate(r.check_out)}<br><small class="muted">${r.nights} night(s)</small></td>
                <td>${r.guests}</td>
                <td>${money(r.total_amount)}</td>
                <td><span class="badge ${esc(r.booking_status)}">${esc(r.booking_status)}</span></td>
                <td><span class="badge ${esc(r.payment_status)}">${esc(r.payment_status)}</span></td>
                <td class="actions">${acts.join("")}</td></tr>`;
        }).join("")}</tbody></table>`;
}

async function loadMyBookings() {
    $("my-bookings").innerHTML = bookingTable(await api("/reservations/mine"), false);
}

// one click handler for the buttons in both booking tables
async function handleBookingAction(e) {
    const btn = e.target.closest("[data-act]");
    if (!btn) return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;

    if (act === "pay") {
        const rows = await api(state.user.role === "admin" ? "/reservations" : "/reservations/mine");
        openPayment(rows.find((r) => String(r.reservation_id) === id));
        return;
    }
    if (act === "cancel" && !confirm("Cancel this reservation?")) return;
    const out = await api(`/reservations/${id}/${act}`, { method: "POST" });
    toast(out.message);
    refreshCurrentView();
}
$("my-bookings").addEventListener("click", safe(handleBookingAction));
$("admin-reservations").addEventListener("click", safe(handleBookingAction));

// ---------------------------------------------------------------- admin
let currentAdminTab = "overview";

document.querySelectorAll("[data-tab]").forEach((b) =>
    b.addEventListener("click", safe(() => showAdminTab(b.dataset.tab))));

async function showAdminTab(tab) {
    currentAdminTab = tab;
    document.querySelectorAll("[data-tab]").forEach((b) =>
        b.classList.toggle("active", b.dataset.tab === tab));
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = p.id !== "tab-" + tab));
    if (tab === "overview") await loadOverview();
    if (tab === "reservations") await loadAdminReservations();
    if (tab === "rooms") await loadAdminRooms();
    if (tab === "guests") await loadAdminGuests();
}

async function loadOverview() {
    const s = await api("/admin/stats");
    const maxRev = Math.max(1, ...s.revenue_by_room_type.map((r) => Number(r.revenue)));
    const maxCnt = Math.max(1, ...s.reservations_by_status.map((r) => r.count));
    $("tab-overview").innerHTML = `
        <div class="stats">
            <div class="stat"><strong>${s.occupied_today} / ${s.total_rooms}</strong><span>Rooms occupied today</span></div>
            <div class="stat"><strong>${s.total_guests}</strong><span>Registered guests</span></div>
            <div class="stat"><strong>${money(s.total_revenue)}</strong><span>Revenue collected</span></div>
            <div class="stat"><strong>${s.reservations_by_status.reduce((a, r) => a + r.count, 0)}</strong><span>Total reservations</span></div>
        </div>
        <div class="two-col">
            <div><h3>Reservations by status</h3>${s.reservations_by_status.map((r) => `
                <div class="bar-row"><span>${esc(r.booking_status)}</span>
                <div class="bar"><i style="width:${(r.count / maxCnt) * 100}%"></i></div><b>${r.count}</b></div>`).join("")
                || '<p class="muted">No reservations yet.</p>'}</div>
            <div><h3>Revenue by room type</h3>${s.revenue_by_room_type.map((r) => `
                <div class="bar-row"><span>${esc(r.type_name)}</span>
                <div class="bar"><i style="width:${(Number(r.revenue) / maxRev) * 100}%"></i></div><b>${money(r.revenue)}</b></div>`).join("")}</div>
        </div>`;
}

async function loadAdminReservations() {
    const status = $("a-status").value;
    const rows = await api("/reservations" + (status ? "?status=" + encodeURIComponent(status) : ""));
    $("admin-reservations").innerHTML = bookingTable(rows, true);
}
$("a-status").addEventListener("change", safe(loadAdminReservations));

let adminRooms = [];
async function loadAdminRooms() {
    adminRooms = await api("/rooms");
    $("admin-rooms").innerHTML = `<table>
        <thead><tr><th>Room</th><th>Type</th><th>Price / night</th><th>Capacity</th>
            <th>Description</th><th>Status</th><th></th></tr></thead>
        <tbody>${adminRooms.map((r) => `<tr>
            <td><b>${esc(r.room_number)}</b></td><td>${esc(r.type_name)}</td>
            <td>${money(r.price_per_night)}</td><td>${r.capacity}</td>
            <td>${esc(r.description)}</td>
            <td><span class="badge ${r.is_active ? "Paid" : "Cancelled"}">${r.is_active ? "Active" : "Disabled"}</span></td>
            <td><button class="btn small ghost" data-edit-room="${r.room_id}">Edit</button></td></tr>`).join("")}
        </tbody></table>`;
}

function openRoomDialog(room) {
    state.editingRoomId = room ? room.room_id : null;
    $("room-dialog-title").textContent = room ? `Edit room ${room.room_number}` : "Add room";
    $("rm-number").value = room?.room_number ?? "";
    $("rm-type").value = room?.type_id ?? state.types[0]?.type_id ?? "";
    $("rm-price").value = room?.price_per_night ?? "";
    $("rm-capacity").value = room?.capacity ?? 2;
    $("rm-desc").value = room?.description ?? "";
    $("rm-active").checked = room ? !!room.is_active : true;
    $("room-error").textContent = "";
    $("room-dialog").showModal();
}
$("btn-add-room").addEventListener("click", () => openRoomDialog(null));
$("admin-rooms").addEventListener("click", (e) => {
    const b = e.target.closest("[data-edit-room]");
    if (b) openRoomDialog(adminRooms.find((r) => String(r.room_id) === b.dataset.editRoom));
});

$("room-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
        room_number: $("rm-number").value, type_id: Number($("rm-type").value),
        price_per_night: Number($("rm-price").value), capacity: Number($("rm-capacity").value),
        description: $("rm-desc").value, is_active: $("rm-active").checked };
    try {
        if (state.editingRoomId) {
            await api(`/rooms/${state.editingRoomId}`, { method: "PUT", body: payload });
        } else {
            await api("/rooms", { method: "POST", body: payload });
        }
        $("room-dialog").close();
        toast("Room saved");
        await loadAdminRooms();
    } catch (err) { $("room-error").textContent = err.message; }
});

async function loadAdminGuests() {
    const rows = await api("/admin/users");
    $("admin-guests").innerHTML = rows.length ? `<table>
        <thead><tr><th>#</th><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th><th>Bookings</th></tr></thead>
        <tbody>${rows.map((u) => `<tr><td>${u.user_id}</td><td>${esc(u.full_name)}</td>
            <td>${esc(u.email)}</td><td>${esc(u.phone || "-")}</td>
            <td>${fmtDate(String(u.created_at).slice(0, 10))}</td><td>${u.bookings}</td></tr>`).join("")}
        </tbody></table>` : '<p class="empty">No guests yet.</p>';
}

// ---------------------------------------------------------------- start
(async function init() {
    const today = new Date();
    const tomorrow = new Date(today.getTime() + 86400000);
    $("s-in").min = $("s-out").min = isoDate(today);
    $("s-in").value = isoDate(today);
    $("s-out").value = isoDate(tomorrow);
    $("s-in").addEventListener("change", () => {
        const next = new Date($("s-in").value + "T00:00:00");
        next.setDate(next.getDate() + 1);
        $("s-out").min = isoDate(next);
        if ($("s-out").value <= $("s-in").value) $("s-out").value = isoDate(next);
    });
    try {
        await Promise.all([loadUser(), loadRoomTypes()]);
        if (state.user?.role === "admin") showView("admin");
    } catch (e) {
        toast("Cannot reach the server. Is app.py running and MySQL started?", true);
    }
})();
