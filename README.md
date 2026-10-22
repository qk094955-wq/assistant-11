# assistant-11# 🏨 Grand Haven Hotel Manager

A beginner-friendly **Hotel Management Dashboard** built with Python and [Streamlit](https://streamlit.io).
It manages **Guests, Rooms, Reservations, Payments and Staff** in one clean, responsive web app, with
interactive charts and downloadable CSV reports.

The whole project is just **three files**:

| File               | Purpose                                   |
| ------------------ | ----------------------------------------- |
| `app.py`           | The complete application                  |
| `requirements.txt` | Python libraries needed to run it         |
| `README.md`        | This documentation                        |

> ⚠️ **Important:** there is no database. Data is held in Streamlit *session state* (memory).
> It is **lost when the browser session ends, the page is refreshed in a new session, or the deployed app restarts or goes to sleep**.
> Use the CSV downloads on the **Reports** page to keep copies.

---

## ✨ Features

- **Dashboard** – metric cards (guests, rooms, available/occupied rooms, active reservations, payments received, estimated revenue, outstanding balance), five interactive charts, and upcoming arrivals/departures.
- **Guests** – add guests (ID, name, phone, email, address), search, sort, and delete with confirmation.
- **Rooms** – add rooms, filter by type or status, update price or maintenance status. Room status is automatic: a room becomes *Occupied* while a guest is checked in.
- **Reservations** – pick a guest and room, choose dates, see nights and total cost calculated automatically, check room availability, and track status (*Confirmed → Checked In → Checked Out*, or *Cancelled*). Invalid dates and overlapping bookings are blocked.
- **Payments** – record payments (ID, reservation, amount, method, date, status), see outstanding balances, block overpayments, and view revenue by payment method.
- **Staff** – manage staff IDs, names, job titles, phone numbers, salaries and employment status.
- **Reports** – date-range filter with summary, reservations, payments, revenue-by-method, occupancy and master-data tables, each downloadable as CSV.
- **Quality touches** – form validation, success/error messages, confirmation before deleting, sample data that never conflicts, and a "Reset to sample data" button.

### How the numbers are calculated

- **Payments received** = sum of payments with status *Paid* (Pending, Failed and Refunded are not counted).
- **Estimated revenue** = total cost of all reservations that are not *Cancelled*.
- **Outstanding balance** = reservation total cost − paid amount (cancelled reservations owe nothing).
- **Occupied rooms** = rooms with a *Checked In* reservation. **Available rooms** = rooms that are neither occupied nor in maintenance.

---

## 📋 Prerequisites

- **Python 3.9 or newer** ([download](https://www.python.org/downloads/))
- **pip** (included with Python)
- A free **GitHub** account and a free **Streamlit Community Cloud** account (only for online deployment)
- Optional: **Git** installed on your computer

---

## 💻 Installation and Local Execution

1. **Create a project folder** and place `app.py`, `requirements.txt` and `README.md` inside it.
2. **Open a terminal** in that folder.
3. *(Recommended)* **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```
4. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the app**:
   ```bash
   streamlit run app.py
   ```
6. Your browser opens at `http://localhost:8501`. Press `Ctrl + C` in the terminal to stop it.

---

## 🐙 GitHub Repository Setup

1. Sign in to [github.com](https://github.com) and click **New repository**.
2. Name it (for example `hotel-management-dashboard`), keep it **Public** (the free Streamlit Cloud plan works best with public repositories), and click **Create repository**.
3. **Upload the files** in either way:
   - *Browser:* click **Add file → Upload files**, drag in `app.py`, `requirements.txt` and `README.md`, then **Commit changes**.
   - *Command line:*
     ```bash
     git init
     git add app.py requirements.txt README.md
     git commit -m "Add hotel management dashboard"
     git branch -M main
     git remote add origin https://github.com/YOUR-USERNAME/hotel-management-dashboard.git
     git push -u origin main
     ```
4. Make sure the three files are in the **root** of the repository (not inside a sub-folder).

---

## ☁️ Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
2. Click **Create app** (or **New app**) and choose **Deploy a public app from GitHub**.
3. Select your **repository**, the **branch** (`main`) and set **Main file path** to `app.py`.
4. *(Optional)* choose a custom subdomain under **App URL**.
5. Click **Deploy**. Streamlit installs the libraries from `requirements.txt` and starts the app. This takes a few minutes the first time.
6. Share the generated link. Whenever you push changes to GitHub, the app updates automatically.

---

## 📦 Dependencies

| Library    | Why it is used                                  |
| ---------- | ----------------------------------------------- |
| `streamlit`| Web interface, forms, navigation, state         |
| `pandas`   | Tables, filtering, grouping, CSV export         |
| `plotly`   | Interactive charts                              |

All are free and open source. No paid APIs, AI models, authentication services or databases are needed.

---

## 🚧 Limitations

- **No permanent storage:** data lives in session memory and disappears when the session resets or the hosted app restarts or sleeps.
- Each visitor gets their own separate copy of the data; nothing is shared between users.
- No login or user roles; anyone with the link can use the app.
- Single currency (change `CURRENCY` at the top of `app.py`).
- Records can be added, deleted and have selected fields updated, but not every field is editable.

## 🔮 Future Improvements

- Connect a free database (SQLite, Supabase or Google Sheets) for permanent storage.
- Add user login and roles (manager, receptionist).
- Edit all fields of every record and add an audit log.
- Seasonal pricing, discounts, taxes and invoice PDFs.
- Email or SMS booking confirmations.
- Housekeeping schedules and staff attendance tracking.
- Import data from CSV files.

---

## 🛠️ Customising

- Change hotel name, currency, room types and statuses in the **configuration section** at the top of `app.py`.
- Edit `build_sample_data()` to change the starting demo records.

Happy coding! 🎉
