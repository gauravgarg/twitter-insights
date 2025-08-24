import json
import streamlit as st
import pandas as pd
from db_init import get_conn, init_db
from utils import normalize_keyword

st.set_page_config(page_title="Stock & Finance Tweets", layout="wide")

conn = get_conn()
init_db(conn)

@st.cache_data(ttl=60)
def load_df():
    return pd.read_sql_query(
        "SELECT id, handle, content, category, stock_name, created_at "
        "FROM tweets ORDER BY datetime(created_at) DESC", conn
    )

def load_keywords():
    cur = conn.cursor()
    cur.execute("SELECT keyword FROM stock_keywords ORDER BY keyword ASC")
    return [r[0] for r in cur.fetchall()]

def add_keywords(keywords):
    cur = conn.cursor()
    added = 0
    for kw in keywords:
        kw = normalize_keyword(kw)
        if not kw:
            continue
        try:
            cur.execute("INSERT INTO stock_keywords (keyword) VALUES (?)", (kw,))
            added += 1
        except Exception:
            pass
    conn.commit()
    return added

st.title("📊 Stock & Finance Tweets Dashboard")

# --- Sidebar: JSON upload for keywords
st.sidebar.header("⚙️ Manage Stock Keywords (JSON)")
uploaded = st.sidebar.file_uploader("Upload JSON in your format", type=["json"])
if uploaded is not None:
    try:
        data = json.load(uploaded)
        new_keywords = set()

        # V40 / V40Next are {sector: [tickers]}
        for key in ("V40", "V40Next"):
            if key in data and isinstance(data[key], dict):
                for _, tickers in data[key].items():
                    for t in tickers:
                        new_keywords.add(t)

        # V200 is a flat list
        if "V200" in data and isinstance(data["V200"], list):
            for t in data["V200"]:
                new_keywords.add(t)

        preview = sorted({normalize_keyword(k) for k in new_keywords})
        st.sidebar.caption("Preview (first 20):")
        st.sidebar.write(preview[:20])

        if st.sidebar.button("Add JSON Keywords to DB"):
            count = add_keywords(preview)
            st.sidebar.success(f"✅ Added {count} keywords (duplicates ignored).")
            st.cache_data.clear()
    except Exception as e:
        st.sidebar.error(f"Failed to parse JSON: {e}")

# --- Load data & keywords
df = load_df()
keywords = load_keywords()

# --- Filters
c1, c2, c3 = st.columns(3)
with c1:
    category = st.selectbox("Category", ["All", "Stock-Specific", "Financial Awareness"])
with c2:
    stock = st.selectbox("Stock Keyword", ["All"] + keywords)
with c3:
    handle = st.selectbox("Handle", ["All"] + sorted(df["handle"].dropna().unique().tolist()))

fdf = df.copy()
if category != "All":
    fdf = fdf[fdf["category"] == category]
if stock != "All":
    fdf = fdf[fdf["stock_name"] == stock]
if handle != "All":
    fdf = fdf[fdf["handle"] == handle]

# --- KPI
k1, k2, k3 = st.columns(3)
k1.metric("Tweets", len(fdf))
k2.metric("Stock Mentions", fdf[fdf["category"]=="Stock-Specific"].shape[0])
k3.metric("Awareness Posts", fdf[fdf["category"]=="Financial Awareness"].shape[0])

# --- Charts
st.subheader("📈 Top Stocks")
if not fdf.empty and "stock_name" in fdf.columns:
    st.bar_chart(fdf["stock_name"].value_counts().head(15))

st.subheader("🗂️ Latest Tweets")
st.dataframe(
    fdf[["created_at","handle","category","stock_name","content"]]
      .rename(columns={
          "created_at":"Time",
          "handle":"Handle",
          "category":"Category",
          "stock_name":"Stock",
          "content":"Tweet"
      }),
    use_container_width=True,
    hide_index=True
)