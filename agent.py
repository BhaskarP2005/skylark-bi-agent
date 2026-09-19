import os
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from data_loader import load_work_orders, load_deals

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---- Load data once per session (kept in memory, refreshed each app run) ----
_work_orders_df = None
_deals_df = None


def get_data():
    """Lazily load and cache both DataFrames for this session."""
    global _work_orders_df, _deals_df
    if _work_orders_df is None:
        _work_orders_df = load_work_orders()
    if _deals_df is None:
        _deals_df = load_deals()
    return _work_orders_df, _deals_df


def refresh_data():
    """Force a fresh pull from monday.com (call this if data might have changed)."""
    global _work_orders_df, _deals_df
    _work_orders_df = load_work_orders()
    _deals_df = load_deals()


# ---- Tool functions the model can call ----

def get_deals(sector: str = None, stage: str = None, status: str = None) -> str:
    """Fetch deals, optionally filtered by sector, stage, or status."""
    try:
        _, deals_df = get_data()
        df = deals_df.copy()
        if sector:
            df = df[df["Sector/service"].str.contains(sector, case=False, na=False)]
        if stage:
            df = df[df["Deal Stage"].str.contains(stage, case=False, na=False)]
        if status:
            df = df[df["Deal Status"].str.contains(status, case=False, na=False)]
        if df.empty:
            return "No matching deals found."
        return df.to_json(orient="records")
    except Exception as e:
        return f"Error fetching deals: {e}"


def get_work_orders(sector: str = None, status: str = None) -> str:
    """Fetch work orders, optionally filtered by sector or execution status."""
    try:
        wo_df, _ = get_data()
        df = wo_df.copy()
        if sector and "Sector" in df.columns:
            df = df[df["Sector"].str.contains(sector, case=False, na=False)]
        if status and "Execution Status" in df.columns:
            df = df[df["Execution Status"].str.contains(status, case=False, na=False)]
        if df.empty:
            return "No matching work orders found."
        return df.to_json(orient="records")
    except Exception as e:
        return f"Error fetching work orders: {e}"


def aggregate_deals(group_by: str, metric: str = "Masked Deal value", agg: str = "sum") -> str:
    """Aggregate deals by a column. Valid group_by values: 'Deal Status', 'Sector/service', 'Deal Stage', 'Owner code'.
    Valid metric values: 'Masked Deal value'. Valid agg values: 'sum', 'count', 'avg'."""
    try:
        _, deals_df = get_data()
        df = deals_df.copy()
        if group_by not in df.columns:
            return f"Error: '{group_by}' is not a valid column. Available columns: {list(df.columns)}"
        if metric not in df.columns:
            return f"Error: '{metric}' is not a valid column. Available columns: {list(df.columns)}"
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        if agg == "sum":
            result = df.groupby(group_by)[metric].sum(min_count=1)
        elif agg == "count":
            result = df.groupby(group_by)[metric].count()
        elif agg == "avg":
            result = df.groupby(group_by)[metric].mean()
        else:
            return f"Unknown aggregation type: {agg}. Use 'sum', 'count', or 'avg'."
        return result.to_json()
    except Exception as e:
        return f"Error aggregating deals: {e}"


def generate_leadership_summary() -> str:
    """Generate a concise weekly leadership digest: pipeline value by stage, work order status breakdown, and notable callouts."""
    try:
        wo_df, deals_df = get_data()

        deals_df_copy = deals_df.copy()
        deals_df_copy["Masked Deal value"] = pd.to_numeric(deals_df_copy["Masked Deal value"], errors="coerce")
        pipeline_by_stage = deals_df_copy.groupby("Deal Stage")["Masked Deal value"].sum(min_count=1).to_dict()
        pipeline_by_status = deals_df_copy.groupby("Deal Status")["Masked Deal value"].sum(min_count=1).to_dict()

        wo_status_counts = wo_df["Execution Status"].value_counts().to_dict() if "Execution Status" in wo_df.columns else {}

        summary = {
            "pipeline_value_by_stage": pipeline_by_stage,
            "pipeline_value_by_status": pipeline_by_status,
            "work_order_status_counts": wo_status_counts,
            "total_deals": len(deals_df),
            "total_work_orders": len(wo_df),
        }
        return json.dumps(summary, default=str)
    except Exception as e:
        return f"Error generating leadership summary: {e}"


# ---- Gemini agent wiring ----

TOOLS = [get_deals, get_work_orders, aggregate_deals, generate_leadership_summary]

SYSTEM_PROMPT = """You are a business intelligence assistant for Skylark Drones' founders.
You have read-only access to live monday.com data via tools: Deals (sales pipeline) and Work Orders (project execution).
Data is real-world and messy — some records have missing or unparseable dates, sectors, or amounts.

Rules:
- Always call tools to get live data; never invent numbers.
- When a query is ambiguous, ask one short clarifying question OR state a reasonable assumption you're making.
- Mention material data-quality caveats (e.g. missing values) when relevant.
- Answer like a sharp analyst: lead with the number/insight, then brief supporting context. Don't dump raw tables.
- If asked for a "leadership update", "weekly summary", or similar, call generate_leadership_summary and turn it into a
  short, copy-pasteable digest: pipeline value by stage/status, work order status breakdown, and 2-3 notable callouts
  (biggest deal, most at-risk work order, any major data-quality issue). Keep it concise and scannable.
"""

model = genai.GenerativeModel(
    model_name="gemini-flash-lite-latest",
    tools=TOOLS,
    system_instruction=SYSTEM_PROMPT,
)


def ask_agent(question: str, chat_history=None) -> str:
    """Send a question to the agent, using tool-calling automatically."""
    chat = model.start_chat(enable_automatic_function_calling=True, history=chat_history or [])
    response = chat.send_message(question)
    return response.text


if __name__ == "__main__":
    print("Testing agent with a sample question...\n")
    answer = ask_agent("What's the total value of open deals right now?")
    print("Answer:")
    print(answer)