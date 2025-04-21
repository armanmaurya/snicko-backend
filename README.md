# 📦 RentX — Peer-to-Peer Rental Platform

**Rent smarter, not harder.**  
A Django-powered app that lets you rent and lend items locally — from calculators to power tools — without the hassle of ownership.

---

## 🚀 Features

✅ List your idle items for rent  
✅ Rent anything you need, when you need it  
✅ Upload pickup & return photos for trust and transparency  
✅ Secure booking system with deposit handling  
✅ User ratings, categories, and damage dispute management

---

## 🛠 Tech Stack

| Layer     | Tech                     |
|-----------|--------------------------|
| Backend   | Django, Django REST API  |
| Database  | PostgreSQL / SQLite      |
| Media     | Django Media Storage     |
| Frontend  | Flutter / React (optional) |

---

## 📸 Core Models

- **Item**: Rentable objects (with image & condition)
- **Booking**: Handles availability, status, pickup & return photos
- **Category**: Organizes listings
- **Damage Report**: Handles disputes with photo evidence

---

## ⚙️ Setup

```bash
git clone https://github.com/yourusername/rentx.git
cd rentx
python -m venv venv
source venv/bin/activate   # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
