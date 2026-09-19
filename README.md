# Skylark Drones — monday.com Business Intelligence Agent

**Live app:** https://skylark-bi-agent-mhcvyfczzju53tlnrwyais.streamlit.app
**Source code:** https://github.com/BhaskarP2005/skylark-bi-agent

A conversational agent that answers founder-level business questions by reading two live monday.com boards — **Work Orders** (project execution) and **Deals** (sales pipeline) — and reasoning over the real, messy data dynamically. No data is hardcoded; every answer is generated from a live API call to monday.com at query time.

---

## 1. Approach & Architecture

```
User question (Streamlit chat)
        │
        ▼
  Gemini (gemini-flash-lite-latest) — tool-use / function-calling
        │
        ├─▶ get_deals(sector, stage, status)
        ├─▶ get_work_orders(sector, status)
        ├─▶ aggregate_deals(group_by, metric, agg)
        └─▶ generate_leadership_summary()
                │
                ▼
     data_loader.py — pandas DataFrames, built dynamically from:
                │
                ├─▶ monday_client.py — live GraphQL calls to monday.com
                └─▶ normalizer.py — cleans nulls, dates, amounts, sector text
                │
                ▼
          monday.com boards (Work Orders, Deals) — read-only
```

**Flow:** A founder's question goes to Gemini along with a set of tool definitions. Gemini decides which tool(s) to call and with what filters (this is the query-understanding step — e.g. mapping "pipeline" and "this quarter" to the right data pull). Each tool call fetches live data via `monday_client.py`, which is cleaned by `normalizer.py`, converted into a pandas DataFrame with human-readable column names by `data_loader.py`, and returned to Gemini. Gemini then synthesizes a narrative answer — numbers plus context plus data-quality caveats — which is rendered in the Streamlit chat UI.

### Files
- `monday_client.py` — GraphQL client: fetches board items and column definitions (id → title mapping) from monday.com's live API.
- `normalizer.py` — cleaning functions: blank/`N/A`-style values → `None`, fuzzy date parsing, currency-symbol stripping, sector text casing normalization, plus a data-quality report helper.
- `data_loader.py` — combines the above into clean, readable pandas DataFrames for each board (`load_work_orders()`, `load_deals()`).
- `agent.py` — the agent itself: tool functions the model can call, the system prompt, and the Gemini chat/tool-loop wiring.
- `app.py` — Streamlit chat interface.

---

## 2. Tech Stack & Why

