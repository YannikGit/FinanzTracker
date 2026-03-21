import pandas as pd
from core.models import classify

def to_dataframe(transactions):
    df = pd.DataFrame(transactions)
    df["amount"] = df["amount"].round(2)  # clean any floating point noise
    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["month_name"] = df["date"].dt.strftime("%B")
    df["type"] = df["amount"].apply(classify)
    return df

def filter_ausgaben(df):
    return df[df["type"] == "Ausgabe"]

def filter_einnahmen(df):
    return df[df["type"] == "Einnahme"]

def summary_by_store(df):
    return df.groupby("store")["amount"].sum().sort_values()

def summary_by_month(df):
    return df.groupby("month")["amount"].sum().sort_values()

def to_transactions_list(df):
    cols_to_save = ["store", "amount", "date", "category"]
    # Convert date back to string for JSON storage
    df = df.copy()
    df["date"] = df["date"].dt.strftime("%d.%m.%Y")
    return df[cols_to_save].to_dict(orient="records")


