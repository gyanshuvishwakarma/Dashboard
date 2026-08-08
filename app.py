"""
Advanced Sales Analytics Dashboard
-----------------------------------
Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# --------------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ⚠️ EDIT THIS LINE with your real CSV path, e.g.:
# Windows:  DATA_PATH = Path(r"C:\Users\YourName\Documents\sales23_advanced.csv")
# Mac/Linux: DATA_PATH = Path("/Users/yourname/Documents/sales23_advanced.csv")

DATA_PATH = Path(r"C:\Users\vishw\OneDrive\Desktop\github\sales23_advanced.csv")
# --------------------------------------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .main { background-color: #0e1117; }
        div[data-testid="stMetric"] {
            background-color: #1a1c24;
            border: 1px solid #2b2f3a;
            border-radius: 12px;
            padding: 15px 15px 5px 15px;
        }
        div[data-testid="stMetricLabel"] { font-size: 14px; color: #9aa0ac; }
        div[data-testid="stMetricValue"] { font-size: 26px; }
        section[data-testid="stSidebar"] { border-right: 1px solid #2b2f3a; }
        h1, h2, h3 { font-weight: 700; }
        .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------
# DATA LOADING & CLEANING
# --------------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    df.columns = [c.strip() for c in df.columns]

    str_cols = df.select_dtypes(include="object").columns
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace({"": np.nan, "nan": np.nan})

    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], errors="coerce")

    df = df.dropna(subset=["Order_Date"]).copy()

    df["Year"] = df["Order_Date"].dt.year
    df["Month"] = df["Order_Date"].dt.month
    df["Month_Name"] = df["Order_Date"].dt.strftime("%B")
    df["Quarter"] = df["Order_Date"].dt.year.astype(str) + "Q" + df["Order_Date"].dt.quarter.astype(str)
    df["Month_Period"] = df["Order_Date"].dt.to_period("M").astype(str)

    df["Ship_Delay_Days"] = (df["Ship_Date"] - df["Order_Date"]).dt.days

    for c in ["Sales", "Quantity", "Discount", "Profit"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Sales", "Quantity", "Discount", "Profit"])

    df["Profit_Margin_%"] = np.where(df["Sales"] != 0, (df["Profit"] / df["Sales"]) * 100, 0)

    for c in ["Region", "State", "Category", "Sub_Category", "Product_Name", "Sales_Category", "High_Discount"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df


if not DATA_PATH.exists():
    st.error(f"Data file not found at: {DATA_PATH}. Please update DATA_PATH in app.py.")
    st.stop()

raw_df = load_data(DATA_PATH)

# --------------------------------------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------------------------------------
st.sidebar.title("📊 Sales Dashboard")
st.sidebar.markdown("Use the filters below to slice the data.")
st.sidebar.markdown("---")

min_date, max_date = raw_df["Order_Date"].min().date(), raw_df["Order_Date"].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

regions = sorted(raw_df["Region"].dropna().unique().tolist())
sel_regions = st.sidebar.multiselect("Region", regions, default=regions)

categories = sorted(raw_df["Category"].dropna().unique().tolist())
sel_categories = st.sidebar.multiselect("Category", categories, default=categories)

subcats_available = sorted(raw_df[raw_df["Category"].isin(sel_categories)]["Sub_Category"].dropna().unique().tolist())
sel_subcats = st.sidebar.multiselect("Sub-Category", subcats_available, default=subcats_available)

states = sorted(raw_df["State"].dropna().unique().tolist())
sel_states = st.sidebar.multiselect("State", states, default=states)

discount_filter = st.sidebar.radio("High Discount Orders", ["All", "Yes only", "No only"], horizontal=False)

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + Plotly · Internship Project")

# --------------------------------------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------------------------------------
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

df = raw_df[
    (raw_df["Order_Date"].dt.date >= start_date)
    & (raw_df["Order_Date"].dt.date <= end_date)
    & (raw_df["Region"].isin(sel_regions))
    & (raw_df["Category"].isin(sel_categories))
    & (raw_df["Sub_Category"].isin(sel_subcats))
    & (raw_df["State"].isin(sel_states))
].copy()

if discount_filter == "Yes only":
    df = df[df["High_Discount"].str.lower() == "yes"]
elif discount_filter == "No only":
    df = df[df["High_Discount"].str.lower() == "no"]

if df.empty:
    st.warning("No data matches the selected filters. Please broaden your filter selection.")
    st.stop()

# --------------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------------
st.title("📈 Advanced Sales Analytics Dashboard")
st.caption(
    f"Showing **{len(df):,}** orders from **{df['Order_Date'].min().date()}** "
    f"to **{df['Order_Date'].max().date()}**"
)

# --------------------------------------------------------------------------------
# KPI ROW
# --------------------------------------------------------------------------------
total_sales = df["Sales"].sum()
total_profit = df["Profit"].sum()
total_orders = df["Order_ID"].nunique()
avg_order_value = total_sales / total_orders if total_orders else 0
overall_margin = (total_profit / total_sales * 100) if total_sales else 0
avg_discount = df["Discount"].mean() * 100
total_qty = df["Quantity"].sum()

period_days = (end_date - start_date).days + 1

# --- FIX ---
# start_date / end_date from st.sidebar.date_input are plain `datetime.date`
# objects. `date - pd.Timedelta(...)` returns another plain `date`, which has
# NO `.date()` method. The original code called `.date()` on them anyway,
# raising: AttributeError: 'datetime.date' object has no attribute 'date'.
# Fix: don't call `.date()` on values that are already `date` objects.
prev_end = start_date - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days - 1)
prev_df = raw_df[
    (raw_df["Order_Date"].dt.date >= prev_start)
    & (raw_df["Order_Date"].dt.date <= prev_end)
]
# --- END FIX ---

prev_sales = prev_df["Sales"].sum()
prev_profit = prev_df["Profit"].sum()

sales_delta = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales else None
profit_delta = ((total_profit - prev_profit) / prev_profit * 100) if prev_profit else None

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Sales", f"₹{total_sales:,.0f}", f"{sales_delta:+.1f}% vs prior period" if sales_delta is not None else None)
k2.metric("Total Profit", f"₹{total_profit:,.0f}", f"{profit_delta:+.1f}% vs prior period" if profit_delta is not None else None)
k3.metric("Profit Margin", f"{overall_margin:.1f}%")
k4.metric("Total Orders", f"{total_orders:,}")
k5.metric("Avg Order Value", f"₹{avg_order_value:,.0f}")
k6.metric("Avg Discount", f"{avg_discount:.1f}%")

st.markdown("---")

# --------------------------------------------------------------------------------
# TABS
# --------------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🧭 Category & Region", "🏆 Products & Discounts", "📋 Raw Data"])

with tab1:
    col1, col2 = st.columns((2, 1))

    with col1:
        st.subheader("Sales & Profit Trend Over Time")
        trend = df.groupby("Month_Period", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        trend = trend.sort_values("Month_Period")
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=trend["Month_Period"], y=trend["Sales"], name="Sales",
                                        mode="lines+markers", line=dict(color="#4C9AFF", width=3), fill="tozeroy"))
        fig_trend.add_trace(go.Scatter(x=trend["Month_Period"], y=trend["Profit"], name="Profit",
                                        mode="lines+markers", line=dict(color="#36B37E", width=3)))
        fig_trend.update_layout(
            template="plotly_dark", height=380, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col2:
        st.subheader("Sales Category Split")
        sc = df.groupby("Sales_Category", as_index=False)["Sales"].sum()
        fig_sc = px.pie(sc, names="Sales_Category", values="Sales", hole=0.55,
                         color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_sc.update_traces(textinfo="percent+label")
        fig_sc.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=30, b=10),
                              showlegend=False)
        st.plotly_chart(fig_sc, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Quarterly Performance")
        q = df.groupby("Quarter", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_values("Quarter")
        fig_q = go.Figure()
        fig_q.add_trace(go.Bar(x=q["Quarter"], y=q["Sales"], name="Sales", marker_color="#4C9AFF"))
        fig_q.add_trace(go.Bar(x=q["Quarter"], y=q["Profit"], name="Profit", marker_color="#36B37E"))
        fig_q.update_layout(template="plotly_dark", barmode="group", height=350,
                             margin=dict(l=10, r=10, t=30, b=10),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_q, use_container_width=True)

    with col4:
        st.subheader("Profit Margin Distribution")
        fig_hist = px.histogram(df, x="Profit_Margin_%", nbins=25, color_discrete_sequence=["#8777D9"])
        fig_hist.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10),
                                bargap=0.05)
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sales by Region")
        reg = df.groupby("Region", as_index=False)["Sales"].sum().sort_values("Sales", ascending=True)
        fig_reg = px.bar(reg, x="Sales", y="Region", orientation="h", text_auto=".2s",
                          color="Sales", color_continuous_scale="Blues")
        fig_reg.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10),
                               coloraxis_showscale=False)
        st.plotly_chart(fig_reg, use_container_width=True)

    with col2:
        st.subheader("Sales by Category")
        cat = df.groupby("Category", as_index=False)["Sales"].sum().sort_values("Sales", ascending=True)
        fig_cat = px.bar(cat, x="Sales", y="Category", orientation="h", text_auto=".2s",
                          color="Sales", color_continuous_scale="Greens")
        fig_cat.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10),
                               coloraxis_showscale=False)
        st.plotly_chart(fig_cat, use_container_width=True)

    st.subheader("Region × Category Sales Heatmap")
    heat = df.pivot_table(index="Region", columns="Category", values="Sales", aggfunc="sum", fill_value=0)
    fig_heat = px.imshow(heat, text_auto=".2s", aspect="auto", color_continuous_scale="Viridis")
    fig_heat.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("Sub-Category Performance (Sales vs Profit)")
    subcat = df.groupby("Sub_Category", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"),
                                                              Orders=("Order_ID", "nunique"))
    fig_sub = px.scatter(subcat, x="Sales", y="Profit", size="Orders", color="Sub_Category", text="Sub_Category",
                          size_max=45)
    fig_sub.update_traces(textposition="top center")
    fig_sub.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
    st.plotly_chart(fig_sub, use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 10 Products by Sales")
        top_products = df.groupby("Product_Name", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False).head(10)
        fig_top = px.bar(top_products.sort_values("Sales"), x="Sales", y="Product_Name", orientation="h",
                          text_auto=".2s", color="Sales", color_continuous_scale="Tealgrn")
        fig_top.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10),
                               coloraxis_showscale=False)
        st.plotly_chart(fig_top, use_container_width=True)

    with col2:
        st.subheader("Top 10 Products by Profit")
        top_profit = df.groupby("Product_Name", as_index=False)["Profit"].sum().sort_values("Profit", ascending=False).head(10)
        fig_topp = px.bar(top_profit.sort_values("Profit"), x="Profit", y="Product_Name", orientation="h",
                           text_auto=".2s", color="Profit", color_continuous_scale="Purp")
        fig_topp.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10),
                                coloraxis_showscale=False)
        st.plotly_chart(fig_topp, use_container_width=True)

    st.subheader("Discount vs Profit Margin")
    fig_disc = px.scatter(df, x="Discount", y="Profit_Margin_%", color="High_Discount", size="Sales",
                           hover_data=["Product_Name", "Region"], color_discrete_map={"Yes": "#FF5630", "No": "#4C9AFF"})
    fig_disc.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_disc, use_container_width=True)

    st.subheader("High Discount Orders — Share by Category")
    hd = df.groupby(["Category", "High_Discount"], as_index=False)["Order_ID"].nunique().rename(columns={"Order_ID": "Orders"})
    fig_hd = px.bar(hd, x="Category", y="Orders", color="High_Discount", barmode="group",
                     color_discrete_map={"Yes": "#FF5630", "No": "#4C9AFF"})
    fig_hd.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_hd, use_container_width=True)

with tab4:
    st.subheader("Filtered Data")
    st.dataframe(df.sort_values("Order_Date", ascending=False), use_container_width=True, height=500)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Filtered Data as CSV", data=csv_bytes,
                        file_name="filtered_sales_data.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Summary Statistics")
    st.dataframe(df[["Sales", "Quantity", "Discount", "Profit", "Profit_Margin_%"]].describe().T,
                 use_container_width=True)