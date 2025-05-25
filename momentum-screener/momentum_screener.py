import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
import ta
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Intraday Momentum Stock Screener", layout="wide")
st.title("📈 Intraday Momentum Stock Screener with VWAP Signals")

# Define parameters
st.sidebar.header("🔧 Filter Settings")
price_change_threshold = st.sidebar.slider("% Price Change", min_value=1.0, max_value=10.0, value=2.0)
volume_multiplier = st.sidebar.slider("Volume Spike (x Avg Vol)", min_value=1.0, max_value=10.0, value=1.5)
rsi_threshold = st.sidebar.slider("RSI Threshold", 50, 90, 70)
adx_threshold = st.sidebar.slider("ADX Threshold", 10, 50, 25)
refresh_interval = st.sidebar.slider("⏱ Refresh Interval (minutes)", 1, 30, 5)

# Auto stock list from NSE (top gainers)
def fetch_nse_momentum_stocks():
    url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        data = response.json()
        symbols = [item['symbol'] + ".NS" for item in data['data'][:10]]
        return symbols
    except:
        return []

# Stock list
auto_fetch = st.sidebar.checkbox("🔄 Auto Fetch Top Gainers from NSE", value=True)
if auto_fetch:
    ticker_list = fetch_nse_momentum_stocks()
    st.sidebar.write("📊 Using Top Gainers from NSE")
else:
    stocks = st.sidebar.text_area("Stock Symbols (comma separated)",
        value="RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS")
    ticker_list = [ticker.strip() for ticker in stocks.split(",") if ticker.strip()]

# Functions
def get_intraday_data(ticker, interval='5m', period='1d'):
    data = yf.download(ticker, interval=interval, period=period, progress=False)
    return data

def calculate_indicators(df):
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['ADX'] = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14).adx()
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    df['15min_avg_volume'] = df['Volume'].rolling(window=3).mean()
    return df

def detect_vwap_signal(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    signal = ""
    if previous['Close'] < previous['VWAP'] and latest['Close'] > latest['VWAP']:
        signal = "VWAP Breakout"
    elif previous['Close'] > previous['VWAP'] and latest['Close'] > latest['VWAP'] and latest['Low'] <= latest['VWAP']:
        signal = "VWAP Bounce"
    return signal

# Main loop
placeholder = st.empty()
while True:
    with placeholder.container():
        momentum_stocks = []
        st.info("🔍 Scanning for momentum stocks with live data...")

        for ticker in ticker_list:
            try:
                df = get_intraday_data(ticker)
                if df.empty or len(df) < 2:
                    continue
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                first = df.iloc[0]
                price_change = ((latest['Close'] - first['Open']) / first['Open']) * 100
                volume_spike = latest['Volume'] > volume_multiplier * df['15min_avg_volume'].mean()

                conditions = [
                    price_change >= price_change_threshold,
                    volume_spike,
                    latest['RSI'] >= rsi_threshold,
                    latest['ADX'] >= adx_threshold
                ]

                signal = detect_vwap_signal(df)

                if all(conditions) and signal:
                    momentum_stocks.append({
                        'Ticker': ticker,
                        'Price Change %': round(price_change, 2),
                        'Volume': int(latest['Volume']),
                        'RSI': round(latest['RSI'], 2),
                        'ADX': round(latest['ADX'], 2),
                        'VWAP': round(latest['VWAP'], 2),
                        'Close': round(latest['Close'], 2),
                        'Signal': signal
                    })
            except Exception as e:
                st.warning(f"Error fetching data for {ticker}: {e}")

        if momentum_stocks:
            st.success(f"✅ {len(momentum_stocks)} Buy Signals Found")
            df_result = pd.DataFrame(momentum_stocks)
            st.dataframe(df_result)

            for stock in momentum_stocks:
                st.subheader(f"📊 {stock['Ticker']} - {stock['Signal']}")
                color = 'green' if stock['Signal'] == "VWAP Breakout" else 'orange'
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=stock['Price Change %'],
                    delta={'reference': price_change_threshold},
                    gauge={'axis': {'range': [None, price_change_threshold * 3]},
                           'bar': {'color': color}},
                    title={'text': f"{stock['Signal']} Strength (% Change)"}
                ))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No buy signals found.")

    st.info(f"⏳ Refreshing in {refresh_interval} minute(s)...")
    time.sleep(refresh_interval * 60)
    placeholder.empty()
