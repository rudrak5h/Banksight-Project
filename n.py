# app/streamlit_app.py
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, date

# ---------------------------
# Streamlit config (must be first Streamlit command)
# ---------------------------
st.set_page_config(page_title="BankSight Dashboard", layout="wide", page_icon="🏦")

DB_PATH = Path(__file__).resolve().parents[1] / "bankdata.db"

# ---------------------------
# Utilities
# ---------------------------
@st.cache_data
def get_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=True)
    conn.close()
    return df

def run_sql(sql, params=(), parse_dates=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(sql, conn, params=params, parse_dates=parse_dates)
    finally:
        conn.close()
    return df

def exec_sql(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

def table_has_column(table, col):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
        cols = [r[1] for r in rows]
        return col in cols
    except Exception:
        return False
    finally:
        conn.close()

def get_key_col(table):
    key_map = {
        "customers": "customer_id",
        "accounts": "customer_id",
        "transactions": "txn_id",
        "loans": "Loan_ID",
        "branches": "Branch_ID",
        "support_tickets": "Ticket_ID"
    }
    return key_map.get(table, None)

def get_table_columns(table):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
        return [r[1] for r in rows]
    finally:
        conn.close()

# ---------------------------
# Sidebar / Navigation
# ---------------------------
st.sidebar.markdown("## 📊 BankSight Navigation")
st.sidebar.markdown("**Go to:**")

page = st.sidebar.radio(
    "",
    [
        "🏠 Introduction",
        "📋 View Tables",
        "🔎 Filter Data",
        "✏️ CRUD Operations",
        "💳 Credit / Debit Simulation",
        "🧠 Analytical Insights",
        "👨‍💻 About Creator"
    ]
)

# ---------------------------
# Pages
# ---------------------------
def page_intro():
    st.markdown("<h1 style='font-size:42px;'>🏦 BankSight: Transaction Intelligence Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("""
    ### Project Overview
    **BankSight** is a financial analytics demo built with **Python**, **Streamlit**, and **SQLite**.
    It provides tooling to explore customers, accounts, transactions, loans, credit-cards and support tickets,
    perform simple CRUD operations, simulate deposits/withdrawals, and run SQL-driven analytical queries.
    """)

    st.markdown("### Objectives")
    st.markdown("""
    - Understand customer & transaction behavior  
    - Detect anomalies and potential fraud signals  
    - Enable fast prototyping of analytics and reporting  
    - Provide a reproducible demo for data engineering and BI workflows
    """)

def page_view_tables():
    st.header("📋 View Database Tables")
    table = st.selectbox("Select a table:", ["customers", "accounts", "transactions", "loans", "credit_cards", "branches", "support_tickets"])
    df = get_table(table)
    st.write(f"### Showing `{table}` ({len(df)} rows)")
    st.dataframe(df, use_container_width=True)

def page_filter():
    st.header("🔎 Filter Data")
    table = st.selectbox("Choose a table to filter:", ["customers","accounts","transactions","loans","credit_cards","branches","support_tickets"], key="filter_table")
    df = get_table(table)
    st.write(f"### {table} — {len(df)} rows")

    columns = st.multiselect("Columns to display:", df.columns.tolist(), default=df.columns.tolist()[:6])
    st.subheader("Filters (text contains)")
    filters = {}
    for col in columns:
        user_input = st.text_input(f"Filter **{col}**:", "", key=f"f_{table}_{col}")
        if user_input.strip():
            filters[col] = user_input

    filtered = df.copy()
    for col, val in filters.items():
        filtered = filtered[filtered[col].astype(str).str.contains(val, case=False, na=False)]

    st.dataframe(filtered[columns], use_container_width=True)

# ---------------------------
# CRUD
# ---------------------------
def page_crud():
    st.header("✏️ CRUD Operations")
    st.write("Select Table and Operation (View / Add / Update / Delete)")

    tables_supported = ["customers", "accounts", "transactions", "loans", "branches", "support_tickets"]
    table = st.selectbox("Select Table", tables_supported, index=0)
    op = st.radio("Select Operation", ["View", "Add", "Update", "Delete"], index=0, horizontal=False)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if op == "View":
        df = pd.read_sql(f"SELECT * FROM {table} LIMIT 1000", conn, parse_dates=True)
        st.dataframe(df, use_container_width=True)

    elif op == "Add":
        st.subheader(f"Add row to `{table}`")
        cols = get_table_columns(table)
        with st.form(f"add_{table}_form"):
            values = {}
            for col in cols:
                if col in ("Branch_ID","Loan_ID","Card_ID"):
                    st.write(f"**{col}** (auto-managed - leave blank if auto-increment)")
                    values[col] = ""
                    continue
                if "date" in col.lower() or col.lower().endswith("_date") or col.lower().startswith("issued"):
                    values[col] = st.date_input(col)
                elif col.lower().endswith("_id") or col.lower().endswith("id") or "name" in col.lower() or "type" in col.lower() or "status" in col.lower() or col.lower()=="city" or col.lower()=="gender":
                    values[col] = st.text_input(col)
                elif "amount" in col.lower() or "balance" in col.lower() or "rate" in col.lower():
                    values[col] = st.number_input(col, value=0.0, format="%.2f")
                elif "age" in col.lower() or "employees" in col.lower() or col.lower().endswith("_months") or col.lower().endswith("_term"):
                    values[col] = st.number_input(col, value=0, step=1)
                else:
                    values[col] = st.text_input(col)
            submitted = st.form_submit_button("Add Row")
            if submitted:
                try:
                    insert_cols = [c for c in cols if not (c in ("Branch_ID","Loan_ID","Card_ID") and values.get(c,"")== "")]
                    insert_vals = []
                    for c in insert_cols:
                        v = values[c]
                        if isinstance(v, (pd.Timestamp, datetime, date)):
                            v = str(v)
                        insert_vals.append(v if v != "" else None)
                    placeholders = ",".join(["?"] * len(insert_cols))
                    cols_sql = ",".join(insert_cols)
                    sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})"
                    cur.execute(sql, tuple(insert_vals))
                    conn.commit()
                    st.success("Row added!")
                except Exception as e:
                    st.error("Error adding row: " + str(e))

    elif op == "Update":
        st.subheader(f"Update row in `{table}` (single-column update)")
        key_col = get_key_col(table)
        if not key_col:
            st.error("No key column configured for this table.")
        else:
            key_val = st.text_input(f"Enter {key_col} to update")
            col_to_update = st.text_input("Column to update (exact column name)")
            new_val = st.text_input("New value (string form)")
            if st.button("Apply Update"):
                try:
                    sql = f"UPDATE {table} SET {col_to_update} = ? WHERE {key_col} = ?"
                    cur.execute(sql, (new_val, key_val))
                    conn.commit()
                    st.success("Update applied (if row existed).")
                except Exception as e:
                    st.error("Error: " + str(e))

    elif op == "Delete":
        st.subheader(f"Delete row from `{table}`")
        key_col = get_key_col(table)
        if not key_col:
            st.error("No key column configured for this table.")
        else:
            key_val = st.text_input(f"Enter {key_col} to delete")
            if st.button("Delete"):
                try:
                    cur.execute(f"DELETE FROM {table} WHERE {key_col} = ?", (key_val,))
                    conn.commit()
                    st.success("Deleted (if existed).")
                except Exception as e:
                    st.error("Error: " + str(e))

    conn.close()

# ---------------------------
# Deposit / Withdraw
# ---------------------------
def page_credit_sim():
    st.header("💰 Deposit / Withdraw Money (by customer_id)")
    st.write("Use `customer_id` as account key (your accounts table maps balances by customer).")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    customer_id = st.text_input("Enter customer_id (e.g. C0001)")
    amount = st.number_input("Enter Amount (₹)", min_value=0.0, format="%.2f")
    action = st.radio("Select Action", ["Check Balance", "Deposit", "Withdraw"])
    if st.button("Submit"):
        try:
            cur.execute("SELECT account_balance FROM accounts WHERE customer_id = ?", (customer_id,))
            row = cur.fetchone()
            if not row:
                st.error("Account (customer_id) not found.")
            else:
                balance = row[0] if row[0] is not None else 0.0
                if action == "Check Balance":
                    st.success(f"Current balance for {customer_id}: ₹{float(balance):,.2f}")
                elif action == "Deposit":
                    new_balance = float(balance) + float(amount)
                    cur.execute(
                        "UPDATE accounts SET account_balance = ?, last_updated = ? WHERE customer_id = ?",
                        (new_balance, datetime.utcnow().isoformat(), customer_id),
                    )
                    try:
                        cur.execute(
                            "INSERT INTO transactions (txn_id, customer_id, txn_type, amount, txn_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                f"txn_{int(datetime.utcnow().timestamp())}",
                                customer_id,
                                "deposit",
                                float(amount),
                                datetime.utcnow().isoformat(),
                                "success",
                            ),
                        )
                    except Exception:
                        pass
                    conn.commit()
                    st.success(f"Deposited ₹{amount:.2f}. New balance: ₹{new_balance:.2f}")
                else:  # Withdraw
                    if float(amount) > float(balance):
                        st.error("Insufficient funds.")
                    else:
                        new_balance = float(balance) - float(amount)
                        cur.execute(
                            "UPDATE accounts SET account_balance = ?, last_updated = ? WHERE customer_id = ?",
                            (new_balance, datetime.utcnow().isoformat(), customer_id),
                        )
                        try:
                            cur.execute(
                                "INSERT INTO transactions (txn_id, customer_id, txn_type, amount, txn_time, status) VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    f"txn_{int(datetime.utcnow().timestamp())}",
                                    customer_id,
                                    "withdraw",
                                    float(amount),
                                    datetime.utcnow().isoformat(),
                                    "success",
                                ),
                            )
                        except Exception:
                            pass
                        conn.commit()
                        st.success(f"Withdrawn ₹{amount:.2f}. New balance: ₹{new_balance:.2f}")
        except Exception as e:
            st.error("Error: " + str(e))

    conn.close()

# ---------------------------
# Analytical Insights (UPDATED to teacher's new questions)
# ---------------------------
def page_analytics():
    st.header("🧠 Analytical Insights")
    st.write("Select a question from the dropdown (Q1–Q15). Results will run and show below. (SQL is hidden for simplicity.)")

    q_text = st.selectbox("Select a question to run:", [
        "Q1: How many customers exist per city, and what is their average account balance?",
        "Q2: Which account type (Savings, Current, Loan, etc.) holds the highest total balance?",
        "Q3: Who are the top 10 customers by total account balance across all account types?",
        "Q4: Which customers opened accounts in 2023 with a balance above ₹1,00,000?",
        "Q5: What is the total transaction volume (sum of amounts) by transaction type?",
        "Q6: How many failed transactions occurred for each transaction type?",
        "Q7: What is the total number of transactions per transaction type?",
        "Q8: Which accounts have 5 or more high-value transactions above ₹20,000?",
        "Q9: What is the average loan amount and interest rate by loan type (Personal, Auto, Home, etc.)?",
        "Q10: Which customers currently hold more than one active or approved loan?",
        "Q11: Who are the top 5 customers with the highest outstanding (non-closed) loan amounts?",
        "Q12: What is the average loan amount per branch?",
        "Q13: How many customers exist in each age group (e.g., 18–25, 26–35, etc.)?",
        "Q14: Which issue categories have the longest average resolution time?",
        "Q15: Which support agents have resolved the most critical tickets with high customer ratings (≥4)?"
    ])

    # Extract question number exactly, e.g. "Q11"
    q_num = q_text.split(":")[0].strip()

    # helpers
    def safe_run(sql, params=(), parse_dates=None, success_title=None):
        try:
            df = run_sql(sql, params=params, parse_dates=parse_dates)
            if df is None:
                st.info("Query returned nothing.")
                return None
            st.write(f"### Result — {len(df)} rows" + (f" — {success_title}" if success_title else ""))
            st.dataframe(df, use_container_width=True)
            return df
        except Exception as e:
            st.error("Query failed: " + str(e))
            return None

    # Q1: customers per city & avg account balance
    if q_num == "Q1":
        sql = """
            SELECT c.city,
                   COUNT(DISTINCT c.customer_id) AS num_customers,
                   ROUND(AVG(COALESCE(a.account_balance,0)),2) AS avg_balance
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            GROUP BY c.city
            ORDER BY num_customers DESC;
        """
        safe_run(sql)

    # Q2: account type with highest total balance
    elif q_num == "Q2":
        # prefer accounts.account_type, fallback to customers.account_type if present
        if table_has_column("accounts", "account_type"):
            sql = """
                SELECT account_type, SUM(COALESCE(account_balance,0)) AS total_balance
                FROM accounts
                GROUP BY account_type
                ORDER BY total_balance DESC;
            """
        elif table_has_column("customers", "account_type"):
            sql = """
                SELECT account_type, SUM(COALESCE(a.account_balance,0)) AS total_balance
                FROM customers c
                LEFT JOIN accounts a ON c.customer_id = a.customer_id
                GROUP BY account_type
                ORDER BY total_balance DESC;
            """
        else:
            st.error("No account_type column found in accounts or customers tables.")
            sql = None
        if sql:
            safe_run(sql)

    # Q3: top 10 customers by total account balance across all account types
    elif q_num == "Q3":
        sql = """
            SELECT a.customer_id,
                   COALESCE(c.name, a.customer_id) AS name,
                   ROUND(SUM(COALESCE(a.account_balance,0)),2) AS total_balance
            FROM accounts a
            LEFT JOIN customers c ON a.customer_id = c.customer_id
            GROUP BY a.customer_id
            ORDER BY total_balance DESC
            LIMIT 10;
        """
        safe_run(sql)

    # Q4: customers who opened accounts in 2023 with balance > 100000
    elif q_num == "Q4":
        # Try to detect an account open date column first (common names)
        open_date_cols = [col for col in ("open_date","opened_date","account_open_date","created_at","created_on","join_date") if table_has_column("accounts", col) or table_has_column("customers", col)]
        # prefer accounts.open_date if exists
        if table_has_column("accounts", "open_date"):
            sql = """
                SELECT a.customer_id, COALESCE(c.name,a.customer_id) AS name, a.account_balance, a.open_date
                FROM accounts a
                LEFT JOIN customers c ON a.customer_id = c.customer_id
                WHERE substr(COALESCE(a.open_date,''),1,4) = '2023'
                  AND COALESCE(a.account_balance,0) > 100000
                ORDER BY a.account_balance DESC;
            """
        elif table_has_column("customers", "join_date"):
            sql = """
                SELECT a.customer_id, COALESCE(c.name,a.customer_id) AS name, a.account_balance, c.join_date
                FROM accounts a
                LEFT JOIN customers c ON a.customer_id = c.customer_id
                WHERE substr(COALESCE(c.join_date,''),1,4) = '2023'
                  AND COALESCE(a.account_balance,0) > 100000
                ORDER BY a.account_balance DESC;
            """
        else:
            # generic fallback: check any date-like column presence in accounts/customers
            sql = """
                SELECT a.customer_id, COALESCE(c.name,a.customer_id) AS name, a.account_balance,
                       COALESCE(a.open_date, c.join_date, '') AS date_candidate
                FROM accounts a
                LEFT JOIN customers c ON a.customer_id = c.customer_id
                WHERE substr(COALESCE(a.open_date, c.join_date, ''),1,4) = '2023'
                  AND COALESCE(a.account_balance,0) > 100000
                ORDER BY a.account_balance DESC;
            """
        safe_run(sql)

    # Q5: total transaction volume (sum of amounts) by transaction type
    elif q_num == "Q5":
        sql = """
            SELECT COALESCE(txn_type, 'UNKNOWN') AS txn_type,
                   ROUND(SUM(COALESCE(amount,0)),2) AS total_amount,
                   COUNT(*) AS txn_count
            FROM transactions
            GROUP BY txn_type
            ORDER BY total_amount DESC;
        """
        safe_run(sql)

    # Q6: how many failed transactions occurred for each transaction type
    elif q_num == "Q6":
        if not table_has_column("transactions", "status") or not table_has_column("transactions", "txn_type"):
            st.warning("transactions.status or transactions.txn_type column not found; cannot compute failed counts by type.")
        else:
            sql = """
                SELECT COALESCE(txn_type,'UNKNOWN') AS txn_type,
                       COUNT(*) AS failed_count
                FROM transactions
                WHERE lower(COALESCE(status,'')) = 'failed'
                GROUP BY txn_type
                ORDER BY failed_count DESC;
            """
            safe_run(sql)

    # Q7: total number of transactions per transaction type
    elif q_num == "Q7":
        if not table_has_column("transactions", "txn_type"):
            st.warning("transactions.txn_type column not found.")
        else:
            sql = """
                SELECT COALESCE(txn_type,'UNKNOWN') AS txn_type,
                       COUNT(*) AS txn_count,
                       ROUND(SUM(COALESCE(amount,0)),2) AS total_amount
                FROM transactions
                GROUP BY txn_type
                ORDER BY txn_count DESC;
            """
            safe_run(sql)

    # Q8: accounts with 5 or more high-value transactions above ₹20,000
    elif q_num == "Q8":
        threshold = 20000.0
        min_count = 5
        # prefer account_id column in transactions, otherwise fall back to customer_id
        if table_has_column("transactions", "account_id"):
            id_col = "account_id"
        elif table_has_column("transactions", "customer_id"):
            id_col = "customer_id"
        else:
            st.error("transactions table does not have account_id or customer_id column to group by.")
            id_col = None

        if id_col:
            sql = f"""
                SELECT {id_col} AS account_or_customer,
                       COUNT(*) AS high_txn_count,
                       ROUND(SUM(COALESCE(amount,0)),2) AS sum_high_amounts
                FROM transactions
                WHERE COALESCE(amount,0) > {float(threshold)}
                GROUP BY {id_col}
                HAVING high_txn_count >= {int(min_count)}
                ORDER BY high_txn_count DESC, sum_high_amounts DESC;
            """
            df = run_sql(sql)
            if df is not None and len(df) > 0:
                st.write(f"### Result — {len(df)} rows (threshold ₹{threshold:,.0f}, min {min_count} txns)")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No accounts matched the criteria.")

    # Q9: average loan amount and interest rate by loan type
    elif q_num == "Q9":
        # try common column names
        loan_amount_col = "Loan_Amount" if table_has_column("loans", "Loan_Amount") else ("Amount" if table_has_column("loans", "Amount") else None)
        interest_col = "Interest_Rate" if table_has_column("loans", "Interest_Rate") else ("Interest" if table_has_column("loans", "Interest") else None)
        loan_type_col = "Loan_Type" if table_has_column("loans", "Loan_Type") else ("Type" if table_has_column("loans", "Type") else None)

        if loan_amount_col and interest_col and loan_type_col:
            sql = f"""
                SELECT {loan_type_col} AS loan_type,
                       ROUND(AVG(COALESCE({loan_amount_col},0)),2) AS avg_loan_amount,
                       ROUND(AVG(COALESCE({interest_col},0)),2) AS avg_interest_rate,
                       COUNT(*) AS n_loans
                FROM loans
                GROUP BY {loan_type_col}
                ORDER BY avg_loan_amount DESC;
            """
            safe_run(sql)
        else:
            st.error("Required columns for loans not found (Loan_Amount, Interest_Rate, Loan_Type).")

    # Q10: customers with more than one active or approved loan
    elif q_num == "Q10":
        # try Loan_Status name variants
        status_col = "Loan_Status" if table_has_column("loans", "Loan_Status") else ("Status" if table_has_column("loans", "Status") else None)
        cust_col = "Customer_ID" if table_has_column("loans", "Customer_ID") else ("customer_id" if table_has_column("loans", "customer_id") else None)
        if not cust_col:
            st.error("No customer id column found in loans table.")
        else:
            if status_col:
                sql = f"""
                    SELECT {cust_col} AS customer_id, COUNT(*) AS num_active_loans
                    FROM loans
                    WHERE {status_col} IN ('Active','Approved')
                    GROUP BY {cust_col}
                    HAVING num_active_loans > 1
                    ORDER BY num_active_loans DESC;
                """
            else:
                sql = f"""
                    SELECT {cust_col} AS customer_id, COUNT(*) AS num_loans
                    FROM loans
                    GROUP BY {cust_col}
                    HAVING num_loans > 1
                    ORDER BY num_loans DESC;
                """
            safe_run(sql)

    # Q11: top 5 customers with highest outstanding (non-closed) loan amounts
    elif q_num == "Q11":
        # prefer Loan_Status column and Loan_Amount, Customer_ID
        loan_amount_col = "Loan_Amount" if table_has_column("loans", "Loan_Amount") else ("Amount" if table_has_column("loans", "Amount") else None)
        cust_col = "Customer_ID" if table_has_column("loans", "Customer_ID") else ("customer_id" if table_has_column("loans", "customer_id") else None)
        status_col = "Loan_Status" if table_has_column("loans", "Loan_Status") else ("Status" if table_has_column("loans", "Status") else None)

        if loan_amount_col and cust_col:
            if status_col:
                sql = f"""
                    SELECT l.{cust_col} AS customer_id,
                           COALESCE(c.name, l.{cust_col}) AS name,
                           ROUND(SUM(COALESCE(l.{loan_amount_col},0)),2) AS outstanding_amount
                    FROM loans l
                    LEFT JOIN customers c ON CAST(l.{cust_col} AS TEXT) = c.customer_id
                    WHERE lower(COALESCE(l.{status_col},'')) NOT LIKE '%closed%'
                    GROUP BY l.{cust_col}
                    ORDER BY outstanding_amount DESC
                    LIMIT 5;
                """
            else:
                sql = f"""
                    SELECT l.{cust_col} AS customer_id,
                           COALESCE(c.name, l.{cust_col}) AS name,
                           ROUND(SUM(COALESCE(l.{loan_amount_col},0)),2) AS outstanding_amount
                    FROM loans l
                    LEFT JOIN customers c ON CAST(l.{cust_col} AS TEXT) = c.customer_id
                    GROUP BY l.{cust_col}
                    ORDER BY outstanding_amount DESC
                    LIMIT 5;
                """
            safe_run(sql)
        else:
            st.error("Required loan columns not found (Loan_Amount, Customer_ID).")

    # Q12: average loan amount per branch
    elif q_num == "Q12":
        # detect branch column name and loan amount
        branch_col = None
        if table_has_column("loans", "Branch"):
            branch_col = "Branch"
        elif table_has_column("loans", "Branch_ID"):
            branch_col = "Branch_ID"

        loan_amount_col = "Loan_Amount" if table_has_column("loans", "Loan_Amount") else ("Amount" if table_has_column("loans", "Amount") else None)

        if branch_col and loan_amount_col:
            sql = f"""
                SELECT {branch_col} AS branch,
                       ROUND(AVG(COALESCE({loan_amount_col},0)),2) AS avg_loan_amount,
                       COUNT(*) AS n_loans
                FROM loans
                GROUP BY {branch_col}
                ORDER BY avg_loan_amount DESC
                LIMIT 50;
            """
            safe_run(sql)
        else:
            st.error("Required columns for computing average loan per branch not found (Branch/Branch_ID and Loan_Amount).")

    # Q13: customers by age group
    elif q_num == "Q13":
        # prefer customers.age; else try to compute from dob/date_of_birth
        if table_has_column("customers", "age"):
            sql = """
                SELECT
                  CASE
                    WHEN age BETWEEN 18 AND 25 THEN '18-25'
                    WHEN age BETWEEN 26 AND 35 THEN '26-35'
                    WHEN age BETWEEN 36 AND 45 THEN '36-45'
                    WHEN age BETWEEN 46 AND 60 THEN '46-60'
                    WHEN age > 60 THEN '60+'
                    ELSE 'Unknown'
                  END AS age_group,
                  COUNT(*) AS num_customers
                FROM customers
                GROUP BY age_group
                ORDER BY num_customers DESC;
            """
            safe_run(sql)
        elif table_has_column("customers", "dob") or table_has_column("customers", "date_of_birth"):
            dob_col = "dob" if table_has_column("customers", "dob") else "date_of_birth"
            # compute age relative to today using SQLite (strftime + julianday)
            sql = f"""
                SELECT
                  CASE
                    WHEN age BETWEEN 18 AND 25 THEN '18-25'
                    WHEN age BETWEEN 26 AND 35 THEN '26-35'
                    WHEN age BETWEEN 36 AND 45 THEN '36-45'
                    WHEN age BETWEEN 46 AND 60 THEN '46-60'
                    WHEN age > 60 THEN '60+'
                    ELSE 'Unknown'
                  END AS age_group,
                  COUNT(*) AS num_customers
                FROM (
                  SELECT {dob_col},
                         CAST((strftime('%Y', 'now') - substr({dob_col},1,4)) - (strftime('%m-%d','now') < substr({dob_col},6,5)) AS INTEGER) AS age
                  FROM customers
                  WHERE {dob_col} IS NOT NULL AND trim({dob_col}) <> ''
                )
                GROUP BY age_group
                ORDER BY num_customers DESC;
            """
            safe_run(sql)
        else:
            st.error("No age or date-of-birth column found in customers table to compute age groups.")

    # Q14: issue categories with longest average resolution time
    elif q_num == "Q14":
        # use Date_Opened and Date_Closed columns (common names)
        if table_has_column("support_tickets", "Date_Opened") and table_has_column("support_tickets", "Date_Closed"):
            sql = """
                SELECT Issue_Category,
                       ROUND(AVG(JULIANDAY(Date_Closed) - JULIANDAY(Date_Opened)),2) AS avg_resolution_days,
                       COUNT(*) AS n_tickets
                FROM support_tickets
                WHERE Date_Closed IS NOT NULL AND trim(Date_Closed) <> ''
                GROUP BY Issue_Category
                ORDER BY avg_resolution_days DESC;
            """
            safe_run(sql)
        else:
            st.error("Support tickets do not have Date_Opened / Date_Closed columns.")

    # Q15: support agents who resolved most critical tickets with high customer ratings (>=4)
    elif q_num == "Q15":
        # detect columns
        if not table_has_column("support_tickets", "Priority") or not table_has_column("support_tickets", "Customer_Rating") or not table_has_column("support_tickets", "Support_Agent"):
            st.error("Required support_tickets columns not found (Priority, Customer_Rating, Support_Agent).")
        else:
            sql = """
                SELECT Support_Agent,
                       COUNT(*) AS critical_resolved_count,
                       ROUND(AVG(COALESCE(Customer_Rating,0)),2) AS avg_rating
                FROM support_tickets
                WHERE Priority = 'Critical' AND Customer_Rating >= 4 AND Status IN ('Resolved','Closed')
                GROUP BY Support_Agent
                ORDER BY critical_resolved_count DESC
                LIMIT 10;
            """
            safe_run(sql)

def page_about():
    st.header("👨‍💻 About the Creator")

    st.write("### BankSight Dashboard")
    st.write("Made with ❤️ using Python & Streamlit.")

    st.write("---")

    st.subheader("Creator Info")
    st.write("**👤 Name:** Rudraksh")
    st.write("**📧 Email:** rudrakshdr@gmail.com")
    st.write("**🐙 GitHub:** https://github.com/rudrak5h")

    st.write("---")



# ---------------------------
# Router
# ---------------------------
if page == "🏠 Introduction":
    page_intro()
elif page == "📋 View Tables":
    page_view_tables()
elif page == "🔎 Filter Data":
    page_filter()
elif page == "✏️ CRUD Operations":
    page_crud()
elif page == "💳 Credit / Debit Simulation":
    page_credit_sim()
elif page == "🧠 Analytical Insights":
    page_analytics()
elif page == "👨‍💻 About Creator":
    page_about()
