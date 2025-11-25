# scripts/prepare_db.py
import pandas as pd
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "bankdata.db"

def read_data():
    customers = pd.read_csv( "customers.csv")
    accounts = pd.read_csv("accounts.csv")
    transactions = pd.read_csv( "transactions.csv", parse_dates=["txn_time"])
    loans = pd.read_json( "loans.json")
    credit_cards = pd.read_json( "credit_cards.json")
    branches = pd.read_json( "branches_fixed.json")
    support = pd.read_json("support_tickets.json")
    return customers, accounts, transactions, loans, credit_cards, branches, support

def simple_clean(df):
    # Drop exact duplicate rows, strip strings, basic null fill for demo
    df = df.copy()
    df = df.drop_duplicates()
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()
    return df

def main():
    customers, accounts, transactions, loans, credit_cards, branches, support = read_data()

    customers = simple_clean(customers)
    accounts = simple_clean(accounts)
    transactions = simple_clean(transactions)
    loans = simple_clean(loans)
    credit_cards = simple_clean(credit_cards)
    branches = simple_clean(branches)
    support = simple_clean(support)

    conn = sqlite3.connect(DB_PATH)
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    accounts.to_sql("accounts", conn, if_exists="replace", index=False)
    transactions.to_sql("transactions", conn, if_exists="replace", index=False)
    loans.to_sql("loans", conn, if_exists="replace", index=False)
    credit_cards.to_sql("credit_cards", conn, if_exists="replace", index=False)
    branches.to_sql("branches", conn, if_exists="replace", index=False)
    support.to_sql("support_tickets", conn, if_exists="replace", index=False)

    print("✅ Data written to", DB_PATH)

if __name__ == "__main__":
    main()
