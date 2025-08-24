# Twitter/X Stock Insights

Collect tweets hourly from selected handles, classify them into Stock-Specific vs Financial Awareness using **DB-driven keywords** that you upload as JSON, and view everything in a Streamlit dashboard.

## Setup

1) Python 3.10+
2) `pip install -r requirements.txt`
3) Copy `.env.example` to `.env` and fill in:
   - `BEARER_TOKEN=...`
   - `TWITTER_HANDLES=finGuru,moneyTalks` (no @)
   - optional `COLLECTOR_INTERVAL=3600`

## Run locally

- Start collector (hourly loop):
