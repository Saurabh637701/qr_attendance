# 📌 QR Attendance System

A **Django-based Attendance Management System** that uses **QR codes** for marking student attendance. Teachers can generate subject-wise QR codes, and students can scan them to mark their presence securely.

---

## 🚀 Features

* Teacher can **add subjects & students**.
* Generate **QR codes** for each subject/session.
* Students can scan QR & mark attendance.
* Live attendance dashboard for faculty.
* Secure validation with **date & time checks**.
* Simple UI with templates for different views.

---

## 🛠️ Tech Stack

* **Backend:** Django (Python)
* **Database:** SQLite (default)
* **Frontend:** HTML, CSS, JavaScript
* **Libraries:**

  * `qrcode`
  * `Pillow`
  * `Django`

---

## 📂 Project Structure (important files)

```
qr_attendance/
│-- manage.py
│-- db.sqlite3
│-- requirements.txt
│
│-- qr_app/
│   │-- admin.py
│   │-- apps.py
│   │-- forms.py
│   │-- models.py
│   │-- urls.py
│   │-- views.py
│   │-- static/
│   │   ├── css/style.css
│   │   ├── js/script.js
│   │   └── images/
│   │-- templates/
│       ├── home.html
│       ├── dashboard.html
│       ├── attendance_stu.html
│       ├── attendance_faculty.html
│       └── ...
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone <your-repo-link>
cd qr_attendance
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run Migrations

```bash
python manage.py migrate
```

### 5️⃣ Create Superuser (for admin access)

```bash
python manage.py createsuperuser
```

### 6️⃣ Run Development Server

```bash
python manage.py runserver
```

Visit: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 📸 Screenshots

(Add screenshots here)

* 🏠 Home Page
* 🎓 Student Attendance Page
* 👨‍🏫 Faculty Dashboard

---

## 📌 Future Improvements

* Add **email/SMS notifications** for attendance.
* Export attendance reports in **CSV/PDF**.
* Add **role-based authentication** (Student/Faculty/Admin).

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📜 License

This project is licensed under the **MIT License**.
