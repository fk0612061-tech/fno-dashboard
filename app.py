
  import streamlit as st
import pandas as pd
import plotly.express as px
from curl_cffi import requests
import time

st.set_page_config(layout="wide", page_title="NSE Live Market Master Terminal", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; }
    div[data-testid="stMetricValue"] { font-size: 1.3rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def get_nse_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    s = requests.Session(impersonate="chrome120")
    try:
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(0.5)
        return s, headers
    except:
        return None, headers

@st.cache_data(ttl=60)
def fetch_market_overview():
    s, headers = get_nse_session()
    if not s:
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame()
    try:
        idx_res = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10).json()
        indices_data = {}
        for item in idx_res.get("data", []):
            if item.get("indexSymbol") in ["NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY MIDCAP 100"]:
                indices_data[item.get("indexSymbol")] = {
                    "last": item.get("last"),
                    "change": item.get("change"),
                    "pChange": item.get("percentChange")
                }
        
        n50_res = s.get("https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050", headers=headers, timeout=10).json()
        stocks = n50_res.get("data", [])[1:]
        
        stock_list = []
        for st_item in stocks:
            stock_list.append({
                "Symbol": st_item.get("symbol"),
                "LTP": float(st_item.get("lastPrice", 0)),
                "% Change": float(st_item.get("pChange", 0)),
                "Volume (Shares)": int(st_item.get("totalTradedVolume", 0)),
                "Turnover (Cr)": round(float(st_item.get("totalTradedValue", 0)) / 10000000, 2),
                "52W High": float(st_item.get("yearHigh", 0)),
                "52W Low": float(st_item.get("yearLow", 0))
            })
            
        df_stocks = pd.DataFrame(stock_list)
        gainers = df_stocks.sort_values(by="% Change", ascending=False).head(10)
        losers = df_stocks.sort_values(by="% Change", ascending=True).head(10)
        return gainers, losers, indices_data, df_stocks
    except:
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_all_fno():
    s, headers = get_nse_session()
    if not s:
        return pd.DataFrame()
    try:
        url = "https://www.nseindia.com/api/live-analysis-variations?index=fo"
        res = s.get(url, headers=headers, timeout=10).json()
        records = []
        for row in res.get("allSec", {}).get("data", []):
            ltp = float(row.get("ltp", 0))
            p_chg = float(row.get("pChange", 0))
            oi = float(row.get("openInterest", 0))
            oi_chg = float(row.get("pchangeinOpenInterest", 0))
            
            if p_chg > 0 and oi_chg > 0:
                trend = "Long Build-up (Bullish)"
            elif p_chg < 0 and oi_chg > 0:
                trend = "Short Build-up (Bearish)"
            elif p_chg > 0 and oi_chg < 0:
                trend = "Short Covering (Pullback)"
            elif p_chg < 0 and oi_chg < 0:
                trend = "Long Unwinding (Profit Booking)"
            else:
                trend = "Neutral"
                
            records.append({
                "Symbol": row.get("symbol"),
                "LTP (₹)": ltp,
                "% Price Chg": p_chg,
                "Open Interest": oi,
                "% OI Chg": oi_chg,
                "Trend": trend
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_option_chain_nse(symbol):
    s, headers = get_nse_session()
    if not s:
        return [], []
    try:
        endpoint = "indices" if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else "equities"
        url = f"https://www.nseindia.com/api/option-chain-{endpoint}?symbol={symbol}"
        res = s.get(url, headers=headers, timeout=10).json()
        expiries = res["records"]["expiryDates"]
        data_rows = res["records"]["data"]
        return expiries, data_rows
    except:
        return [], []

st.title("⚡ NSE Real-Time Market & F&O Intelligence Terminal")

top_col1, top_col2 = st.columns([6, 1])
with top_col2:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Market Movers (Gainers / Losers)",
    "🔥 All F&O Stocks (Price vs OI)",
    "📊 Option Chain & PCR Analysis",
    "💼 Volume & 52-Week High/Low"
])

with tab1:
    with st.spinner("Fetching Live Market Status..."):
        gainers, losers, indices, all_stocks = fetch_market_overview()
    
    if indices:
        ic1, ic2, ic3, ic4 = st.columns(4)
        cols = [ic1, ic2, ic3, ic4]
        for idx, (iname, idata) in enumerate(indices.items()):
            cols[idx].metric(iname, f"{idata['last']:,}", f"{idata['change']} ({idata['pChange']}%)")
    st.divider()
    
    col_g, col_l = st.columns(2)
    with col_g:
        st.subheader("🟢 Top 10 Gainers")
        if not gainers.empty:
            st.dataframe(gainers[["Symbol", "LTP", "% Change", "Volume (Shares)", "Turnover (Cr)"]], use_container_width=True)
        else:
            st.info("डेटा लोड हो रहा है...")
    with col_l:
        st.subheader("🔴 Top 10 Losers")
        if not losers.empty:
            st.dataframe(losers[["Symbol", "LTP", "% Change", "Volume (Shares)", "Turnover (Cr)"]], use_container_width=True)
        else:
            st.info("डेटा लोड हो रहा है...")

