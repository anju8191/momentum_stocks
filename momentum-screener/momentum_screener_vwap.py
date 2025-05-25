import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from ta.trend import ADXIndicator
from ta.volume import VolumeWeightedAveragePrice

# --- UI ---
st.set_page_config(page_title="Momentum Stock Screener", layout="wide")
st.title("📈 Momentum Screener with VWAP Breakout Detection")

tickers = st.text_area("Enter Stock Symbols (comma separated)", "RELIANCE.NS,TATASTEEL.NS,HDFCBANK.NS").split(',')
interval = st.selectbox("Select Interval", ["5m", "15m", "1h", "1d"])
lookback = st.slider("Lookback Period (days)", 1, 10, 2)

strong_momentum = []

for symbol in tickers:
    try:
        df = yf.download(symbol.strip(), period=f"{lookback}d", interval=interval, progress=False)
        df.dropna(inplace=True)
        if df.empty:
            st.warning(f"No data for {symbol}")
            continue

        # VWAP Calculation
        vwap = VolumeWeightedAveragePrice(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])
        df['VWAP'] = vwap.vwap

        # ADX Indicator
        adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14)
        df["ADX"] = adx.adx()

        last = df.iloc[-1]
        signal = ""

        # Breakout / Bounce Signal
        if last["Close"] > last["VWAP"] and last["ADX"] > 20:
            signal = "Breakout ↑"
            strong_momentum.append((symbol.strip(), signal, "green"))
        elif last["Close"] < last["VWAP"] and last["ADX"] > 20:
            signal = "Breakdown ↓"
            strong_momentum.append((symbol.strip(), signal, "red"))

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='Candles'
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='blue')))
        st.subheader(f"{symbol} - {signal}")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error with {symbol}: {str(e)}")

# Summary
st.markdown("## ✅ Momentum Summary")
for sym, sig, color in strong_momentum:
    st.markdown(f"<span style='color:{color}; font-size:18px'>{sym}: {sig}</span>", unsafe_allow_html=True)
