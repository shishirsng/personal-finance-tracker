# 💰 Personal Finance Tracker API & Frontend

A complete, beginner-friendly, and production-ready Personal Finance Tracker with a **FastAPI** backend and an interactive **Streamlit** frontend.

---

## 📁 Project Overview
- **Backend API (`app/`)**: High-performance REST API built with FastAPI, PostgreSQL / SQLite, SQLAlchemy 2.0 async, Redis, and ARQ background worker.
- **Frontend App (`frontend.py`)**: Clean and intuitive Streamlit dashboard to create accounts, log transactions, set budgets, and view visual analytics.
- **Virtual Environment (`.venv/`)**: Isolated environment with all dependencies installed.

---

## 🚀 Quickstart Guide (Step-by-Step)

### Step 1: Open Terminal in Project Folder
Open PowerShell or Command Prompt and navigate to this folder:
```powershell
cd "C:\Users\Shishir Singh\Desktop\personal-finance-tracker"
```

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### Step 3: Run the FastAPI Backend
Start the backend server on port 8000:
```powershell
uvicorn app.main:app --reload --port 8000
```
- Interactive API Docs (Swagger UI): **http://localhost:8000/docs**
- Health Probe: **http://localhost:8000/health/live**
- Prometheus Metrics: **http://localhost:8000/metrics**

### Step 4: Run the Streamlit Frontend (In a New Terminal)
Open a second terminal window, navigate to the same folder, activate `.venv`, and start Streamlit:
```powershell
cd "C:\Users\Shishir Singh\Desktop\personal-finance-tracker"
.\.venv\Scripts\Activate.ps1
streamlit run frontend.py
```
Streamlit will automatically launch in your browser at:
👉 **http://localhost:8501**

---

## 🖥️ Using the Streamlit Frontend

1. **🔐 Login & Register**:
   - Go to the **Create New Account** tab.
   - Enter your name, email, and password to register.
   - Switch to the **Log In** tab and sign in.
2. **💳 Accounts**:
   - Add your checking, savings, cash, or credit accounts.
3. **🏷️ Categories**:
   - Create income categories (e.g. *Salary*, *Freelance*) and expense categories (e.g. *Groceries*, *Rent*, *Dining*).
4. **💸 Transactions**:
   - Record income or expenses.
   - Check *Enable Idempotency Token* to prevent duplicate submissions over flaky networks.
   - View your interactive transaction history table.
5. **🎯 Monthly Budgets**:
   - Select a month (`YYYY-MM`, e.g. `2026-11`).
   - Assign budget targets to your expense categories.
6. **📊 Reports & Analytics**:
   - Real-time monthly summary (Total Income, Total Expense, Net Savings, Savings Rate).
   - Visual progress bars comparing **Budget vs. Actual Spending**.
   - Spending breakdown bar chart by category.

---

## 🧪 Running the Tests
To run the automated test suite with pytest:
```powershell
pytest -v
```

---

## 🐳 Optional: Running with Docker Compose
If you have Docker Desktop installed, you can spin up PostgreSQL 16, Redis 7, the FastAPI app, and the ARQ worker in one command:
```powershell
docker-compose up --build -d
```
All database tables and migrations will be applied automatically!
