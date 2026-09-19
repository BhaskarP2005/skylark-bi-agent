import os
import requests
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_URL = "https://api.monday.com/v2"
API_TOKEN = os.getenv("MONDAY_API_TOKEN")


def query_monday(query: str, variables: dict = None):
    headers = {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json",
        "API-Version": "2024-10",
    }
    resp = requests.post(
        MONDAY_API_URL,
        json={"query": query, "variables": variables or {}},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"monday.com API error: {data['errors']}")
    return data["data"]


def get_board_items(board_id: str):
    """Pull all items + column values from a board, handling pagination."""
    items = []
    cursor = None
    query = """
    query ($boardId: [ID!], $cursor: String) {
      boards(ids: $boardId) {
        name
        items_page(limit: 100, cursor: $cursor) {
          cursor
          items {
            id
            name
            column_values {
              id
              text
              value
              type
            }
          }
        }
      }
    }
    """
    while True:
        data = query_monday(query, {"boardId": [board_id], "cursor": cursor})
        page = data["boards"][0]["items_page"]
        items.extend(page["items"])
        cursor = page["cursor"]
        if not cursor:
            break
    return items


def get_board_columns(board_id: str):
    """Return {column_id: column_title} for a board."""
    query = """
    query ($boardId: [ID!]) {
      boards(ids: $boardId) {
        columns {
          id
          title
          type
        }
      }
    }
    """
    data = query_monday(query, {"boardId": [board_id]})
    columns = data["boards"][0]["columns"]
    return {c["id"]: c["title"] for c in columns}

if __name__ == "__main__":
    work_orders_id = os.getenv("WORK_ORDERS_BOARD_ID")
    deals_id = os.getenv("DEALS_BOARD_ID")

    wo_columns = get_board_columns(work_orders_id)
    print("Work Orders columns:")
    for cid, title in wo_columns.items():
        print(f"  {cid} -> {title}")

    deal_columns = get_board_columns(deals_id)
    print("\nDeal columns:")
    for cid, title in deal_columns.items():
        print(f"  {cid} -> {title}")