| Choice | Reasoning |
|---|---|
| **monday.com GraphQL API** (not MCP) | Full control and easier to debug directly against real data within a short build window; no extra server to host. MCP was considered but adds setup overhead that wasn't worth it here. |
| **Google Gemini** (`gemini-flash-lite-latest`) for the agent | Free-tier API access with function-calling support, sufficient reasoning quality for structured BI queries, and a high enough free daily quota to iterate quickly during development (the default `gemini-3.6-flash` model's free tier is capped at 20 requests/day, which was hit during testing). |
| **Python + pandas** | Fast to iterate, strong ecosystem for cleaning/aggregating tabular data. |
| **Streamlit** | Got a working, hosted chat UI running in well under an hour, with a public link via Streamlit Community Cloud requiring no separate frontend/backend deployment. |
| **Streamlit Community Cloud** for hosting | Free, deploys directly from GitHub, gives a public testable link with no local setup for reviewers. |

---

## 3. AI Tools Used

This project was built with the help of **Claude (Anthropic)** as a coding assistant/pair-programmer throughout — for architecture planning, writing the Python modules (monday.com client, normalizer, agent tool-loop, Streamlit UI), debugging errors encountered during setup (dependency conflicts, deprecated model names, GitHub authentication), and drafting this README. **Google Gemini** is the LLM that powers the deployed agent itself (the reasoning/tool-calling engine end users interact with) — this is a separate, deliberate choice from the development-assistant tool, made primarily due to free-tier API availability.

---

## 4. Key Assumptions

- Treated blank/`N/A`/`-`/`null`-style strings as genuinely missing data (`None`), rather than as zero or a literal string, across all fields.
- Sector/category text fields (`Sector`, `Sector/service`) are normalized for casing/whitespace only (e.g. "  mining " → "Mining"); no fuzzy-matching of near-duplicate sector names (e.g. "Energy" vs "Powerline") was implemented — if a query names a sector that doesn't exactly match the data, the agent either broadens its answer across all sectors and states that assumption, or asks a clarifying question, depending on the query.
- Dates are parsed with a fuzzy parser; any date string that can't be confidently parsed is treated as missing rather than guessed, so it's excluded from date-filtered aggregates rather than silently miscounted.
- "Overdue" work orders are not a field that exists directly in the data — the agent infers this by cross-referencing `Probable End Date` against incomplete execution status, and explicitly states this inference method when it does so.
- "Open deals" is interpreted as any deal where `Deal Status` = "Open" (as opposed to Won/Lost/Dead/On Hold states present in the data).

## 5. Trade-offs Chosen and Why

- **GraphQL API over MCP**, as noted above — prioritized speed and debuggability over using monday.com's newer native MCP server.
- **Gemini over Claude/OpenAI for the deployed agent** — driven by free-tier API access rather than a strict capability comparison; this is documented as an explicit constraint, not a claim that Gemini is categorically the best choice.
- **In-memory data caching per session** rather than persistent caching — each Streamlit session loads data once and reuses it across the conversation; a manual `refresh_data()` function exists for forcing a re-pull, but isn't wired into the UI. This favors simplicity/speed over always-freshest data.
- **Minimal, hand-picked `requirements.txt`** rather than a full `pip freeze` dump — the frozen version list caused a real dependency conflict (`google-api-core[grpc]` vs `grpcio-status`) when deploying to Streamlit Cloud's Linux environment; switching to an unpinned, minimal list let pip resolve compatible versions itself.
- **Tool functions return helpful error strings instead of crashing** (e.g. an invalid `group_by` column returns the list of valid columns) — this lets the agent self-correct within the same conversation turn instead of failing outright when it guesses a wrong field name, which happened during testing.

## 6. What I'd Do Differently With More Time

- Add a proper caching/rate-limit layer for the monday.com API instead of simple in-memory session caching.
- Build real entity-resolution/fuzzy-matching for sector and company name variants, instead of a fixed casing-normalization pass.
- Add automated tests for the normalizer functions against a broader set of real edge cases found in the data.
- Add explicit conversation memory/follow-up handling in the Streamlit UI (currently each question is sent with limited chat history threading).
- Swap the deprecated `google-generativeai` SDK for the current `google-genai` package (a deprecation warning appeared during development; functionality was unaffected but this should be updated for long-term maintenance).

## 7. How I Interpreted "Leadership Updates"

Implemented as an additional tool, `generate_leadership_summary()`, that the agent calls when asked for a "leadership update," "weekly summary," or similar phrasing. It returns pipeline value broken down by deal stage and by deal status, a work-order status count breakdown, and total record counts. The agent then turns this into a short, copy-pasteable digest — crore-formatted figures, a stage-by-stage breakdown, and 2-3 notable callouts (e.g. concentration in a single large deal, or a data-quality issue) — rather than a separate standalone report feature, so it fits naturally into the same conversational interface as every other query.

---

## 8. Setup Instructions (Local)

1. Clone the repo and create a virtual environment:
   ```
   git clone https://github.com/BhaskarP2005/skylark-bi-agent.git
   cd skylark-bi-agent
   python -m venv venv
   venv\Scripts\Activate.ps1   # Windows PowerShell
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the project root:
   ```
   MONDAY_API_TOKEN=your_monday_api_token
   WORK_ORDERS_BOARD_ID=your_work_orders_board_id
   DEALS_BOARD_ID=your_deals_board_id
   GEMINI_API_KEY=your_gemini_api_key
   ```
3. Run the app:
   ```
   streamlit run app.py
   ```

### monday.com configuration
Two boards are expected: a **Work Orders** board and a **Deals** board, imported from the provided source data with monday.com's Excel importer. Column types were left largely as monday.com auto-detected them on import (Status, Date, Text, Numbers), with cleaning/normalization handled entirely in code (`normalizer.py`) rather than depending on strict column typing in monday.com itself — this makes the agent resilient to minor differences in how a board is set up.

---

## 9. Error Handling

- All monday.com API calls and tool functions are wrapped in try/except; failures return a descriptive message to the agent (and, if unrecoverable, to the user) rather than crashing the app.
- Invalid column names passed by the model to `aggregate_deals` return the list of valid columns, allowing the model to self-correct.
- Date and amount parsing failures are treated as missing data rather than raising exceptions or guessing incorrect values.
