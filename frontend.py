"""Personal Finance Tracker - Simple Beginner-Friendly Streamlit Frontend.

Connects to the FastAPI backend running at http://localhost:8000.
"""

from datetime import datetime, timezone
import uuid
import requests
import streamlit as st

# Configure page
st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None


def get_headers():
    """Build Authorization headers if logged in."""
    headers = {"Content-Type": "application/json"}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    return headers


def handle_error_response(response):
    """Extract human-readable error from standard envelope."""
    try:
        data = response.json()
        if "error" in data:
            err = data["error"]
            return f"Error {response.status_code}: {err.get('message', 'Unknown error')} ({err.get('code', '')})"
        return f"Error {response.status_code}: {response.text}"
    except Exception:
        return f"Error {response.status_code}: {response.text}"


# Check backend liveness
backend_online = False
try:
    health_res = requests.get(f"{st.session_state.api_url}/health/live", timeout=1.5)
    if health_res.status_code == 200:
        backend_online = True
except Exception:
    backend_online = False

# Sidebar Navigation
st.sidebar.title("💰 Finance Tracker")

api_base = st.sidebar.text_input("Backend API URL", value=st.session_state.api_url)
st.session_state.api_url = api_base.rstrip("/")

if backend_online:
    st.sidebar.success("🟢 Backend Connected", icon="✅")
else:
    st.sidebar.error("🔴 Backend Offline")
    st.sidebar.caption("Run `run_backend.bat` or `uvicorn app.main:app --port 8000` to start it.")

if not backend_online:
    st.error(
        "🚨 **FastAPI Backend is Offline!**\n\n"
        "Streamlit cannot reach the backend server at `" + st.session_state.api_url + "`.\n\n"
        "**To start the backend:**\n"
        "1. Open a new terminal in this folder:\n"
        "   ```powershell\n"
        "   cd 'C:\\Users\\Shishir Singh\\OneDrive\\Desktop\\personal-finance-tracker'\n"
        "   .\\.venv\\Scripts\\Activate.ps1\n"
        "   uvicorn app.main:app --port 8000 --reload\n"
        "   ```\n"
        "2. Or simply double-click **`run_backend.bat`** (or **`run_all.bat`**)."
    )

if st.session_state.current_user:
    st.sidebar.info(
        f"Logged in as: **{st.session_state.current_user.get('full_name')}**\n\n"
        f"📧 {st.session_state.current_user.get('email')}\n\n"
        f"Role: `{st.session_state.current_user.get('role')}`"
    )
    if st.sidebar.button("Logout", key="logout_btn"):
        if st.session_state.refresh_token:
            try:
                requests.post(
                    f"{st.session_state.api_url}/api/v1/auth/logout",
                    json={"refresh_token": st.session_state.refresh_token},
                    timeout=3,
                )
            except Exception:
                pass
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.current_user = None
        st.rerun()

menu = st.sidebar.radio(
    "Navigation",
    ["🔐 Login & Register", "💳 Accounts", "🏷️ Categories", "💸 Transactions", "🎯 Budgets", "📊 Reports"],
)

