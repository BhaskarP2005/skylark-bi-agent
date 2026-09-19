import os
import pandas as pd
from dotenv import load_dotenv
from monday_client import get_board_items, get_board_columns
from normalizer import normalize_text, normalize_date, normalize_amount, normalize_sector, data_quality_report

load_dotenv()

# Columns that should be treated as dates
DATE_COLUMNS = [
    "Data Delivery Date", "Date of PO/LOI", "Probable Start Date", "Probable End Date",
    "Last invoice date", "Collection Date", "Close Date (A)", "Tentative Close Date",
    "Created Date",
]

# Columns that should be treated as monetary amounts
AMOUNT_COLUMNS = [
    "Amount in Rupees (Excl of GST) (Masked)", "Amount in Rupees (Incl of GST) (Masked)",
    "Billed Value in Rupees (Excl of GST.) (Masked)", "Billed Value in Rupees (Incl of GST.) (Masked)",
    "Collected Amount in Rupees (Incl of GST.) (Masked)",
    "Amount to be billed in Rs. (Exl. of GST) (Masked)", "Amount to be billed in Rs. (Incl. of GST) (Masked)",
    "Amount Receivable (Masked)", "Masked Deal value",
]

# Columns that represent a sector/category (normalize casing)
SECTOR_COLUMNS = ["Sector", "Sector/service"]


def board_to_dataframe(board_id: str) -> pd.DataFrame:
    columns_map = get_board_columns(board_id)
    items = get_board_items(board_id)

    rows = []
    for item in items:
        row = {"Item Name": item["name"]}
        for cv in item["column_values"]:
            title = columns_map.get(cv["id"], cv["id"])
            row[title] = cv["text"]
        rows.append(row)

    return pd.DataFrame(rows)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalization rules to known column types; leave others as trimmed text."""
    df = df.copy()
    for col in df.columns:
        if col in DATE_COLUMNS:
            df[col] = df[col].apply(normalize_date)
        elif col in AMOUNT_COLUMNS:
            df[col] = df[col].apply(normalize_amount)
        elif col in SECTOR_COLUMNS:
            df[col] = df[col].apply(normalize_sector)
        else:
            df[col] = df[col].apply(normalize_text)
    return df


def load_work_orders() -> pd.DataFrame:
    df = board_to_dataframe(os.getenv("WORK_ORDERS_BOARD_ID"))
    return clean_dataframe(df)


def load_deals() -> pd.DataFrame:
    df = board_to_dataframe(os.getenv("DEALS_BOARD_ID"))
    return clean_dataframe(df)


if __name__ == "__main__":
    wo_df = load_work_orders()
    print("Work Orders — cleaned")
    print(wo_df.shape)
    print(wo_df[["Item Name", "Sector", "Execution Status"]].head())
    print("\nData quality (Work Orders):")
    print(data_quality_report(wo_df, DATE_COLUMNS + AMOUNT_COLUMNS + ["Sector"]))

    deals_df = load_deals()
    print("\nDeals — cleaned")
    print(deals_df.shape)
    print(deals_df[["Item Name", "Sector/service", "Deal Status"]].head())
    print("\nData quality (Deals):")