with tab2:
    st.subheader("All 180+ F&O Stocks - Trend & Build-up Screener")
    with st.spinner("Analyzing F&O Contracts..."):
        df_fno = fetch_all_fno()
    
    if not df_fno.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Long Build-up", len(df_fno[df_fno["Trend"] == "Long Build-up (Bullish)"]))
        c2.metric("🔴 Short Build-up", len(df_fno[df_fno["Trend"] == "Short Build-up (Bearish)"]))
        c3.metric("⚡ Short Covering", len(df_fno[df_fno["Trend"] == "Short Covering (Pullback)"]))
        c4.metric("⚠️ Long Unwinding", len(df_fno[df_fno["Trend"] == "Long Unwinding (Profit Booking)"]))
        
        fno_filter = st.selectbox("Filter Stocks by Action:", [
            "All F&O Stocks",
            "Long Build-up (Bullish)",
            "Short Build-up (Bearish)",
            "Short Covering (Pullback)",
            "Long Unwinding (Profit Booking)"
        ])
        
        if fno_filter != "All F&O Stocks":
            view_fno = df_fno[df_fno["Trend"] == fno_filter]
        else:
            view_fno = df_fno
            
        st.dataframe(view_fno.sort_values(by="% Price Chg", ascending=False), use_container_width=True, height=500)
    else:
        st.warning("NSE F&O डेटा लोड हो रहा है। कृपया 'Refresh Data' दबाएं।")

with tab3:
    st.subheader("Live Options Greeks, OI & PCR")
    sel_sym = st.selectbox("Underlying Symbol:", ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "HDFCBANK", "INFY", "TCS", "TATAMOTORS"])
    
    expiries, raw_chain = fetch_option_chain_nse(sel_sym)
    if expiries and raw_chain:
        selected_exp = st.selectbox("Expiry Date:", expiries)
        
        chain_rows = []
        for r in raw_chain:
            if r.get("expiryDate") == selected_exp:
                strike = r.get("strikePrice")
                ce = r.get("CE", {})
                pe = r.get("PE", {})
                
                chain_rows.append({
                    "Call OI": ce.get("openInterest", 0),
                    "Call OI Chg": ce.get("changeinOpenInterest", 0),
                    "Call IV": ce.get("impliedVolatility", 0),
                    "Call LTP": ce.get("lastPrice", 0),
                    "STRIKE": strike,
                    "Put LTP": pe.get("lastPrice", 0),
                    "Put IV": pe.get("impliedVolatility", 0),
                    "Put OI Chg": pe.get("changeinOpenInterest", 0),
                    "Put OI": pe.get("openInterest", 0)
                })
        
        df_oc = pd.DataFrame(chain_rows)
        if not df_oc.empty:
            tot_call = df_oc["Call OI"].sum()
            tot_put = df_oc["Put OI"].sum()
            pcr_val = round(tot_put / tot_call, 2) if tot_call > 0 else 0
            
            p1, p2, p3 = st.columns(3)
            p1.metric("Total Call OI", f"{tot_call:,}")
            p2.metric("Total Put OI", f"{tot_put:,}")
            p3.metric("Live PCR", pcr_val, delta="Bullish (>1)" if pcr_val > 1 else "Bearish (<1)")
            
            st.dataframe(df_oc, use_container_width=True, height=500)
    else:
        st.info("ऑप्शन चेन लोड करने के लिए ऊपर 'Refresh Data' बटन दबाएं।")

with tab4:
    st.subheader("Market Breadth: High Volume & 52-Week Range")
    if not all_stocks.empty:
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.write("🔥 **Most Active by Volume (Shares)**")
            st.dataframe(all_stocks.sort_values(by="Volume (Shares)", ascending=False)[["Symbol", "LTP", "% Change", "Volume (Shares)"]].head(10), use_container_width=True)
        with v_col2:
            st.write("💰 **Most Active by Turnover (Crores ₹)**")
            st.dataframe(all_stocks.sort_values(by="Turnover (Cr)", ascending=False)[["Symbol", "LTP", "% Change", "Turnover (Cr)"]].head(10), use_container_width=True)
            
