"""
Grand Haven Hotel Manager - a beginner-friendly Hotel Management Dashboard.

Built with Streamlit, pandas and Plotly. The whole application lives in this
single file. Data is kept in Streamlit's session state (memory only), so it is
reset whenever the browser session ends or the deployed app restarts.

Run locally with:  streamlit run app.py
"""

import re
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# =============================================================================
# 1. CONFIGURATION AND CONSTANTS
# =============================================================================

APP_TITLE = "Grand Haven Hotel Manager"
CURRENCY = "$"

ROOM_TYPES = ["Single", "Double", "Deluxe", "Suite"]
ROOM_STATUSES = ["Available", "Occupied", "Maintenance"]
RESERVATION_STATUSES = ["Confirmed", "Checked In", "Checked Out", "Cancelled"]
ACTIVE_RESERVATION_STATUSES = ["Confirmed", "Checked In"]  # These block a room
PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "Bank Transfer", "Mobile Wallet"]
PAYMENT_STATUSES = ["Paid", "Pending", "Failed", "Refunded"]
STAFF_STATUSES = ["Active", "On Leave", "Inactive"]

# Allowed next steps for a reservation's status
STATUS_TRANSITIONS = {
    "Confirmed": ["Checked In", "Cancelled"],
    "Checked In": ["Checked Out"],
}

# Small icons make statuses easy to scan in tables
STATUS_ICONS = {
    "Available": "🟢", "Occupied": "🔴", "Maintenance": "🟠",
    "Confirmed": "🔵", "Checked In": "🟢", "Checked Out": "⚪", "Cancelled": "🔴",
    "Paid": "🟢", "Pending": "🟡", "Failed": "🔴", "Refunded": "🟣",
    "Active": "🟢", "On Leave": "🟡", "Inactive": "⚫",
    "Booked": "🔴", "Too small": "⚪",
}

# Column names for every table (kept in one place to avoid typos)
GUEST_COLS = ["Guest ID", "Full Name", "Phone", "Email", "Address"]
ROOM_COLS = ["Room Number", "Room Type", "Price per Night", "Capacity", "Status"]
RESERVATION_COLS = ["Reservation ID", "Guest ID", "Room Number", "Check-In",
                    "Check-Out", "Guests", "Nights", "Total Cost", "Status"]
PAYMENT_COLS = ["Payment ID", "Reservation ID", "Amount", "Method", "Payment Date", "Status"]
STAFF_COLS = ["Staff ID", "Full Name", "Job Title", "Phone", "Salary", "Status"]

# Chart colours (hotel-style navy, gold, green, brick red, plum, sky blue)
PALETTE = ["#1f4e79", "#c9a227", "#2e8b57", "#b5483a", "#6c5b7b", "#3a9ad9"]
ROOM_STATUS_COLORS = {"Available": "#2e8b57", "Occupied": "#b5483a", "Maintenance": "#c9a227"}

PAGES = [
    "📊 Dashboard", "👥 Guests", "🛏️ Rooms", "📅 Reservations",
    "💳 Payments", "🧑‍💼 Staff", "📑 Reports",
]

CUSTOM_CSS = """
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1250px;}
    .main-banner {
        background: linear-gradient(135deg, #1f3a5f 0%, #2c5282 60%, #c9a227 100%);
        padding: 1.2rem 1.5rem; border-radius: 14px; margin-bottom: 1.2rem;
    }
    .main-banner h1 {margin: 0; padding: 0; font-size: 1.8rem; color: #ffffff;}
    .main-banner p {margin: 0.25rem 0 0 0; color: #f1f5f9; font-size: 0.95rem;}
    .metric-card {
        background: #ffffff; border-radius: 12px; padding: 0.9rem 1.1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.10); margin-bottom: 0.8rem;
    }
    .metric-label {color: #6b7280; font-size: 0.78rem; text-transform: uppercase;
                   letter-spacing: 0.05em; font-weight: 600;}
    .metric-value {color: #1f2937; font-size: 1.65rem; font-weight: 700; line-height: 1.3;}
    .metric-icon {float: right; font-size: 1.6rem;}
    @media (max-width: 640px) {
        .main-banner h1 {font-size: 1.35rem;}
        .metric-value {font-size: 1.3rem;}
        .block-container {padding-left: 0.8rem; padding-right: 0.8rem;}
    }
</style>
"""


# =============================================================================
# 2. SMALL HELPER FUNCTIONS (formatting, IDs, validation, messages)
# =============================================================================

def money(value):
    """Format a number as currency, e.g. $1,250.00."""
    return f"{CURRENCY}{float(value):,.2f}"


def next_id(df, id_col, prefix, width):
    """Return the next unused ID such as G-011 or RES-1017."""
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)")
    numbers = []
    for value in df[id_col]:
        match = pattern.fullmatch(str(value))
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers) + 1 if numbers else 1
    return f"{prefix}-{number:0{width}d}"


