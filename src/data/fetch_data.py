import streamlit as st 
import yfinance as yf
import logic.trade_logic as trade_logic
import pandas as pd 

@st.cache_data
def load_ticker(ticker, timeframe='max'):
    ticker_obj = yf.Ticker(ticker)
    try:
        ticker_data = ticker_obj.history(period=timeframe)
        ticker_data.index = pd.to_datetime(ticker_data.index).tz_localize(None)
        details = ticker_obj.fast_info
        return ticker_data, dict(details)
    except:
        return None, None


@st.cache_data
def get_trades(strategy, asset_data, long_bool, gap=0, spans=(None), scaling=1, start=None):
    return trade_logic.get_trades(strategy=strategy, long_bool=long_bool, asset_data=asset_data, gap=gap,
                                  spans=spans, scaling=scaling, start=start)