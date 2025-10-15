# 💰 Personal Finance Tracker

A web-based personal finance management application built with Django. Track your income, expenses, budgets, and savings goals all in one beautiful, intuitive interface.

## ✨ Features

### 📊 Dashboard

* **Financial Overview**: Display of total balance, income, and expenses
* **Interactive Charts**: Visual representation of spending trends and category breakdowns using Chart.js
* **Recent Transactions**: Quick access to your latest financial activities
* **Budget Progress**: Visual indicators showing how you're tracking against your budgets
* **Savings Goals**: Monitor progress towards your financial objectives

### 💸 Transaction Management

* **Comprehensive Tracking**: Record all income and expense transactions
* **Advanced Filtering**: Filter by date range, category, and type
* **Bulk Operations**: Import, and export transactions
* **Pagination**: Efficiently browse through large transaction histories

### 🏷️ Category Management

* **Custom Categories**: Create personalized income and expense categories
* **Visual Organization**: Assign icons and colors to each category
* **Transaction Analytics**: View total transactions and amounts per category

### 💼 Budget Planning

* **Flexible Budgets**: Set budgets by category
* **Tracking**: Monitor spending against budget limits
* **Visual Progress**: Color-coded progress bars (green, yellow, red)
* **Budget Alerts**: Alerts when approaching or exceeding limits
* **Performance Charts**: Compare budgeted vs actual spending

### 🎯 Savings Goals

* **Goal Setting**: Define savings targets with deadlines
* **Progress Tracking**: Visual progress bars showing completion percentage
* **Quick Contributions**: Add money with preset amount buttons
* **Achievement Tracking**: Celebrate when goals are reached

### 🔐 User Authentication

* **Secure Login**: Protected user authentication system
* **User Registration**: Easy account creation with validation
* **Password Security**: Encrypted password storage
* **Session Management**: Secure session handling

### ⚙️ Settings & Customization

* **Theme Options**: Light and dark mode support

## 🛠️ Technologies Used

### Backend

* **Django 5.0**: Python web framework for robust backend development
* **Python 3.13+**: Modern Python for clean, efficient code
* **SQLite**: Database for data persistence
* **Django ORM**: Object-relational mapping for database operations

### Frontend

* **HTML5/CSS3**: Modern web standards
* **Bootstrap 5.1**: Responsive UI framework
* **JavaScript (ES6+)**: Interactive client-side functionality
* **Chart.js**: Beautiful, responsive charts and graphs
* **Font Awesome 6.0**: Comprehensive icon library

### Additional Libraries

* **django-mathfilters**: Advanced math filters
* **python-dateutil**: Advanced date handling

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
* **Python 3.13 or higher**
* **uv** - Fast Python package installer and resolver

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/WorldChallenge1/personal-finance-tracker.git
cd personal-finance-tracker
```

### 2. Create Virtual Environment and Install Dependencies

Using `uv` for ultra-fast dependency installation:

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
# Create database tables
python manage.py makemigrations
python manage.py migrate

# or using uv
uv run manage.py makemigrations
uv run manage.py migrate
```

### 4. Create a Superuser

```bash
# Create an admin account
python manage.py createsuperuser

# or using uv
uv run manage.py createsuperuser
```

Follow the prompts to set up your admin username, email, and password.

### 5. Run the Development Server

```bash
# Start the Django development server
python manage.py runserver

# or using uv
uv run manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your web browser.

### 6. Running docker-compose

```bash
docker-compose up -d
```

### 7. Access Admin Panel

Visit `http://127.0.0.1:8000/admin/` and log in with your superuser credentials.