def is_valid_email(email):
    return bool(re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", email.strip()))


def is_valid_phone(phone):
    return bool(re.fullmatch(r"[0-9+\-\s()]{7,20}", phone.strip()))


def flash(kind, message):
    """Store a message to show after the next page refresh (kind: success/error/warning/info)."""
    st.session_state.flash = (kind, message)


def show_flash():
    """Display and clear any stored message."""
    stored = st.session_state.get("flash")
    if stored:
        kind, message = stored
        getattr(st, kind)(message)
        st.session_state.flash = None


def vkey(name):
    """Widget key that changes after each successful action, which resets the widgets."""
    return f"{name}_{st.session_state.form_version}"


def bump_form_version():
    st.session_state.form_version += 1


def append_row(table_name, row):
    """Add one record (a dict) to a table stored in session state."""
    df = st.session_state[table_name]
    new_row = pd.DataFrame([row], columns=df.columns)
    st.session_state[table_name] = new_row if df.empty else pd.concat([df, new_row], ignore_index=True)


def csv_download(label, df, filename, key):
    """Render a CSV download button for a DataFrame."""
    st.download_button(
        f"⬇️ Download {label} (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


# =============================================================================
# 3. SAMPLE DATA
# =============================================================================

def build_sample_data():
    """Create realistic sample records. Dates are relative to today so the demo always looks fresh."""
    today = date.today()

    guests = [
        ("G-001", "Ayesha Khan", "+92 300 1234567", "ayesha.khan@example.com", "12 Garden Road, Lahore"),
        ("G-002", "Michael Turner", "+1 415 555 0132", "m.turner@example.com", "48 Pine Street, San Francisco, USA"),
        ("G-003", "Fatima Noor", "+92 321 7654321", "fatima.noor@example.com", "7 Hill View, Abbottabad"),
        ("G-004", "Daniel Schmidt", "+49 30 5550 1423", "d.schmidt@example.com", "Kastanienallee 21, Berlin, Germany"),
        ("G-005", "Sara Ahmed", "+92 333 9876543", "sara.ahmed@example.com", "25 Blue Area, Islamabad"),
        ("G-006", "Liam O'Connor", "+353 1 555 0187", "liam.oconnor@example.com", "9 Harbour Lane, Dublin, Ireland"),
        ("G-007", "Mei Lin", "+86 21 5550 7788", "mei.lin@example.com", "88 Century Avenue, Shanghai, China"),
        ("G-008", "Omar Farooq", "+92 345 1122334", "omar.farooq@example.com", "3 Mall Road, Peshawar"),
        ("G-009", "Emily Carter", "+44 20 5550 0199", "emily.carter@example.com", "14 Elm Close, London, UK"),
        ("G-010", "Hassan Raza", "+92 300 5566778", "hassan.raza@example.com", "61 Satellite Town, Rawalpindi"),
    ]

    # Room status is recalculated from reservations by sync_room_status()
    rooms = [
        ("101", "Single", 85.0, 1, "Available"), ("102", "Single", 85.0, 1, "Available"),
        ("103", "Double", 120.0, 2, "Available"), ("104", "Double", 120.0, 2, "Available"),
        ("105", "Double", 130.0, 2, "Available"), ("106", "Double", 130.0, 2, "Available"),
        ("201", "Deluxe", 180.0, 3, "Available"), ("202", "Deluxe", 185.0, 3, "Available"),
        ("203", "Deluxe", 190.0, 3, "Available"), ("301", "Suite", 320.0, 4, "Available"),
        ("302", "Suite", 340.0, 4, "Available"), ("303", "Suite", 360.0, 4, "Maintenance"),
    ]
    price_of = {room[0]: room[2] for room in rooms}

    # (guest, room, check-in offset, check-out offset, guests, status) - offsets in days from today
    # No two active reservations overlap in the same room.
    reservation_specs = [
        ("G-004", "203", -75, -72, 2, "Checked Out"),
        ("G-007", "106", -60, -57, 2, "Checked Out"),
        ("G-001", "101", -40, -37, 1, "Checked Out"),
        ("G-002", "103", -30, -26, 2, "Checked Out"),
        ("G-003", "201", -21, -18, 3, "Checked Out"),
        ("G-004", "301", -14, -10, 4, "Checked Out"),
        ("G-005", "104", -9, -5, 2, "Checked Out"),
        ("G-006", "102", -2, 2, 1, "Checked In"),
        ("G-007", "105", -1, 3, 2, "Checked In"),
        ("G-008", "202", 0, 4, 3, "Checked In"),
        ("G-009", "302", -3, 1, 2, "Checked In"),
        ("G-010", "103", 3, 6, 2, "Confirmed"),
        ("G-001", "201", 5, 9, 2, "Confirmed"),
        ("G-002", "106", 2, 5, 2, "Cancelled"),
        ("G-003", "101", 8, 10, 1, "Confirmed"),
        ("G-005", "301", 12, 16, 3, "Confirmed"),
    ]

    reservations = []
    for index, (guest_id, room_no, in_offset, out_offset, num_guests, status) in enumerate(reservation_specs):
        check_in = today + timedelta(days=in_offset)
        check_out = today + timedelta(days=out_offset)
        nights = (check_out - check_in).days
        total = round(nights * price_of[room_no], 2)
        reservations.append((f"RES-{1001 + index}", guest_id, room_no, check_in, check_out,
                             num_guests, nights, total, status))

    # Payments are generated from reservations so the totals always stay consistent
    payments = []
    for index, res in enumerate(reservations):
        _, guest_id, _, check_in, check_out, _, _, total, status = res
        rows = []
        if status == "Checked Out":
            rows.append((total, check_out, "Paid"))                       # paid in full
        elif status == "Checked In":
            rows.append((round(total * 0.5, 2), check_in, "Paid"))        # 50% deposit
            if guest_id == "G-008":
                rows.append((round(total * 0.25, 2), today, "Pending"))   # one pending payment
        elif status == "Confirmed" and index % 2 == 0:
            rows.append((round(total * 0.3, 2), today - timedelta(days=1), "Paid"))
        elif status == "Cancelled":
            rows.append((round(total * 0.3, 2), today - timedelta(days=2), "Refunded"))
        for amount, pay_date, pay_status in rows:
            number = len(payments) + 1
            method = PAYMENT_METHODS[number % len(PAYMENT_METHODS)]
            payments.append((f"PAY-{number:04d}", res[0], amount, method, pay_date, pay_status))

    staff = [
        ("STF-001", "Nadia Hussain", "General Manager", "+92 300 1112233", 3200.0, "Active"),
        ("STF-002", "Bilal Ahmed", "Front Desk Agent", "+92 301 2223344", 1100.0, "Active"),
        ("STF-003", "Hira Malik", "Front Desk Agent", "+92 302 3334455", 1100.0, "On Leave"),
        ("STF-004", "Tariq Mehmood", "Head Housekeeper", "+92 303 4445566", 1000.0, "Active"),
        ("STF-005", "Rubina Shah", "Housekeeper", "+92 304 5556677", 750.0, "Active"),
        ("STF-006", "Imran Ali", "Executive Chef", "+92 305 6667788", 2100.0, "Active"),
        ("STF-007", "Zubair Khan", "Maintenance Technician", "+92 306 7778899", 900.0, "Active"),
        ("STF-008", "Sana Iqbal", "Concierge", "+92 307 8889900", 1000.0, "Inactive"),
    ]

    return {
        "guests": pd.DataFrame(guests, columns=GUEST_COLS),
        "rooms": pd.DataFrame(rooms, columns=ROOM_COLS),
        "reservations": pd.DataFrame(reservations, columns=RESERVATION_COLS),
        "payments": pd.DataFrame(payments, columns=PAYMENT_COLS),
        "staff": pd.DataFrame(staff, columns=STAFF_COLS),
    }


def load_sample_data():
    """Put fresh sample data into session state."""
    for name, table in build_sample_data().items():
        st.session_state[name] = table
    sync_room_status()


def init_state():
    """Run once per session: load sample data and set up helper values."""
    if "data_ready" not in st.session_state:
        st.session_state.form_version = 0
        st.session_state.flash = None
        load_sample_data()
        st.session_state.data_ready = True


# =============================================================================
# 4. BUSINESS LOGIC (availability, overlaps, balances, metrics)
# =============================================================================

def sync_room_status():
    """Keep room status consistent with reservations.

    A room is 'Occupied' when it has a Checked In reservation. Rooms set to
    'Maintenance' stay in maintenance. Everything else is 'Available'.
    """
    rooms = st.session_state.rooms
    if rooms.empty:
        return
    reservations = st.session_state.reservations
    occupied = set(reservations.loc[reservations["Status"] == "Checked In", "Room Number"])

    def new_status(row):
        if row["Status"] == "Maintenance":
            return "Maintenance"
        return "Occupied" if row["Room Number"] in occupied else "Available"

    rooms["Status"] = rooms.apply(new_status, axis=1)
    st.session_state.rooms = rooms


def find_conflicts(reservations, room_number, check_in, check_out, ignore_id=None):
    """Return IDs of active reservations that overlap the requested dates for a room.

    Two stays overlap when each one starts before the other ends. A guest may
    check in on the same day another guest checks out.
    """
    active = reservations[(reservations["Room Number"] == room_number)
                          & (reservations["Status"].isin(ACTIVE_RESERVATION_STATUSES))]
    return [
        row["Reservation ID"] for _, row in active.iterrows()
        if row["Reservation ID"] != ignore_id
        and check_in < row["Check-Out"] and check_out > row["Check-In"]
    ]


def availability_overview(rooms, reservations, check_in, check_out, guests):
    """Table showing every room's availability for the chosen dates and party size."""
    rows = []
    for _, room in rooms.iterrows():
        if room["Status"] == "Maintenance":
            state = "Maintenance"
        elif room["Capacity"] < guests:
            state = "Too small"
        elif find_conflicts(reservations, room["Room Number"], check_in, check_out):
            state = "Booked"
        else:
            state = "Available"
        rows.append({"Room Number": room["Room Number"], "Room Type": room["Room Type"],
                     "Capacity": room["Capacity"], "Price per Night": room["Price per Night"],
                     "Availability": state})
    return pd.DataFrame(rows, columns=["Room Number", "Room Type", "Capacity",
                                       "Price per Night", "Availability"])


def build_balance_table(reservations, payments):
    """Per-reservation total cost, amount paid and outstanding balance (only 'Paid' payments count)."""
    paid = payments[payments["Status"] == "Paid"].groupby("Reservation ID")["Amount"].sum()
    table = reservations[["Reservation ID", "Guest ID", "Status", "Total Cost"]].copy()
    table["Paid"] = table["Reservation ID"].map(paid).fillna(0.0)
    table["Outstanding"] = (table["Total Cost"] - table["Paid"]).clip(lower=0).round(2)
    table.loc[table["Status"] == "Cancelled", "Outstanding"] = 0.0  # nothing is owed on cancelled stays
    return table


def paid_for_reservation(payments, reservation_id, exclude_payment_id=None):
    """Sum of 'Paid' payments for one reservation (optionally ignoring one payment)."""
    subset = payments[(payments["Reservation ID"] == reservation_id) & (payments["Status"] == "Paid")]
    if exclude_payment_id:
        subset = subset[subset["Payment ID"] != exclude_payment_id]
    return float(subset["Amount"].sum())


def nights_in_range(check_in, check_out, start, end):
    """How many booked nights of a stay fall inside [start, end] (inclusive)."""
    first = max(check_in, start)
    last = min(check_out, end + timedelta(days=1))
    return max((last - first).days, 0)


def reservations_with_names():
    """Reservations table with the guest's name added for readability."""
    guests = st.session_state.guests[["Guest ID", "Full Name"]].rename(columns={"Full Name": "Guest Name"})
    merged = st.session_state.reservations.merge(guests, on="Guest ID", how="left")
    columns = ["Reservation ID", "Guest ID", "Guest Name"] + RESERVATION_COLS[2:]
    return merged[columns]


def compute_metrics():
    """All numbers shown on the dashboard, calculated from the underlying tables."""
    guests = st.session_state.guests
    rooms = st.session_state.rooms
    reservations = st.session_state.reservations
    payments = st.session_state.payments
    balances = build_balance_table(reservations, payments)
    return {
        "guests": len(guests),
        "rooms": len(rooms),
        "available": int((rooms["Status"] == "Available").sum()),
        "occupied": int((rooms["Status"] == "Occupied").sum()),
        "active": int(reservations["Status"].isin(ACTIVE_RESERVATION_STATUSES).sum()),
        "paid": float(payments.loc[payments["Status"] == "Paid", "Amount"].sum()),
        "estimated": float(reservations.loc[reservations["Status"] != "Cancelled", "Total Cost"].sum()),
        "outstanding": float(balances["Outstanding"].sum()),
    }


# =============================================================================
# 5. REUSABLE USER-INTERFACE PIECES
# =============================================================================

def render_header(title, subtitle):
    """Banner at the top of every page, followed by any pending message."""
    st.markdown(f'<div class="main-banner"><h1>{title}</h1><p>{subtitle}</p></div>',
                unsafe_allow_html=True)
    show_flash()


def metric_card(label, value, icon, color):
    st.markdown(
        f'<div class="metric-card" style="border-left: 6px solid {color};">'
        f'<span class="metric-icon">{icon}</span>'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def show_table(df, money_cols=None, status_col=None):
    """Display a DataFrame as a full-width table, with optional money format and status icons."""
    display = df.copy()
    if status_col and status_col in display.columns:
        display[status_col] = display[status_col].map(lambda s: f"{STATUS_ICONS.get(s, '⚪')} {s}")
    config = {col: st.column_config.NumberColumn(col, format=f"{CURRENCY}%.2f")
              for col in (money_cols or []) if col in display.columns}
    try:
        st.dataframe(display, hide_index=True, column_config=config, width="stretch")
    except Exception:  # older Streamlit versions use a different argument
        st.dataframe(display, hide_index=True, column_config=config, use_container_width=True)


def apply_controls(df, key, search_cols, filter_cols=None, sort_cols=None):
    """Draw search, filter and sort controls and return the resulting DataFrame."""
    filter_cols = filter_cols or {}
    sort_cols = sort_cols or list(df.columns)
    columns = st.columns([2] + [1] * (len(filter_cols) + 2))

    query = columns[0].text_input("🔍 Search", key=f"{key}_search", placeholder="Type to search...")
    result = df.copy()

    for position, (column, options) in enumerate(filter_cols.items(), start=1):
        choice = columns[position].selectbox(f"Filter by {column}", ["All"] + list(options),
                                             key=f"{key}_filter_{column}")
        if choice != "All":
            result = result[result[column] == choice]

    sort_by = columns[-2].selectbox("Sort by", sort_cols, key=f"{key}_sort")
    ascending = columns[-1].selectbox("Order", ["Ascending", "Descending"], key=f"{key}_order") == "Ascending"

    if query.strip():
        needle = query.strip().lower()
        mask = pd.Series(False, index=result.index)
        for column in search_cols:
            mask |= result[column].astype(str).str.lower().str.contains(needle, regex=False)
        result = result[mask]

    if not result.empty:
        result = result.sort_values(sort_by, ascending=ascending, kind="stable")
    return result


def delete_panel(table_name, id_col, key, blocker=None):
    """A safe delete tool: pick a record, tick a confirmation box, then delete."""
    df = st.session_state[table_name]
    with st.expander("🗑️ Delete a record"):
        if df.empty:
            st.info("There are no records to delete.")
            return
        selected = st.selectbox(f"Select {id_col} to delete", df[id_col].tolist(), key=vkey(f"{key}_del_select"))
        confirmed = st.checkbox("Yes, I understand this cannot be undone.", key=vkey(f"{key}_del_confirm"))
        if st.button("Delete record", key=vkey(f"{key}_del_button"), type="primary", disabled=not confirmed):
            reason = blocker(selected) if blocker else None
            if reason:
                st.error(reason)
            else:
                st.session_state[table_name] = df[df[id_col] != selected].reset_index(drop=True)
                sync_room_status()
                flash("success", f"{id_col} {selected} was deleted.")
                bump_form_version()
                st.rerun()


# =============================================================================
# 6. CHARTS
# =============================================================================

def style_figure(fig, height=340):
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=height, legend_title_text="")
    return fig


def chart_room_occupancy(rooms):
    counts = rooms["Status"].value_counts().reset_index()
    counts.columns = ["Status", "Rooms"]
    fig = px.pie(counts, names="Status", values="Rooms", hole=0.55, title="Room Occupancy",
                 color="Status", color_discrete_map=ROOM_STATUS_COLORS)
    return style_figure(fig)


def chart_room_types(rooms):
    counts = rooms["Room Type"].value_counts().reset_index()
    counts.columns = ["Room Type", "Rooms"]
    fig = px.bar(counts, x="Room Type", y="Rooms", color="Room Type", title="Room-Type Distribution",
                 color_discrete_sequence=PALETTE, text="Rooms")
    fig.update_layout(showlegend=False)
    return style_figure(fig)


def chart_reservation_trends(reservations):
    data = reservations.copy()
    data["Month"] = pd.to_datetime(data["Check-In"]).dt.strftime("%Y-%m")
    trend = data.groupby(["Month", "Status"]).size().reset_index(name="Reservations")
    fig = px.bar(trend, x="Month", y="Reservations", color="Status", barmode="stack",
                 title="Reservation Trends (by check-in month)", color_discrete_sequence=PALETTE)
    return style_figure(fig)


def chart_monthly_revenue(payments):
    paid = payments[payments["Status"] == "Paid"].copy()
    paid["Month"] = pd.to_datetime(paid["Payment Date"]).dt.strftime("%Y-%m")
    monthly = paid.groupby("Month")["Amount"].sum().reset_index()
    fig = px.bar(monthly, x="Month", y="Amount", title=f"Revenue Received per Month ({CURRENCY})",
                 color_discrete_sequence=[PALETTE[2]], text_auto=".2s")
    return style_figure(fig)


def chart_payment_methods(payments):
    paid = payments[payments["Status"] == "Paid"].groupby("Method")["Amount"].sum().reset_index()
    fig = px.pie(paid, names="Method", values="Amount", hole=0.4, title="Payment-Method Distribution",
                 color_discrete_sequence=PALETTE)
    return style_figure(fig)


def show_chart(fig, has_data):
    """Show a chart, or a friendly note when there is nothing to plot."""
    if has_data:
        st.plotly_chart(fig)
    else:
        st.info("Not enough data to draw this chart yet.")


# =============================================================================
# 7. PAGES
# =============================================================================

def page_dashboard():
    render_header("Dashboard Overview", "A live summary of rooms, bookings, payments and revenue")
    st.info("ℹ️ **Heads up:** data is stored only in this session's memory. It is reset when the "
            "browser session ends or the deployed app restarts. Download CSV files from the "
            "**Reports** page if you want to keep a copy.")

    m = compute_metrics()
    cards = [
        ("Total Guests", m["guests"], "👥", PALETTE[0]),
        ("Total Rooms", m["rooms"], "🛏️", PALETTE[5]),
        ("Available Rooms", m["available"], "🟢", PALETTE[2]),
        ("Occupied Rooms", m["occupied"], "🔴", PALETTE[3]),
        ("Active Reservations", m["active"], "📅", PALETTE[4]),
        ("Payments Received", money(m["paid"]), "💰", PALETTE[2]),
        ("Estimated Revenue", money(m["estimated"]), "📈", PALETTE[1]),
        ("Outstanding Balance", money(m["outstanding"]), "⏳", PALETTE[3]),
    ]
    for start in (0, 4):
        for column, (label, value, icon, color) in zip(st.columns(4), cards[start:start + 4]):
            with column:
                metric_card(label, value, icon, color)

    rooms = st.session_state.rooms
    reservations = st.session_state.reservations
    payments = st.session_state.payments
    paid_exists = not payments[payments["Status"] == "Paid"].empty

    st.subheader("Charts")
    left, right = st.columns(2)
    with left:
        show_chart(chart_room_occupancy(rooms), not rooms.empty)
    with right:
        show_chart(chart_room_types(rooms), not rooms.empty)
    left, right = st.columns(2)
    with left:
        show_chart(chart_reservation_trends(reservations), not reservations.empty)
    with right:
        show_chart(chart_monthly_revenue(payments), paid_exists)
    left, right = st.columns(2)
    with left:
        show_chart(chart_payment_methods(payments), paid_exists)
    with right:
        today = date.today()
        week = today + timedelta(days=7)
        names = reservations_with_names()
        st.markdown("**Upcoming arrivals (next 7 days)**")
        arrivals = names[(names["Status"] == "Confirmed") & (names["Check-In"] >= today)
                         & (names["Check-In"] <= week)]
        if arrivals.empty:
            st.caption("No arrivals expected in the next 7 days.")
        else:
            show_table(arrivals[["Reservation ID", "Guest Name", "Room Number", "Check-In"]])
        st.markdown("**Upcoming departures (next 7 days)**")
        departures = names[(names["Status"] == "Checked In") & (names["Check-Out"] <= week)]
        if departures.empty:
            st.caption("No departures expected in the next 7 days.")
        else:
            show_table(departures[["Reservation ID", "Guest Name", "Room Number", "Check-Out"]])


# ---------------------------------------------------------------- Guests ----

def validate_guest(guest_id, name, phone, email, address, existing_ids):
    errors = []
    if not guest_id.strip():
        errors.append("Guest ID is required.")
    elif guest_id.strip() in existing_ids:
        errors.append(f"Guest ID {guest_id.strip()} already exists.")
    if len(name.strip()) < 2:
        errors.append("Please enter the guest's full name.")
    if not is_valid_phone(phone):
        errors.append("Phone number must contain 7-20 digits (you may use +, spaces, - and brackets).")
    if not is_valid_email(email):
        errors.append("Please enter a valid email address, e.g. name@example.com.")
    if len(address.strip()) < 5:
        errors.append("Please enter the guest's address.")
    return errors


def page_guests():
    render_header("Guests", "Register guests and search your guest list")
    tab_list, tab_add = st.tabs(["📋 Guest List", "➕ Add Guest"])

    with tab_list:
        guests = st.session_state.guests
        filtered = apply_controls(guests, "guests", ["Guest ID", "Full Name", "Phone", "Email", "Address"])
        st.caption(f"Showing {len(filtered)} of {len(guests)} guests")
        show_table(filtered)

        def guest_blocker(guest_id):
            count = int((st.session_state.reservations["Guest ID"] == guest_id).sum())
            return (f"{guest_id} has {count} reservation(s). Delete or reassign those first."
                    if count else None)

        delete_panel("guests", "Guest ID", "guest", guest_blocker)

    with tab_add:
        with st.form(vkey("guest_form")):
            guest_id = st.text_input("Guest ID", value=next_id(st.session_state.guests, "Guest ID", "G", 3),
                                     key=vkey("g_id"))
            name = st.text_input("Full name", key=vkey("g_name"))
            col1, col2 = st.columns(2)
            phone = col1.text_input("Phone number", placeholder="+92 300 1234567", key=vkey("g_phone"))
            email = col2.text_input("Email", placeholder="name@example.com", key=vkey("g_email"))
            address = st.text_area("Address", key=vkey("g_address"))
            submitted = st.form_submit_button("Add guest", type="primary")

        if submitted:
            errors = validate_guest(guest_id, name, phone, email, address,
                                    set(st.session_state.guests["Guest ID"]))
            if errors:
                for error in errors:
                    st.error(error)
            else:
                append_row("guests", {"Guest ID": guest_id.strip(), "Full Name": name.strip(),
                                      "Phone": phone.strip(), "Email": email.strip(),
                                      "Address": address.strip()})
                flash("success", f"Guest {name.strip()} ({guest_id.strip()}) was added successfully.")
                bump_form_version()
                st.rerun()


# ----------------------------------------------------------------- Rooms ----

def page_rooms():
    render_header("Rooms", "Manage room inventory, pricing and availability")
    tab_list, tab_add, tab_update = st.tabs(["📋 Room List", "➕ Add Room", "✏️ Update Room"])
    rooms = st.session_state.rooms

    with tab_list:
        filtered = apply_controls(rooms, "rooms", ["Room Number", "Room Type"],
                                  filter_cols={"Room Type": ROOM_TYPES, "Status": ROOM_STATUSES})
        st.caption(f"Showing {len(filtered)} of {len(rooms)} rooms")
        show_table(filtered, money_cols=["Price per Night"], status_col="Status")
        st.caption("Room status is automatic: a room is **Occupied** while a guest is checked in. "
                   "You can switch a room to **Maintenance** or back to **Available** in the Update tab.")

        def room_blocker(room_number):
            count = int((st.session_state.reservations["Room Number"] == room_number).sum())
            return (f"Room {room_number} appears in {count} reservation(s). Delete those first."
                    if count else None)

        delete_panel("rooms", "Room Number", "room", room_blocker)

    with tab_add:
        with st.form(vkey("room_form")):
            col1, col2 = st.columns(2)
            number = col1.text_input("Room number", placeholder="e.g. 304", key=vkey("r_number"))
            room_type = col2.selectbox("Room type", ROOM_TYPES, key=vkey("r_type"))
            col3, col4, col5 = st.columns(3)
            price = col3.number_input("Price per night", min_value=0.0, value=100.0, step=5.0,
                                      format="%.2f", key=vkey("r_price"))
            capacity = col4.number_input("Capacity (guests)", min_value=1, max_value=10, value=2,
                                         step=1, key=vkey("r_capacity"))
            status = col5.selectbox("Status", ["Available", "Maintenance"], key=vkey("r_status"))
            submitted = st.form_submit_button("Add room", type="primary")

        if submitted:
            errors = []
            if not number.strip():
                errors.append("Room number is required.")
            elif number.strip() in set(rooms["Room Number"]):
                errors.append(f"Room {number.strip()} already exists.")
            if price <= 0:
                errors.append("Price per night must be greater than zero.")
            if errors:
                for error in errors:
                    st.error(error)
            else:
                append_row("rooms", {"Room Number": number.strip(), "Room Type": room_type,
                                     "Price per Night": float(price), "Capacity": int(capacity),
                                     "Status": status})
                sync_room_status()
                flash("success", f"Room {number.strip()} was added successfully.")
                bump_form_version()
                st.rerun()

    with tab_update:
        if rooms.empty:
            st.info("Add a room first.")
        else:
            room_number = st.selectbox("Room", rooms["Room Number"].tolist(), key=vkey("ru_room"))
            room = rooms[rooms["Room Number"] == room_number].iloc[0]
            col1, col2 = st.columns(2)
            new_price = col1.number_input("Price per night", min_value=0.0, value=float(room["Price per Night"]),
                                          step=5.0, format="%.2f", key=vkey(f"ru_price_{room_number}"))
            if room["Status"] == "Occupied":
                col2.text_input("Status", value="Occupied (a guest is checked in)", disabled=True,
                                key=vkey(f"ru_status_locked_{room_number}"))
                new_status = "Occupied"
            else:
                new_status = col2.selectbox("Status", ["Available", "Maintenance"],
                                            index=0 if room["Status"] == "Available" else 1,
                                            key=vkey(f"ru_status_{room_number}"))
            if st.button("Save changes", type="primary", key=vkey("ru_save")):
                reservations = st.session_state.reservations
                has_bookings = not reservations[(reservations["Room Number"] == room_number)
                                                & (reservations["Status"].isin(ACTIVE_RESERVATION_STATUSES))].empty
                if new_price <= 0:
                    st.error("Price per night must be greater than zero.")
                elif new_status == "Maintenance" and has_bookings:
                    st.error("This room has active reservations. Cancel or finish them before "
                             "moving it to maintenance.")
                else:
                    mask = rooms["Room Number"] == room_number
                    st.session_state.rooms.loc[mask, "Price per Night"] = float(new_price)
                    st.session_state.rooms.loc[mask, "Status"] = new_status
                    sync_room_status()
                    flash("success", f"Room {room_number} was updated.")
                    bump_form_version()
                    st.rerun()


# ---------------------------------------------------------- Reservations ----

def page_reservations():
    render_header("Reservations", "Create bookings, check room availability and track booking status")
    tab_list, tab_new, tab_status = st.tabs(["📋 All Reservations", "➕ New Reservation", "🔄 Update Status"])

    with tab_list:
        names = reservations_with_names()
        filtered = apply_controls(names, "res", ["Reservation ID", "Guest ID", "Guest Name", "Room Number"],
                                  filter_cols={"Status": RESERVATION_STATUSES})
        st.caption(f"Showing {len(filtered)} of {len(names)} reservations")
        show_table(filtered, money_cols=["Total Cost"], status_col="Status")

        def reservation_blocker(reservation_id):
            count = int((st.session_state.payments["Reservation ID"] == reservation_id).sum())
            return (f"{reservation_id} has {count} payment record(s). Delete those first, "
                    "or cancel the reservation instead." if count else None)

        delete_panel("reservations", "Reservation ID", "res", reservation_blocker)

    with tab_new:
        create_reservation_form()

    with tab_status:
        update_reservation_status_form()


def create_reservation_form():
    guests = st.session_state.guests
    rooms = st.session_state.rooms
    reservations = st.session_state.reservations
    if guests.empty or rooms.empty:
        st.warning("You need at least one guest and one room before creating a reservation.")
        return

    today = date.today()
    guest_labels = {row["Guest ID"]: f'{row["Guest ID"]} - {row["Full Name"]}' for _, row in guests.iterrows()}
    guest_id = st.selectbox("Guest", list(guest_labels), format_func=guest_labels.get, key=vkey("n_guest"))

    col1, col2, col3 = st.columns(3)
    check_in = col1.date_input("Check-in date", value=today, min_value=today, key=vkey("n_in"))
    check_out = col2.date_input("Check-out date", value=today + timedelta(days=1), min_value=today,
                                key=vkey("n_out"))
    party = col3.number_input("Number of guests", min_value=1, max_value=10, value=1, step=1, key=vkey("n_party"))

    if check_out <= check_in:
        st.error("Check-out must be at least one day after check-in.")
        return

    nights = (check_out - check_in).days
    overview = availability_overview(rooms, reservations, check_in, check_out, int(party))
    with st.expander("🔎 Room availability for these dates"):
        show_table(overview, money_cols=["Price per Night"], status_col="Availability")

    free_rooms = overview[overview["Availability"] == "Available"]
    if free_rooms.empty:
        st.warning("No rooms are available for these dates and party size. Try different dates.")
        return

    room_labels = {
        row["Room Number"]: f'Room {row["Room Number"]} - {row["Room Type"]} - '
                            f'{money(row["Price per Night"])}/night - up to {row["Capacity"]} guests'
        for _, row in free_rooms.iterrows()
    }
    room_number = st.selectbox("Available room", list(room_labels), format_func=room_labels.get,
                               key=vkey("n_room"))
    price = float(rooms.loc[rooms["Room Number"] == room_number, "Price per Night"].iloc[0])
    total = round(nights * price, 2)

    m1, m2, m3 = st.columns(3)
    m1.metric("Nights", nights)
    m2.metric("Price per night", money(price))
    m3.metric("Total booking cost", money(total))

    if st.button("Create reservation", type="primary", key=vkey("n_create")):
        # Re-check right before saving, in case something changed
        if find_conflicts(reservations, room_number, check_in, check_out):
            st.error("That room has just become unavailable for these dates. Please choose another room.")
            return
        reservation_id = next_id(reservations, "Reservation ID", "RES", 4)
        append_row("reservations", {
            "Reservation ID": reservation_id, "Guest ID": guest_id, "Room Number": room_number,
            "Check-In": check_in, "Check-Out": check_out, "Guests": int(party),
            "Nights": nights, "Total Cost": total, "Status": "Confirmed",
        })
        flash("success", f"Reservation {reservation_id} created for room {room_number}: "
                         f"{nights} night(s), total {money(total)}.")
        bump_form_version()
        st.rerun()


def update_reservation_status_form():
    reservations = st.session_state.reservations
    changeable = reservations[reservations["Status"].isin(STATUS_TRANSITIONS)]
    if changeable.empty:
        st.info("No reservations can change status right now.")
        return

    names = reservations_with_names().set_index("Reservation ID")
    labels = {rid: f'{rid} - {names.loc[rid, "Guest Name"]} - Room {names.loc[rid, "Room Number"]} '
                   f'({names.loc[rid, "Status"]})' for rid in changeable["Reservation ID"]}
    reservation_id = st.selectbox("Reservation", list(labels), format_func=labels.get, key=vkey("s_res"))
    current = reservations.loc[reservations["Reservation ID"] == reservation_id].iloc[0]
    new_status = st.selectbox("Change status to", STATUS_TRANSITIONS[current["Status"]],
                              key=vkey(f"s_new_{reservation_id}"))

    if st.button("Update status", type="primary", key=vkey("s_save")):
        room_number = current["Room Number"]
        rooms = st.session_state.rooms
        room_state = rooms.loc[rooms["Room Number"] == room_number, "Status"]
        problem = None
        if new_status == "Checked In":
            others_in = reservations[(reservations["Room Number"] == room_number)
                                     & (reservations["Status"] == "Checked In")]
            if current["Check-In"] > date.today():
                problem = f"Check-in is scheduled for {current['Check-In']}. You cannot check in earlier."
            elif not room_state.empty and room_state.iloc[0] == "Maintenance":
                problem = f"Room {room_number} is under maintenance."
            elif not others_in.empty:
                problem = f"Room {room_number} is still occupied by another guest."
        if problem:
            st.error(problem)
        else:
            st.session_state.reservations.loc[
                st.session_state.reservations["Reservation ID"] == reservation_id, "Status"] = new_status
            sync_room_status()
            flash("success", f"Reservation {reservation_id} is now '{new_status}'.")
            bump_form_version()
            st.rerun()


# -------------------------------------------------------------- Payments ----

def page_payments():
    render_header("Payments", "Record payments, track balances and review revenue")
    tab_list, tab_add, tab_update, tab_summary = st.tabs(
        ["📋 Payment List", "➕ Record Payment", "🔄 Update Status", "💰 Balances & Revenue"])
    payments = st.session_state.payments
    reservations = st.session_state.reservations
    guest_names = dict(zip(st.session_state.guests["Guest ID"], st.session_state.guests["Full Name"]))

    with tab_list:
        filtered = apply_controls(payments, "pay", ["Payment ID", "Reservation ID", "Method"],
                                  filter_cols={"Method": PAYMENT_METHODS, "Status": PAYMENT_STATUSES})
        st.caption(f"Showing {len(filtered)} of {len(payments)} payments")
        show_table(filtered, money_cols=["Amount"], status_col="Status")
        delete_panel("payments", "Payment ID", "pay")

    with tab_add:
        balances = build_balance_table(reservations, payments)
        owing = balances[(balances["Status"] != "Cancelled") & (balances["Outstanding"] > 0)]
        if owing.empty:
            st.info("All active reservations are fully paid, or there are no reservations yet.")
        else:
            labels = {row["Reservation ID"]: f'{row["Reservation ID"]} - {guest_names.get(row["Guest ID"], "?")} - '
                                             f'outstanding {money(row["Outstanding"])}'
                      for _, row in owing.iterrows()}
            reservation_id = st.selectbox("Reservation", list(labels), format_func=labels.get, key=vkey("p_res"))
            row = owing[owing["Reservation ID"] == reservation_id].iloc[0]
            m1, m2, m3 = st.columns(3)
            m1.metric("Total cost", money(row["Total Cost"]))
            m2.metric("Already paid", money(row["Paid"]))
            m3.metric("Outstanding", money(row["Outstanding"]))

            with st.form(vkey("payment_form")):
                col1, col2 = st.columns(2)
                amount = col1.number_input("Amount", min_value=0.0, value=float(row["Outstanding"]), step=10.0,
                                           format="%.2f", key=vkey(f"p_amount_{reservation_id}"))
                method = col2.selectbox("Payment method", PAYMENT_METHODS, key=vkey("p_method"))
                col3, col4 = st.columns(2)
                pay_date = col3.date_input("Payment date", value=date.today(), key=vkey("p_date"))
                status = col4.selectbox("Payment status", PAYMENT_STATUSES, key=vkey("p_status"))
                submitted = st.form_submit_button("Record payment", type="primary")

            if submitted:
                errors = []
                if amount <= 0:
                    errors.append("Amount must be greater than zero.")
                if status == "Paid" and amount > row["Outstanding"] + 0.005:
                    errors.append(f"Amount cannot exceed the outstanding balance of {money(row['Outstanding'])}.")
                if status == "Paid" and pay_date > date.today():
                    errors.append("A payment marked 'Paid' cannot have a future date.")
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    payment_id = next_id(payments, "Payment ID", "PAY", 4)
                    append_row("payments", {"Payment ID": payment_id, "Reservation ID": reservation_id,
                                            "Amount": round(float(amount), 2), "Method": method,
                                            "Payment Date": pay_date, "Status": status})
                    flash("success", f"Payment {payment_id} of {money(amount)} was recorded ({status}).")
                    bump_form_version()
                    st.rerun()

    with tab_update:
        if payments.empty:
            st.info("There are no payments yet.")
        else:
            payment_id = st.selectbox("Payment", payments["Payment ID"].tolist(), key=vkey("pu_id"))
            payment = payments[payments["Payment ID"] == payment_id].iloc[0]
            st.write(f"Current: **{money(payment['Amount'])}** for **{payment['Reservation ID']}** - "
                     f"{STATUS_ICONS.get(payment['Status'], '')} {payment['Status']}")
            new_status = st.selectbox("New status", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(payment["Status"]),
                                      key=vkey(f"pu_status_{payment_id}"))
            if st.button("Update payment", type="primary", key=vkey("pu_save")):
                match = reservations[reservations["Reservation ID"] == payment["Reservation ID"]]
                if new_status == "Paid" and not match.empty:
                    total = float(match.iloc[0]["Total Cost"])
                    already = paid_for_reservation(payments, payment["Reservation ID"], exclude_payment_id=payment_id)
                    if already + payment["Amount"] > total + 0.005:
                        st.error("Marking this payment as Paid would exceed the reservation's total cost.")
                        return
                st.session_state.payments.loc[st.session_state.payments["Payment ID"] == payment_id,
                                              "Status"] = new_status
                flash("success", f"Payment {payment_id} is now '{new_status}'.")
                bump_form_version()
                st.rerun()

    with tab_summary:
        balances = build_balance_table(reservations, payments)
        balances.insert(2, "Guest Name", balances["Guest ID"].map(guest_names))
        st.markdown("**Outstanding balances per reservation**")
        show_table(balances, money_cols=["Total Cost", "Paid", "Outstanding"], status_col="Status")
        st.markdown("**Revenue by payment method** (only payments with status 'Paid')")
        by_method = (payments[payments["Status"] == "Paid"].groupby("Method")["Amount"]
                     .agg(["count", "sum"]).reset_index())
        by_method.columns = ["Method", "Payments", "Revenue"]
        if by_method.empty:
            st.info("No paid payments yet.")
        else:
            by_method["Share %"] = (100 * by_method["Revenue"] / by_method["Revenue"].sum()).round(1)
            left, right = st.columns([1, 1])
            with left:
                show_table(by_method, money_cols=["Revenue"])
            with right:
                show_chart(chart_payment_methods(payments), True)


# ----------------------------------------------------------------- Staff ----

def page_staff():
    render_header("Staff", "Manage employees, job titles, salaries and employment status")
    tab_list, tab_add, tab_update = st.tabs(["📋 Staff List", "➕ Add Staff", "✏️ Update Staff"])
    staff = st.session_state.staff

    with tab_list:
        active = staff[staff["Status"] == "Active"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total staff", len(staff))
        m2.metric("Active staff", len(active))
        m3.metric("Monthly payroll (active)", money(active["Salary"].sum()))
        filtered = apply_controls(staff, "staff", ["Staff ID", "Full Name", "Job Title", "Phone"],
                                  filter_cols={"Status": STAFF_STATUSES})
        st.caption(f"Showing {len(filtered)} of {len(staff)} staff members")
        show_table(filtered, money_cols=["Salary"], status_col="Status")
        delete_panel("staff", "Staff ID", "staff")

    with tab_add:
        with st.form(vkey("staff_form")):
            col1, col2 = st.columns(2)
            staff_id = col1.text_input("Staff ID", value=next_id(staff, "Staff ID", "STF", 3), key=vkey("st_id"))
            name = col2.text_input("Full name", key=vkey("st_name"))
            col3, col4 = st.columns(2)
            title = col3.text_input("Job title", key=vkey("st_title"))
            phone = col4.text_input("Phone number", key=vkey("st_phone"))
            col5, col6 = st.columns(2)
            salary = col5.number_input("Monthly salary", min_value=0.0, value=800.0, step=50.0,
                                       format="%.2f", key=vkey("st_salary"))
            status = col6.selectbox("Employment status", STAFF_STATUSES, key=vkey("st_status"))
            submitted = st.form_submit_button("Add staff member", type="primary")

        if submitted:
            errors = []
            if not staff_id.strip():
                errors.append("Staff ID is required.")
            elif staff_id.strip() in set(staff["Staff ID"]):
                errors.append(f"Staff ID {staff_id.strip()} already exists.")
            if len(name.strip()) < 2:
                errors.append("Please enter the staff member's full name.")
            if not title.strip():
                errors.append("Job title is required.")
            if not is_valid_phone(phone):
                errors.append("Phone number must contain 7-20 digits (you may use +, spaces, - and brackets).")
            if salary <= 0:
                errors.append("Salary must be greater than zero.")
            if errors:
                for error in errors:
                    st.error(error)
            else:
                append_row("staff", {"Staff ID": staff_id.strip(), "Full Name": name.strip(),
                                     "Job Title": title.strip(), "Phone": phone.strip(),
                                     "Salary": float(salary), "Status": status})
                flash("success", f"Staff member {name.strip()} ({staff_id.strip()}) was added.")
                bump_form_version()
                st.rerun()

    with tab_update:
        if staff.empty:
            st.info("There are no staff members yet.")
        else:
            staff_id = st.selectbox("Staff member", staff["Staff ID"].tolist(), key=vkey("su_id"))
            person = staff[staff["Staff ID"] == staff_id].iloc[0]
            col1, col2, col3 = st.columns(3)
            new_title = col1.text_input("Job title", value=person["Job Title"], key=vkey(f"su_title_{staff_id}"))
            new_salary = col2.number_input("Monthly salary", min_value=0.0, value=float(person["Salary"]),
                                           step=50.0, format="%.2f", key=vkey(f"su_salary_{staff_id}"))
            new_status = col3.selectbox("Status", STAFF_STATUSES, index=STAFF_STATUSES.index(person["Status"]),
                                        key=vkey(f"su_status_{staff_id}"))
            if st.button("Save changes", type="primary", key=vkey("su_save")):
                if not new_title.strip():
                    st.error("Job title is required.")
                elif new_salary <= 0:
                    st.error("Salary must be greater than zero.")
                else:
                    mask = st.session_state.staff["Staff ID"] == staff_id
                    st.session_state.staff.loc[mask, ["Job Title", "Salary", "Status"]] = [
                        new_title.strip(), float(new_salary), new_status]
                    flash("success", f"{person['Full Name']} was updated.")
                    bump_form_version()
                    st.rerun()


# --------------------------------------------------------------- Reports ----

def occupancy_by_room_type(rooms, reservations, start, end):
    """Booked room-nights versus available room-nights per room type for a date range."""
    days = (end - start).days + 1
    type_of_room = dict(zip(rooms["Room Number"], rooms["Room Type"]))
    booked = {}
    for _, res in reservations[reservations["Status"] != "Cancelled"].iterrows():
        room_type = type_of_room.get(res["Room Number"])
        if room_type:
            booked[room_type] = booked.get(room_type, 0) + nights_in_range(
                res["Check-In"], res["Check-Out"], start, end)
    rows = []
    for room_type in ROOM_TYPES:
        room_count = int((rooms["Room Type"] == room_type).sum())
        available_nights = room_count * days
        booked_nights = booked.get(room_type, 0)
        rows.append({
            "Room Type": room_type, "Rooms": room_count,
            "Available Room-Nights": available_nights, "Booked Room-Nights": booked_nights,
            "Occupancy %": round(100 * booked_nights / available_nights, 1) if available_nights else 0.0,
        })
    return pd.DataFrame(rows)


def page_reports():
    render_header("Reports", "Filter by date range and download tables as CSV files")
    today = date.today()
    period = st.date_input("Report period (start and end date)",
                           value=(today - timedelta(days=90), today + timedelta(days=30)), key="report_period")
    if not (isinstance(period, (tuple, list)) and len(period) == 2):
        st.info("Please pick both a start date and an end date.")
        return
    start, end = period
    stamp = f"{start}_to_{end}"

    rooms = st.session_state.rooms
    reservations = st.session_state.reservations
    payments = st.session_state.payments

    in_range_res = reservations[(reservations["Check-In"] >= start) & (reservations["Check-In"] <= end)]
    in_range_pay = payments[(payments["Payment Date"] >= start) & (payments["Payment Date"] <= end)]
    paid_in_range = in_range_pay[in_range_pay["Status"] == "Paid"]
    occupancy = occupancy_by_room_type(rooms, reservations, start, end)
    total_available = occupancy["Available Room-Nights"].sum()
    overall_rate = round(100 * occupancy["Booked Room-Nights"].sum() / total_available, 1) if total_available else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reservations starting", len(in_range_res))
    m2.metric("Booking value", money(in_range_res.loc[in_range_res["Status"] != "Cancelled", "Total Cost"].sum()))
    m3.metric("Payments received", money(paid_in_range["Amount"].sum()))
    m4.metric("Occupancy rate", f"{overall_rate}%")

    summary = pd.DataFrame({
        "Metric": ["Period start", "Period end", "Reservations starting", "Cancelled reservations",
                   "Booking value (non-cancelled)", "Payments received (Paid)", "Occupancy rate %"],
        "Value": [str(start), str(end), len(in_range_res), int((in_range_res["Status"] == "Cancelled").sum()),
                  round(float(in_range_res.loc[in_range_res["Status"] != "Cancelled", "Total Cost"].sum()), 2),
                  round(float(paid_in_range["Amount"].sum()), 2), overall_rate],
    })

    tabs = st.tabs(["📝 Summary", "📅 Reservations", "💳 Payments", "💰 Revenue by Method",
                    "🛏️ Occupancy", "🗂️ Master Data"])

    with tabs[0]:
        show_table(summary)
        csv_download("summary report", summary, f"summary_report_{stamp}.csv", "dl_summary")

    with tabs[1]:
        names = reservations_with_names()
        table = names[(names["Check-In"] >= start) & (names["Check-In"] <= end)]
        show_table(table, money_cols=["Total Cost"], status_col="Status")
        csv_download("reservations", table, f"reservations_{stamp}.csv", "dl_res")

    with tabs[2]:
        show_table(in_range_pay, money_cols=["Amount"], status_col="Status")
        csv_download("payments", in_range_pay, f"payments_{stamp}.csv", "dl_pay")

    with tabs[3]:
        by_method = paid_in_range.groupby("Method")["Amount"].agg(["count", "sum"]).reset_index()
        by_method.columns = ["Method", "Payments", "Revenue"]
        if by_method.empty:
            st.info("No paid payments in this period.")
        else:
            show_table(by_method, money_cols=["Revenue"])
            csv_download("revenue by method", by_method, f"revenue_by_method_{stamp}.csv", "dl_method")

    with tabs[4]:
        show_table(occupancy)
        csv_download("occupancy report", occupancy, f"occupancy_{stamp}.csv", "dl_occ")

    with tabs[5]:
        st.caption("Full copies of the master tables (not filtered by date).")
        for label, name in [("guests", "guests"), ("rooms", "rooms"), ("staff", "staff")]:
            csv_download(label, st.session_state[name], f"{label}.csv", f"dl_{name}")


# =============================================================================
# 8. SIDEBAR AND MAIN ENTRY POINT
# =============================================================================

def render_sidebar():
    """Sidebar navigation plus the data-reset tool. Returns the selected page name."""
    with st.sidebar:
        st.markdown(f"## 🏨 {APP_TITLE}")
        page = st.radio("Navigation", PAGES, label_visibility="collapsed")
        st.divider()
        st.caption("⚠️ Data is stored in session memory only and is lost when the session resets "
                   "or the deployed app restarts.")
        with st.expander("⚙️ Data options"):
            st.caption("Restore the original sample data and discard all changes.")
            confirmed = st.checkbox("I want to reset all data.", key=vkey("reset_confirm"))
            if st.button("Reset to sample data", disabled=not confirmed, key=vkey("reset_button")):
                load_sample_data()
                flash("success", "Sample data was restored.")
                bump_form_version()
                st.rerun()
    return page


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🏨", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_state()
    page = render_sidebar()

    routes = {
        "📊 Dashboard": page_dashboard,
        "👥 Guests": page_guests,
        "🛏️ Rooms": page_rooms,
        "📅 Reservations": page_reservations,
        "💳 Payments": page_payments,
        "🧑‍💼 Staff": page_staff,
        "📑 Reports": page_reports,
    }
    try:
        routes[page]()
    except Exception as error:  # show a friendly message instead of a crash
        st.error(f"Something went wrong: {error}")
        st.caption("Try another page, or use 'Reset to sample data' in the sidebar.")


main()