# ----------------------------------------------------
# 1. AUTHENTICATION (LOGIN & REGISTER)
# ----------------------------------------------------
if menu == "🔐 Login & Register":
    st.header("🔐 User Authentication")
    st.caption("Register an account or log in to generate your secure JWT session token.")

    tab_login, tab_register = st.tabs(["Log In", "Create New Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.warning("Please fill in both email and password.")
                else:
                    try:
                        res = requests.post(
                            f"{st.session_state.api_url}/api/v1/auth/login",
                            json={"username": email.strip(), "password": password},
                            timeout=5,
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.access_token = data["access_token"]
                            st.session_state.refresh_token = data["refresh_token"]
                            st.session_state.current_user = {"email": email, "full_name": email.split("@")[0], "role": "user"}
                            st.success("Successfully logged in! You can now use the navigation menu.")
                            st.rerun()
                        else:
                            st.error(handle_error_response(res))
                    except requests.exceptions.ConnectionError:
                        st.error(
                            "❌ Connection refused: Could not reach the backend at "
                            f"{st.session_state.api_url}. Please ensure the FastAPI backend is running on port 8000."
                        )
                    except Exception as e:
                        st.error(f"Failed to connect to server: {e}")

    with tab_register:
        with st.form("register_form"):
            reg_name = st.text_input("Full Name", placeholder="Jane Doe")
            reg_email = st.text_input("Email Address", placeholder="jane@example.com")
            reg_pass = st.text_input("Password (min 8 chars)", type="password")
            reg_submitted = st.form_submit_button("Register", use_container_width=True)

            if reg_submitted:
                if not reg_name or not reg_email or not reg_pass:
                    st.warning("Please complete all fields.")
                elif len(reg_pass) < 8:
                    st.warning("Password must be at least 8 characters long.")
                else:
                    try:
                        res = requests.post(
                            f"{st.session_state.api_url}/api/v1/auth/register",
                            json={"full_name": reg_name.strip(), "email": reg_email.strip(), "password": reg_pass},
                            timeout=5,
                        )
                        if res.status_code == 201:
                            st.success("Account registered successfully! Please switch to the Log In tab.")
                        else:
                            st.error(handle_error_response(res))
                    except requests.exceptions.ConnectionError:
                        st.error(
                            "❌ Connection refused: Could not reach the backend at "
                            f"{st.session_state.api_url}. Please ensure the FastAPI backend is running on port 8000."
                        )
                    except Exception as e:
                        st.error(f"Registration request failed: {e}")

# Helper check for protected tabs
elif not st.session_state.access_token:
    st.info("👋 Welcome! Please log in or register via the **'🔐 Login & Register'** tab to view your personal finance data.")

# ----------------------------------------------------
# 2. ACCOUNTS
# ----------------------------------------------------
elif menu == "💳 Accounts":
    st.header("💳 Financial Accounts")
    st.caption("Manage checking, savings, credit card, and cash accounts.")

    with st.expander("➕ Create New Account", expanded=False):
        with st.form("create_account_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                acc_name = st.text_input("Account Name", placeholder="e.g. Chase Main Checking")
            with col2:
                acc_type = st.selectbox("Account Type", ["checking", "savings", "credit", "cash"])
            with col3:
                currency = st.text_input("Currency (ISO code)", value="USD", max_chars=3)
            acc_submit = st.form_submit_button("Create Account")

            if acc_submit:
                if not acc_name:
                    st.warning("Account name is required.")
                else:
                    try:
                        res = requests.post(
                            f"{st.session_state.api_url}/api/v1/accounts",
                            headers=get_headers(),
                            json={"name": acc_name.strip(), "type": acc_type, "currency": currency.upper()},
                        )
                        if res.status_code == 201:
                            st.success(f"Account '{acc_name}' created successfully!")
                            st.rerun()
                        else:
                            st.error(handle_error_response(res))
                    except Exception as e:
                        st.error(f"Request failed: {e}")

    # List Accounts
    try:
        res = requests.get(f"{st.session_state.api_url}/api/v1/accounts?limit=50", headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            accounts = data.get("items", [])
            if not accounts:
                st.info("No accounts created yet. Expand the box above to add your first account!")
            else:
                for acc in accounts:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                        c1.markdown(f"**{acc['name']}**")
                        c2.markdown(f"Type: `{acc['type'].title()}` | Currency: `{acc['currency']}`")
                        stale_badge = "💤 Stale (>90d inactive)" if acc.get("is_stale") else "⚡ Active"
                        c3.markdown(f"Status: {stale_badge}")
                        if c4.button("Delete", key=f"del_acc_{acc['id']}"):
                            del_res = requests.delete(
                                f"{st.session_state.api_url}/api/v1/accounts/{acc['id']}",
                                headers=get_headers(),
                            )
                            if del_res.status_code == 204:
                                st.success("Account deleted.")
                                st.rerun()
                            else:
                                st.error(handle_error_response(del_res))
    except Exception as e:
        st.error(f"Could not load accounts: {e}")

# ----------------------------------------------------
# 3. CATEGORIES
# ----------------------------------------------------
elif menu == "🏷️ Categories":
    st.header("🏷️ Transaction Categories")
    st.caption("Organize your income streams and expense categories.")

    with st.expander("➕ Add New Category", expanded=False):
        with st.form("create_cat_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                cat_name = st.text_input("Category Name", placeholder="e.g. Groceries, Rent, Salary")
            with col2:
                cat_kind = st.selectbox("Category Kind", ["expense", "income"])
            with col3:
                cat_color = st.color_picker("Color Tag", "#3498DB")
            cat_submit = st.form_submit_button("Add Category")

            if cat_submit:
                if not cat_name:
                    st.warning("Category name cannot be empty.")
                else:
                    try:
                        res = requests.post(
                            f"{st.session_state.api_url}/api/v1/categories",
                            headers=get_headers(),
                            json={"name": cat_name.strip(), "kind": cat_kind, "color": cat_color.upper()},
                        )
                        if res.status_code == 201:
                            st.success(f"Category '{cat_name}' added!")
                            st.rerun()
                        else:
                            st.error(handle_error_response(res))
                    except Exception as e:
                        st.error(f"Request failed: {e}")

    try:
        res = requests.get(f"{st.session_state.api_url}/api/v1/categories", headers=get_headers())
        if res.status_code == 200:
            categories = res.json()
            if not categories:
                st.info("No categories configured. Add your first category above!")
            else:
                col_inc, col_exp = st.columns(2)
                with col_inc:
                    st.subheader("💵 Income Categories")
                    for cat in [c for c in categories if c["kind"] == "income"]:
                        with st.container(border=True):
                            st.markdown(f"🏷️ **{cat['name']}** (Color: `{cat['color'] or 'None'}`)")
                            if st.button("Delete", key=f"del_cat_{cat['id']}"):
                                requests.delete(f"{st.session_state.api_url}/api/v1/categories/{cat['id']}", headers=get_headers())
                                st.rerun()

                with col_exp:
                    st.subheader("🛒 Expense Categories")
                    for cat in [c for c in categories if c["kind"] == "expense"]:
                        with st.container(border=True):
                            st.markdown(f"🏷️ **{cat['name']}** (Color: `{cat['color'] or 'None'}`)")
                            if st.button("Delete", key=f"del_cat_{cat['id']}"):
                                requests.delete(f"{st.session_state.api_url}/api/v1/categories/{cat['id']}", headers=get_headers())
                                st.rerun()
    except Exception as e:
        st.error(f"Could not load categories: {e}")

# ----------------------------------------------------
# 4. TRANSACTIONS
# ----------------------------------------------------
elif menu == "💸 Transactions":
    st.header("💸 Financial Transactions")
    st.caption("Record new income and expense entries with idempotency protection.")

    accounts = []
    categories = []
    try:
        accs_res = requests.get(f"{st.session_state.api_url}/api/v1/accounts?limit=100", headers=get_headers())
        cats_res = requests.get(f"{st.session_state.api_url}/api/v1/categories", headers=get_headers())
        accounts = accs_res.json().get("items", []) if accs_res.status_code == 200 else []
        categories = cats_res.json() if cats_res.status_code == 200 else []
    except Exception as e:
        st.error(f"Could not load accounts or categories: {e}")

    if not accounts:
        st.warning("⚠️ You must create at least one Account before logging transactions.")
    else:
        with st.expander("➕ Log New Transaction", expanded=False):
            with st.form("tx_form"):
                c1, c2, c3 = st.columns(3)
                acc_options = {acc["name"]: acc["id"] for acc in accounts}
                cat_options = {"(Uncategorized)": None}
                for c in categories:
                    cat_options[f"{c['name']} ({c['kind']})"] = c["id"]

                with c1:
                    sel_acc = st.selectbox("Select Account", list(acc_options.keys()))
                with c2:
                    tx_direction = st.selectbox("Direction", ["expense", "income"])
                with c3:
                    sel_cat = st.selectbox("Category (Optional)", list(cat_options.keys()))

                c4, c5, c6 = st.columns(3)
                with c4:
                    amount_input = st.number_input("Amount ($)", min_value=0.01, step=1.00, value=25.00, format="%.2f")
                with c5:
                    description = st.text_input("Memo / Description", placeholder="e.g. Supermarket Grocery")
                with c6:
                    use_idempotency = st.checkbox("Enable Idempotency Token", value=True)

                tx_submit = st.form_submit_button("Record Transaction")

                if tx_submit:
                    payload = {
                        "account_id": acc_options[sel_acc],
                        "category_id": cat_options[sel_cat],
                        "amount": f"{amount_input:.2f}",
                        "direction": tx_direction,
                        "description": description.strip() if description else None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                    }
                    headers = get_headers()
                    if use_idempotency:
                        headers["Idempotency-Key"] = str(uuid.uuid4())

                    try:
                        res = requests.post(f"{st.session_state.api_url}/api/v1/transactions", headers=headers, json=payload)
                        if res.status_code == 201:
                            st.success(f"Transaction of ${amount_input:.2f} recorded!")
                            st.rerun()
                        else:
                            st.error(handle_error_response(res))
                    except Exception as e:
                        st.error(f"Transaction failed: {e}")

    # List Recent Transactions
    st.subheader("Recent Transaction Log")
    try:
        tx_res = requests.get(f"{st.session_state.api_url}/api/v1/transactions?limit=25", headers=get_headers())
        if tx_res.status_code == 200:
            tx_data = tx_res.json()
            tx_list = tx_data.get("items", [])
            if not tx_list:
                st.info("No transactions logged yet.")
            else:
                table_rows = []
                for t in tx_list:
                    cat_label = t["category"]["name"] if t.get("category") else "Uncategorized"
                    sign = "+" if t["direction"] == "income" else "-"
                    table_rows.append({
                        "Date (UTC)": t["occurred_at"][:10],
                        "Amount": f"{sign}${float(t['amount']):,.2f}",
                        "Direction": t["direction"].upper(),
                        "Category": cat_label,
                        "Description": t["description"] or "-",
                    })
                st.dataframe(table_rows, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load transactions: {e}")

# ----------------------------------------------------
# 5. BUDGETS
# ----------------------------------------------------
elif menu == "🎯 Budgets":
    st.header("🎯 Monthly Category Budgets")
    st.caption("Define monthly spending targets per category.")

    current_month = datetime.now().strftime("%Y-%m")
    selected_month = st.text_input("Target Month (YYYY-MM)", value=current_month, max_chars=7)

    categories = []
    try:
        cats_res = requests.get(f"{st.session_state.api_url}/api/v1/categories?kind=expense", headers=get_headers())
        categories = cats_res.json() if cats_res.status_code == 200 else []
    except Exception as e:
        st.error(f"Could not load categories: {e}")

    if not categories:
        st.warning("⚠️ Please create at least one Expense Category before setting budgets.")
    else:
        with st.expander("➕ Set Category Budget Target", expanded=False):
            with st.form("budget_form"):
                cat_dict = {c["name"]: c["id"] for c in categories}
                b_cat = st.selectbox("Category", list(cat_dict.keys()))
                b_amount = st.number_input("Budget Amount ($)", min_value=0.00, value=500.00, step=50.00, format="%.2f")
                b_submit = st.form_submit_button("Save Budget")

                if b_submit:
                    cat_id = cat_dict[b_cat]
                    try:
                        res = requests.put(
                            f"{st.session_state.api_url}/api/v1/budgets/{cat_id}?month={selected_month}",
                            headers=get_headers(),
                            json={"amount": f"{b_amount:.2f}"},
                        )
                        if res.status_code == 200:
                            st.success(f"Budget of ${b_amount:.2f} set for {b_cat} in {selected_month}!")
                            st.rerun()
                        else:
                            st.error(handle_error_response(res))
                    except Exception as e:
                        st.error(f"Budget update failed: {e}")

        # Show existing budgets
        try:
            b_list_res = requests.get(f"{st.session_state.api_url}/api/v1/budgets?month={selected_month}", headers=get_headers())
            if b_list_res.status_code == 200:
                budgets = b_list_res.json()
                if not budgets:
                    st.info(f"No budgets defined for {selected_month}.")
                else:
                    for b in budgets:
                        cname = b["category"]["name"] if b.get("category") else "Unknown"
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([4, 4, 2])
                            c1.markdown(f"🎯 **{cname}**")
                            c2.markdown(f"Budget Limit: **${float(b['amount']):,.2f}**")
                            if c3.button("Delete", key=f"del_b_{b['id']}"):
                                requests.delete(f"{st.session_state.api_url}/api/v1/budgets/{b['id']}", headers=get_headers())
                                st.rerun()
        except Exception as e:
            st.error(f"Could not load budgets: {e}")

# ----------------------------------------------------
# 6. REPORTS & ANALYTICS
# ----------------------------------------------------
elif menu == "📊 Reports":
    st.header("📊 Financial Reports & Analytics")
    st.caption("Review monthly summaries, spending breakdown charts, and budget progress.")

    current_month = datetime.now().strftime("%Y-%m")
    rep_month = st.text_input("Report Month (YYYY-MM)", value=current_month, max_chars=7)

    # 1. Monthly Summary
    try:
        sum_res = requests.get(f"{st.session_state.api_url}/api/v1/reports/monthly-summary?month={rep_month}", headers=get_headers())
        if sum_res.status_code == 200:
            summary = sum_res.json()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Income", f"${float(summary['total_income']):,.2f}")
            m2.metric("Total Expense", f"${float(summary['total_expense']):,.2f}")
            net = float(summary["net_savings"])
            m3.metric("Net Savings", f"${net:,.2f}", delta=f"{summary['savings_rate']}% Saved")
            m4.metric("Savings Rate", f"{summary['savings_rate']}%")
    except Exception as e:
        st.error(f"Could not load summary: {e}")

    st.divider()

    # 2. Budget vs Actual
    st.subheader(f"🎯 Budget vs Actual Spending ({rep_month})")
    try:
        bva_res = requests.get(f"{st.session_state.api_url}/api/v1/reports/budget-vs-actual?month={rep_month}", headers=get_headers())
        if bva_res.status_code == 200:
            bva = bva_res.json()
            items = bva.get("items", [])
            if not items:
                st.info("No budgets or categorized spending found for this month.")
            else:
                for item in items:
                    b_amt = float(item["budgeted_amount"])
                    a_amt = float(item["actual_amount"])
                    pct = float(item["percentage_used"])
                    col_a, col_b = st.columns([3, 7])
                    with col_a:
                        st.write(f"**{item['category_name']}**")
                        st.caption(f"Spent ${a_amt:,.2f} of ${b_amt:,.2f} ({pct:.1f}%)")
                    with col_b:
                        progress_val = min(max(pct / 100.0, 0.0), 1.0)
                        st.progress(progress_val)
                        if a_amt > b_amt and b_amt > 0:
                            st.caption(f"⚠️ Over budget by ${a_amt - b_amt:,.2f}")
    except Exception as e:
        st.error(f"Could not load budget vs actual: {e}")

    st.divider()

    # 3. Category Breakdown Chart
    st.subheader(f"🛒 Expense Breakdown by Category ({rep_month})")
    try:
        bk_res = requests.get(f"{st.session_state.api_url}/api/v1/reports/category-breakdown?month={rep_month}&direction=expense", headers=get_headers())
        if bk_res.status_code == 200:
            breakdown = bk_res.json()
            cat_items = breakdown.get("items", [])
            if cat_items:
                chart_data = {item["category_name"]: float(item["total_amount"]) for item in cat_items}
                st.bar_chart(chart_data)
            else:
                st.info("No expense transactions recorded in this month.")
    except Exception as e:
        st.error(f"Could not load breakdown: {e}")
