import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from curl_cffi import requests
import time
from datetime import datetime

st.set_page_config(
    layout="wide",
    page_title="PRO-TERMINAL | NSE Real-Time Market Intelligence",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# Custom Institutional Dark Theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #080a0f;
        color: #e6edf3;
    }
    
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 20px;
        background: #0f141c;
        border-bottom: 1px solid #1f2937;
        margin-bottom: 18px;
        border-radius: 8px;
    }
    .brand-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: 1px;
        color: #38bdf8;
    }
    .status-badge {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
        border: 1px solid #22c55e;
        padding: 4px 10px;
        font-size: 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-pulse {
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #22c55e;
    }
    
    div[data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        padding: 12px 16px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        text-transform: uppercase;
        color: #94a3b8;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 700;
        color: #f8fafc;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1f2937;
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #0f141c;
        border: 1px solid #1e293b;
        color: #94a3b8;
        border-radius: 6px 6px 0 0;
        padding: 8px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function for safe float parsing
def clean_float(value, default=0.0):
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.replace(",", "").strip())
        return default
    except:
        return default

# Network Engine
def get_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    s = requests.Session(impersonate="chrome120")
    try:
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(0.4)
        return s, headers
    except:
        return None, headers

@st.cache_data(ttl=45)
def fetch_market_indices():
    s, headers = get_session()
    if not s:
        return {}
    try:
        res = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10).json()
        indices = {}
        for item in res.get("data", []):
            name = item.get("indexSymbol")
            if name in ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY IT"]:
                indices[name] = {
                    "last": clean_float(item.get("last")),
                    "change": clean_float(item.get("change")),
                    "pChange": clean_float(item.get("percentChange"))
                }
        return indices
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_fno_market_data():
    s, headers = get_session()
    if not s:
        return pd.DataFrame()
    try:
        url = "https://www.nseindia.com/api/live-analysis-variations?index=fo"
        res = s.get(url, headers=headers, timeout=10).json()
        records = []
        for row in res.get("allSec", {}).get("data", []):
            ltp = clean_float(row.get("ltp"))
            p_chg = clean_float(row.get("pChange"))
            oi = clean_float(row.get("openInterest"))
            oi_chg = clean_float(row.get("pchangeinOpenInterest"))
            
            if p_chg > 0 and oi_chg > 0:
                trend = "Long Buildup"
            elif p_chg < 0 and oi_chg > 0:
                trend = "Short Buildup"
            elif p_chg > 0 and oi_chg < 0:
                trend = "Short Covering"
            elif p_chg < 0 and oi_chg < 0:
                trend = "Long Unwinding"
            else:
                trend = "Neutral"
                
            records.append({
                "Symbol": row.get("symbol"),
                "LTP (₹)": ltp,
                "% Price Chg": p_chg,
                "Open Interest": int(oi),
                "% OI Chg": oi_chg,
                "Build-up": trend
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=45)
def fetch_live_option_chain(symbol):
    s, headers = get_session()
    if not s:
        return 0, [], []
    try:
        endpoint = "indices" if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else "equities"
        url = f"https://www.nseindia.com/api/option-chain-{endpoint}?symbol={symbol}"
        res = s.get(url, headers=headers, timeout=10).json()
        underlying = clean_float(res["records"]["underlyingValue"])
        expiries = res["records"]["expiryDates"]
        data = res["records"]["data"]
        return underlying, expiries, data
    except:
        return 0, [], []

def calculate_max_pain(df):
    if df.empty:
        return 0
    strikes = df["Strike"].tolist()
    total_loss = []
    for strike in strikes:
        loss = 0
        for _, row in df.iterrows():
            if row["Strike"] < strike:
                loss += (strike - row["Strike"]) * row["Call OI"]
            elif row["Strike"] > strike:
                loss += (row["Strike"] - strike) * row["Put OI"]
        total_loss.append(loss)
    if not total_loss:
        return 0
    return strikes[total_loss.index(min(total_loss))]

# Top Banner
current_time_str = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

st.markdown(f"""
<div class="top-header">
    <div>
        <span class="brand-title">TERMINAL // NSE INTELLIGENCE</span>
        <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">INSTITUTIONAL DERIVATIVES & VOLUME ENGINE</div>
    </div>
    <div style="display: flex; gap: 15px; align-items: center;">
        <span style="font-size: 0.8rem; color: #94a3b8; font-family: monospace;">SYS TIME: {current_time_str} IST</span>
        <span class="status-badge"><span class="status-pulse"></span>FEED CONNECTED</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Indices Ticker
indices_data = fetch_market_indices()
if indices_data:
    idx_cols = st.columns(len(indices_data))
    for i, (name, val) in enumerate(indices_data.items()):
        idx_cols[i].metric(
            label=name,
            value=f"{val['last']:,.2f}",
            delta=f"{val['change']:+.2f} ({val['pChange']:+.2f}%)"
        )
st.write("")

# Main Tabs Workspace
t1, t2, t3 = st.tabs([
    "📊 OPEN INTEREST & OPTION CHAIN",
    "⚡ F&O MARKET BREADTH (180+ CONTRACTS)",
    "🎯 TOP VOLUME & MARKET MOVERS"
])

# TAB 1: OPTION CHAIN & OI
with t1:
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
    with ctrl_col1:
        sel_symbol = st.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"])
    
    spot, expiries, raw_oc = fetch_live_option_chain(sel_symbol)
    
    with ctrl_col2:
        sel_expiry = st.selectbox("Expiry Contract", expiries if expiries else ["No Expiry Available"])
    with ctrl_col3:
        st.write("")
        st.write("")
        if st.button("⚡ FORCE REFRESH", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if raw_oc and expiries:
        parsed_rows = []
        for item in raw_oc:
            if item.get("expiryDate") == sel_expiry:
                strike = clean_float(item.get("strikePrice"))
                ce = item.get("CE", {})
                pe = item.get("PE", {})
                parsed_rows.append({
                    "Call OI": clean_float(ce.get("openInterest")),
                    "Call Chg OI": clean_float(ce.get("changeinOpenInterest")),
                    "Call IV": clean_float(ce.get("impliedVolatility")),
                    "Call LTP": clean_float(ce.get("lastPrice")),
                    "Strike": strike,
                    "Put LTP": clean_float(pe.get("lastPrice")),
                    "Put IV": clean_float(pe.get("impliedVolatility")),
                    "Put Chg OI": clean_float(pe.get("changeinOpenInterest")),
                    "Put OI": clean_float(pe.get("openInterest"))
                })
                
        df_oc = pd.DataFrame(parsed_rows).sort_values("Strike").reset_index(drop=True)
        
        if not df_oc.empty:
            total_ce_oi = df_oc["Call OI"].sum()
            total_pe_oi = df_oc["Put OI"].sum()
            pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
            atm_strike = min(df_oc["Strike"], key=lambda x: abs(x - spot))
            max_pain = calculate_max_pain(df_oc)
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Underlying Spot", f"{spot:,.2f}")
            m2.metric("Total Call OI", f"{int(total_ce_oi):,}")
            m3.metric("Total Put OI", f"{int(total_pe_oi):,}")
            pcr_sentiment = "BULLISH (>1.2)" if pcr > 1.2 else ("BEARISH (<0.8)" if pcr < 0.8 else "NEUTRAL")
            m4.metric("PCR Ratio", f"{pcr:.2f}", delta=pcr_sentiment)
            m5.metric("Max Pain", f"{max_pain:,.0f}")
            
            st.divider()
            
            atm_matches = df_oc.index[df_oc["Strike"] == atm_strike].tolist()
            atm_idx = atm_matches[0] if atm_matches else len(df_oc) // 2
            sub_oc = df_oc.iloc[max(0, atm_idx - 12) : min(len(df_oc), atm_idx + 13)]
            
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=(
                    f"TOTAL OPEN INTEREST (ATM: {atm_strike})",
                    "INTRADAY OI BUILDUP / UNWINDING"
                ),
                shared_yaxes=False
            )
            
            fig.add_trace(go.Bar(
                x=sub_oc["Strike"], y=sub_oc["Call OI"],
                name="Call OI (Resistance)", marker_color="#ef4444"
            ), row=1, col=1)
            fig.add_trace(go.Bar(
                x=sub_oc["Strike"], y=sub_oc["Put OI"],
                name="Put OI (Support)", marker_color="#22c55e"
            ), row=1, col=1)
            
            fig.add_trace(go.Bar(
                x=sub_oc["Strike"], y=sub_oc["Call Chg OI"],
                name="Call OI Chg (Writing)", marker_color="#f87171"
            ), row=1, col=2)
            fig.add_trace(go.Bar(
                x=sub_oc["Strike"], y=sub_oc["Put Chg OI"],
                name="Put OI Chg (Writing)", marker_color="#4ade80"
            ), row=1, col=2)
            
            fig.update_layout(
                height=460,
                barmode="group",
                plot_bgcolor="#0b0e14",
                paper_bgcolor="#0b0e14",
                font=dict(family="Inter, sans-serif", color="#94a3b8"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Interactive Option Matrix")
            st.dataframe(sub_oc, use_container_width=True, height=450)
    else:
        st.warning("Receiving public gateway response... Click 'FORCE REFRESH' if market feed is busy.")

# TAB 2: F&O BUILDUP (ALL STOCKS)
with t2:
    st.subheader("All 180+ F&O Equities Build-up Screener")
    df_fno = fetch_fno_market_data()
    
    if not df_fno.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Long Buildup", len(df_fno[df_fno["Build-up"] == "Long Buildup"]))
        c2.metric("🔴 Short Buildup", len(df_fno[df_fno["Build-up"] == "Short Buildup"]))
        c3.metric("⚡ Short Covering", len(df_fno[df_fno["Build-up"] == "Short Covering"]))
        c4.metric("⚠️ Long Unwinding", len(df_fno[df_fno["Build-up"] == "Long Unwinding"]))
        
        filter_action = st.radio(
            "Filter Market Structure:",
            ["All Contracts", "Long Buildup", "Short Buildup", "Short Covering", "Long Unwinding"],
            horizontal=True
        )
        
        if filter_action != "All Contracts":
            display_fno = df_fno[df_fno["Build-up"] == filter_action]
        else:
            display_fno = df_fno
            
        st.dataframe(
            display_fno.sort_values(by="% Price Chg", ascending=False),
            use_container_width=True,
            height=550
        )
    else:
        st.info("Synchronizing F&O market contracts...")

# TAB 3: VOLUME & MARKET MOVERS
with t3:
    st.subheader("Market Breadth: Top Gainers, Losers & Heavy Turnover")
    if not df_fno.empty:
        col_g, col_l = st.columns(2)
        with col_g:
            st.write("🟢 **Top Gainers (Price Acceleration)**")
            top_gainers = df_fno.sort_values(by="% Price Chg", ascending=False).head(10)
            st.dataframe(top_gainers[["Symbol", "LTP (₹)", "% Price Chg", "% OI Chg", "Build-up"]], use_container_width=True)
            
        with col_l:
            st.write("🔴 **Top Losers (Heavy Distribution)**")
            top_losers = df_fno.sort_values(by="% Price Chg", ascending=True).head(10)
            st.dataframe(top_losers[["Symbol", "LTP (₹)", "% Price Chg", "% OI Chg", "Build-up"]], use_container_width=True)
            
