import pandas as pd
import yfinance as yf
import streamlit as st

# Import other packages within strat_test
import plot_funcs
import trade_logic

@st.cache
def load_ticker(ticker):
    ticker_obj = yf.Ticker(ticker)
    history = ticker_obj.history(period='max')
    return history

st.set_page_config('Strategy Tester', layout='wide')


st.sidebar.title('Strategy Tester')
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'MSFT')
history = load_ticker(selected_ticker)

strategy = st.sidebar.selectbox('Select Buying Strategy', list(trade_logic.strategies.keys()))

st.plotly_chart(plot_funcs.plot_buys(history, strategy=strategy, scaling=0.85), use_container_width=True, height= 900)
