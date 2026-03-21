import pandas as pd
from core.models import classify

def to_dataframe(transactions, apply_reimbursements=True):
    """
    Convert transactions list to DataFrame.
    If apply_reimbursements=True, uses effective amounts.
    """
    if not transactions:
        return None

    from core.reimbursement_manager import get_effective_amount

    df = pd.DataFrame(transactions)
    df["amount"] = df["amount"].round(2)
    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["type"] = df["amount"].apply(classify)

    if apply_reimbursements:
        # Add effective amount column
        df["effective_amount"] = df.apply(
            lambda row: get_effective_amount(row.to_dict()), axis=1
        )
        df["effective_amount"] = df["effective_amount"].round(2)
    else:
        df["effective_amount"] = df["amount"]

    # Add reimbursement status columns with defaults
    if "reimbursement_status" not in df.columns:
        df["reimbursement_status"] = None
    if "reimbursement_amount" not in df.columns:
        df["reimbursement_amount"] = None
    if "reimbursed_by" not in df.columns:
        df["reimbursed_by"] = None
    if "reimburses" not in df.columns:
        df["reimburses"] = None

    return df

def filter_ausgaben(df):
    return df[df["type"] == "Ausgabe"]

def filter_einnahmen(df):
    return df[df["type"] == "Einnahme"]

def summary_by_store(df):
    return df.groupby("store")["effective_amount"].sum().sort_values()

def summary_by_month(df):
    return df.groupby("month")["effective_amount"].sum().sort_values()