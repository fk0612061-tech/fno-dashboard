import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(layout="wide", page_title="Live F&O Terminal", page_icon="📈")

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("⚡ Live F&O Intelligence Terminal")

st.sidebar.header("⚙️ Settings")
symbol = st.sidebar.selectbox(
    "Select Underlying", ["NIFTY", "BANKNIFTY", "FINNIFTY"]
)
expiry = st.sidebar.text_input("Expiry Date (YYYY-MM-DD)", value="2026-11-12")
access_token = st.sidebar.text_input(
    "Upstox Access Token", type="password", help="Paste your token here"
)

tab1, tab2, tab3 = st.tabs(
    ["🔥 Trend Scanner", "📊 Live Option Chain (OI)", "🎯 IV vs RV Screener"]
)

# TAB 1: Trend Scanner
with tab1:
  st.subheader("F&O Market Breadth & Price-OI Trends")
  scan_data = {
      "Symbol": [
          "NIFTY",
          "BANKNIFTY",
          "DIVISLAB",
          "ASTRAL",
          "CIPLA",
          "COROMANDEL",
          "DATAPATTNS",
          "RELIANCE",
      ],
      "LTP": [
          24520.0,
          52310.0,
          4850.0,
          1920.0,
          1530.0,
          1680.0,
          3120.0,
          2740.0,
      ],
      "% Price Chg": [0.45, -0.62, 1.85, 2.10, -1.20, -0.40, 3.40, 0.15],
      "% OI Chg": [8.2, 12.4, 15.6, -5.4, 9.8, -4.2, 22.1, -1.1],
      "Trend": [
          "Long Build-up",
          "Short Build-up",
          "Long Build-up",
          "Short Covering",
          "Short Build-up",
          "Long Unwinding",
          "Long Build-up",
          "Neutral",
      ],
  }
  df_scan = pd.DataFrame(scan_data)

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Long Buildup", len(df_scan[df_scan["Trend"] == "Long Build-up"]))
  col2.metric(
      "Short Buildup", len(df_scan[df_scan["Trend"] == "Short Build-up"])
  )
  col3.metric(
      "Short Covering", len(df_scan[df_scan["Trend"] == "Short Covering"])
  )
  col4.metric(
      "Long Unwinding", len(df_scan[df_scan["Trend"] == "Long Unwinding"])
  )

  st.dataframe(df_scan, use_container_width=True)

# TAB 2: Option Chain
with tab2:
  st.subheader(f"Full Option Chain: {symbol} ({expiry})")
  chain_data = {
      "Call OI": [120450, 245000, 380100, 150200, 95000],
      "Call OI Chg": [15200, 42000, 110500, -8400, -12000],
      "Call IV": [14.2, 13.8, 13.5, 13.1, 12.8],
      "Call LTP": [320.5, 215.0, 125.4, 62.0, 24.5],
      "STRIKE": [24300, 24400, 24500, 24600, 24700],
      "Put LTP": [28.0, 52.5, 112.0, 198.5, 310.0],
      "Put IV": [15.1, 14.8, 14.3, 14.0, 13.6],
      "Put OI Chg": [-5200, 18500, 95200, 52000, 14000],
      "Put OI": [85000, 160000, 410000, 210000, 78000],
  }
  df_chain = pd.DataFrame(chain_data)

  total_call_oi = df_chain["Call OI"].sum()
  total_put_oi = df_chain["Put OI"].sum()
  pcr = round(total_put_oi / total_call_oi, 2)

  c1, c2, c3 = st.columns(3)
  c1.metric("Total Call OI", f"{total_call_oi:,}")
  c2.metric("Total Put OI", f"{total_put_oi:,}")
  c3.metric("PCR", pcr)

  st.dataframe(df_chain, use_container_width=True)

# TAB 3: IV Screener
with tab3:
  st.subheader("Options Volatility Scatter Map (IV vs RV)")
  iv_data = {
      "Stock": [
          "NIFTY",
          "BANKNIFTY",
          "DIVISLAB",
          "ASTRAL",
          "CIPLA",
          "COROMANDEL",
          "DATAPATTNS",
      ],
      "ATM_IV": [13.5, 16.2, 38.0, 31.5, 22.0, 29.0, 42.0],
      "Realised_Vol": [11.0, 14.5, 23.0, 24.0, 16.5, 26.0, 35.0],
      "Volume": [150000, 120000, 25000, 18000, 45000, 12000, 8000],
  }
  df_iv = pd.DataFrame(iv_data)
  df_iv["Ratio"] = df_iv["ATM_IV"] / df_iv["Realised_Vol"]
  df_iv["Category"] = [
      (
          "High IV (Sell Options)"
          if r >= 1.3
          else ("Cheap IV (Buy Options)" if r <= 0.85 else "Normal")
      )
      for r in df_iv["Ratio"]
  ]

  fig = px.scatter(
      df_iv,
      x="ATM_IV",
      y="Ratio",
      size="Volume",
      color="Category",
      text="Stock",
      hover_name="Stock",
      color_discrete_map={
          "High IV (Sell Options)": "#FFA500",
          "Normal": "#888888",
          "Cheap IV (Buy Options)": "#00BFFF",
      },
      template="plotly_dark",
  )
  fig.add_hline(
      y=1.3,
      line_dash="dot",
      line_color="#FFA500",
      annotation_text="Rich IV (>= 1.3)",
  )
  fig.add_hline(
      y=0.85,
      line_dash="dot",
      line_color="#00BFFF",
      annotation_text="Cheap IV (<= 0.85)",
  )
  fig.update_traces(textposition="top center")
  fig.update_layout(
      height=550,
      xaxis_title="ATM Implied Volatility (%)",
      yaxis_title="IV / Realised Vol",
  )

  st.plotly_chart(fig, use_container_width=True)
  
